#!/usr/bin/env python3
"""
CI auto-fix using synthetic.new GLM-5.1.
Usage: python fix_ci.py <run_id> <repo> <head_sha>

Fetches CI failure logs, asks the model to fix them, applies the changes.
Branch creation and PR opening are handled by the calling workflow.

Note: the workflow always checks out the default branch (not the failing commit)
to prevent untrusted code from running with secrets. The head_sha is used only
to check out the failing commit's source files via git for context.
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
MODEL = "hf:zai-org/GLM-5.1"
API_URL = "https://api.synthetic.new/openai/v1/chat/completions"
MAX_LOG_CHARS = 8_000
MAX_FILE_CHARS = 4_000


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
    if len(logs) > MAX_LOG_CHARS:
        logs = logs[:MAX_LOG_CHARS] + "\n...[truncated]"
    return logs


def extract_paths(logs: str) -> list[str]:
    """Pull source file paths out of failure log lines."""
    hits = re.findall(
        r'\b((?:api|tests|cli|workers|migrations)/[\w/.-]+\.py)\b',
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
    match = re.search(r'\{[^{}]*"files"\s*:\s*\[.*?\]\s*\}', response, re.DOTALL)
    if not match:
        # Try broader match
        match = re.search(r'\{.*"files".*\}', response, re.DOTALL)
    if not match:
        print(f"WARNING: no JSON found in response. Raw output:\n{response[:600]}", file=sys.stderr)
        return []
    try:
        return json.loads(match.group()).get("files", [])
    except json.JSONDecodeError as e:
        print(f"WARNING: JSON parse error: {e}\nRaw: {match.group()[:400]}", file=sys.stderr)
        return []


def apply_files(files: list[dict]) -> list[str]:
    changed = []
    for f in files:
        path, content = f.get("path", ""), f.get("content", "")
        if not path or not content:
            continue
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        Path(path).write_text(content)
        print(f"  fixed: {path}")
        changed.append(path)
    return changed


# ---------------------------------------------------------------------------
# Fix strategies
# ---------------------------------------------------------------------------

def fix_pip_audit(logs: str) -> list[str]:
    pyproject = Path("pyproject.toml").read_text()
    prompt = f"""The pip-audit CI check failed:

{logs}

Current pyproject.toml:
```toml
{pyproject}
```

Update the vulnerable package(s) to the patched version shown in the audit output.

Return ONLY valid JSON, no other text:
{{
  "files": [
    {{"path": "pyproject.toml", "content": "<full updated content>"}}
  ],
  "explanation": "one line summary"
}}"""

    response = call_model(prompt)
    changed = apply_files(parse_json_fix(response))
    if "pyproject.toml" in changed:
        print("  running uv lock...")
        subprocess.run(["uv", "lock"], check=True)
        changed.append("uv.lock")
    return changed


def fix_general(logs: str, paths: list[str]) -> list[str]:
    file_context = "\n\n".join(
        f"### {p}\n```python\n{read_file(p)}\n```"
        for p in paths
    ) or "(no source files identified — use the error context to determine what to fix)"

    prompt = f"""The CI workflow failed:

{logs}

Relevant source files:
{file_context}

Fix the failures. Return ONLY valid JSON, no other text:
{{
  "files": [
    {{"path": "relative/path/to/file.py", "content": "<full corrected file content>"}}
  ],
  "explanation": "one line summary"
}}

Rules:
- Return complete file contents, not diffs
- Only include files that need changing
- ruff: fix linting errors (unused imports, line length, formatting)
- mypy: fix type errors in source files directly
- pytest: fix the test or the source — never mock the database layer"""

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

    # Check out the failing commit's files so the model has the right context.
    # The workflow checked out main (trusted), but we need the broken source.
    print(f"Checking out failing commit {head_sha[:8]}...")
    subprocess.run(["git", "fetch", "origin", head_sha], check=True, capture_output=True)
    subprocess.run(["git", "checkout", head_sha, "--", "api/", "tests/", "cli/", "workers/", "pyproject.toml"],
                   check=False, capture_output=True)  # best-effort; files may not all exist

    print(f"Fetching logs for run {run_id} in {repo}...")

    logs = get_logs(run_id, repo)
    if not logs.strip():
        print("No failure logs found — nothing to fix.")
        return 0

    print(f"Log size: {len(logs)} chars")

    if "pip-audit" in logs and ("known vulnerabilit" in logs or "PYSEC-" in logs):
        print("Strategy: pip-audit")
        changed = fix_pip_audit(logs)
    else:
        paths = extract_paths(logs)
        print(f"Strategy: general | files: {paths or '(none identified)'}")
        changed = fix_general(logs, paths)

    if not changed:
        print("No changes produced.", file=sys.stderr)
        return 1

    print(f"Done. Changed: {changed}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
