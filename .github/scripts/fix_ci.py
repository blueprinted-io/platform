#!/usr/bin/env python3
"""
CI auto-fix using synthetic.new (model via the syn:large:text routing alias).
Usage: python fix_ci.py <run_id> <repo> <head_sha>

Fetches CI failure logs, asks the model to fix them, applies the changes.
Branch creation and PR opening are handled by the calling workflow.

Note: the workflow always checks out the default branch (not the failing commit)
to prevent untrusted code from running with secrets. The head_sha is used only
to restore the failing commit's source files via git for context.
"""

import json
import os
import re
import subprocess
import sys
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

API_KEY = os.environ["SYNTHETIC_API_KEY"]
MODEL = "syn:large:text"  # synthetic.new alias — auto-routes to the latest recommended large text model
API_URL = "https://api.synthetic.new/openai/v1/chat/completions"
MAX_LOG_CHARS = 8_000
MAX_FILE_CHARS = 4_000


def log(msg: str) -> None:
    print(msg, flush=True)


# ---------------------------------------------------------------------------
# API
# ---------------------------------------------------------------------------

def call_model(prompt: str, max_tokens: int = 8192) -> str:
    body = json.dumps({
        "model": MODEL,
        "max_tokens": max_tokens,
        "messages": [{"role": "user", "content": prompt}],
    }).encode()
    req = Request(
        API_URL,
        data=body,
        headers={
            "Authorization": f"Bearer {API_KEY}",
            "Content-Type": "application/json",
        },
    )
    try:
        with urlopen(req, timeout=120) as resp:
            data = json.loads(resp.read())
    except HTTPError as e:
        raise RuntimeError(f"API error {e.code}: {e.read().decode()}") from e

    msg = data["choices"][0]["message"]
    # GLM-5.1 returns content when given enough tokens; fall back to reasoning_content
    return msg.get("content") or msg.get("reasoning_content") or ""


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def sh(cmd: list[str]) -> str:
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.stdout


def get_logs(run_id: str, repo: str) -> str:
    logs = sh(["gh", "run", "view", run_id, "--repo", repo, "--log-failed"])
    # Strip the GHA log prefix: "<job>\t<step>\t<timestamp>Z " on each line
    lines = []
    for line in logs.splitlines():
        # Format: "jobname\tstepname\t2026-...Z actual content"
        parts = line.split("\t", 2)
        lines.append(parts[-1].split("Z ", 1)[-1] if len(parts) >= 3 else line)
    cleaned = "\n".join(lines)
    if len(cleaned) > MAX_LOG_CHARS:
        cleaned = cleaned[:MAX_LOG_CHARS] + "\n...[truncated]"
    return cleaned


def extract_paths(logs: str) -> list[str]:
    """Pull source file paths from failure log lines."""
    hits = re.findall(
        r'((?:api|tests|cli|workers|migrations)/[\w/.-]+\.py)',
        logs,
    )
    return list(dict.fromkeys(p for p in hits if Path(p).exists()))


def read_file(path: str) -> str:
    text = Path(path).read_text()
    if len(text) > MAX_FILE_CHARS:
        text = text[:MAX_FILE_CHARS] + "\n...[truncated]"
    return text


def parse_json_fix(response: str) -> list[dict]:
    """Extract the JSON fix object from model response."""
    # The model sometimes returns {{ and }} (double braces) — normalise first
    response = response.replace("{{", "{").replace("}}", "}")

    # Extract the JSON block (may be wrapped in markdown code fence)
    match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', response, re.DOTALL)
    if not match:
        match = re.search(r'(\{.*"files".*\})', response, re.DOTALL)
    if not match:
        log(f"WARNING: no JSON found in response. Raw output:\n{response[:600]}")
        return []
    try:
        return json.loads(match.group(1)).get("files", [])
    except json.JSONDecodeError as e:
        log(f"WARNING: JSON parse error: {e}\nRaw: {match.group(1)[:400]}")
        return []


REPO_ROOT = Path(".").resolve()
ALLOWED_DIRS = [REPO_ROOT / d for d in ("api", "tests", "cli", "workers")]
ALLOWED_FILES = {REPO_ROOT / "pyproject.toml"}


def _safe_target(path: str) -> Path | None:
    """Resolve path and verify it stays within an allowed directory or is an allowed file."""
    if ".." in Path(path).parts:
        return None
    target = (REPO_ROOT / path).resolve()
    if target in ALLOWED_FILES:
        return target
    if any(allowed in target.parents for allowed in ALLOWED_DIRS):
        return target
    return None


# Guard against models that echo the response template literally instead of
# returning real content (observed with the syn:large:text alias). Writing these
# would corrupt the target file — e.g. an invalid pyproject.toml that breaks uv lock.
_PLACEHOLDER_MARKERS = (
    "<full updated file content>",
    "<full corrected file content>",
)


def apply_files(files: list[dict]) -> list[str]:
    changed = []
    for f in files:
        path, content = f.get("path", ""), f.get("content", "")
        if not path or not content or "..." in path:
            continue
        if any(marker in content for marker in _PLACEHOLDER_MARKERS):
            log(f"  SKIPPED (model returned placeholder, not real content): {path}")
            continue
        target = _safe_target(path)
        if target is None:
            log(f"  SKIPPED (unsafe path): {path}")
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content)
        log(f"  fixed: {path}")
        changed.append(path)
    return changed


# ---------------------------------------------------------------------------
# Fix strategies
# ---------------------------------------------------------------------------

def fix_pip_audit(logs: str) -> list[str]:
    pyproject = Path("pyproject.toml").read_text()
    prompt = (
        "The pip-audit CI check failed with the following output:\n\n"
        f"{logs}\n\n"
        "Here is the current pyproject.toml:\n"
        f"```toml\n{pyproject}\n```\n\n"
        "Update the vulnerable package(s) to the patched version shown above.\n\n"
        "Respond with ONLY a JSON object like this (no other text, no markdown outside the block):\n"
        '```json\n'
        '{"files": [{"path": "pyproject.toml", "content": "<full updated file content>"}], '
        '"explanation": "one line summary"}\n'
        '```'
    )
    response = call_model(prompt)
    changed = apply_files(parse_json_fix(response))
    if "pyproject.toml" in changed:
        import tomllib

        try:
            tomllib.loads(Path("pyproject.toml").read_text())
        except tomllib.TOMLDecodeError as exc:
            log(f"  updated pyproject.toml is not valid TOML ({exc}); reverting")
            subprocess.run(["git", "checkout", "--", "pyproject.toml"], check=False)
            return []
        log("  running uv lock...")
        subprocess.run(["uv", "lock"], check=True)
        changed.append("uv.lock")
    return changed


def fix_general(logs: str, paths: list[str]) -> list[str]:
    file_context = "\n\n".join(
        f"### {p}\n```python\n{read_file(p)}\n```"
        for p in paths
    )
    if not file_context:
        file_context = "(no source files identified from error output)"

    prompt = (
        "The CI workflow failed with these errors:\n\n"
        f"{logs}\n\n"
        f"Relevant source files:\n\n{file_context}\n\n"
        "Fix the failures. Rules:\n"
        "- ruff: fix linting errors (remove unused imports, fix line length, etc)\n"
        "- mypy: fix type errors directly in the source\n"
        "- pytest: fix the test or the source — never mock the database layer\n\n"
        "Respond with ONLY a JSON object like this (no other text, no markdown outside the block):\n"
        '```json\n'
        '{"files": [{"path": "relative/path/to/file.py", "content": "<full corrected file content>"}], '
        '"explanation": "one line summary"}\n'
        '```\n\n'
        "Return complete file contents (not diffs). Only include files that need changes."
    )
    response = call_model(prompt)
    return apply_files(parse_json_fix(response))


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> int:
    if len(sys.argv) < 4:
        print("Usage: fix_ci.py <run_id> <repo> <head_sha>", file=sys.stderr)
        return 1

    run_id, repo, head_sha = sys.argv[1], sys.argv[2], sys.argv[3]

    # Restore the failing commit's source files for context.
    # The workflow checked out main (trusted), so we selectively restore only
    # source/test files from the failing commit — never pyproject or scripts.
    log(f"Restoring source files from failing commit {head_sha[:8]}...")
    subprocess.run(["git", "fetch", "origin", head_sha], check=True, capture_output=True)
    subprocess.run(
        ["git", "checkout", head_sha, "--", "api/", "tests/", "cli/", "workers/"],
        check=False, capture_output=True,
    )

    log(f"Fetching logs for run {run_id}...")
    logs = get_logs(run_id, repo)
    if not logs.strip():
        log("No failure logs found — nothing to fix.")
        return 0

    log(f"Log size: {len(logs)} chars")

    if "pip-audit" in logs and ("known vulnerabilit" in logs or "PYSEC-" in logs):
        log("Strategy: pip-audit")
        changed = fix_pip_audit(logs)
    else:
        paths = extract_paths(logs)
        log(f"Strategy: general | files: {paths or '(none identified)'}")
        changed = fix_general(logs, paths)

    if not changed:
        log("No changes produced.")
        return 1

    log(f"Done. Changed: {changed}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
