"""Prompt loading for the ingestion pipeline (§11.16).

Reads versioned markdown files from prompts/ingestion/ at import time and
caches them. No inline prompt strings exist in Python source — the files
are the single source of truth.

Each file contains ## System Prompt and ## User Message Template sections
delimited by level-2 markdown headings. Content between the heading and the
next ## heading is extracted verbatim (stripped of leading/trailing whitespace).
The ## Known-Good Example section and any further sections are ignored at
load time — they are for human readers and LLM grounding, not for code.
"""

from dataclasses import dataclass
from pathlib import Path

_PROMPTS_DIR = Path(__file__).parent.parent / "prompts" / "ingestion"

_VALID_STAGES = ("triage", "extract_task", "extract_principle")


@dataclass(frozen=True)
class Prompt:
    """A loaded prompt ready to be rendered into a message pair."""

    stage: str
    system: str
    user_template: str

    def render(self, **kwargs: str) -> tuple[str, str]:
        """Return (system_message, user_message) with variables substituted."""
        return self.system, self.user_template.format(**kwargs)


def _parse_prompt_file(path: Path) -> tuple[str, str]:
    """Extract system and user_template text from a prompt markdown file."""
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()

    sections: dict[str, list[str]] = {}
    current: str | None = None

    for line in lines:
        if line.startswith("## "):
            current = line[3:].strip()
            sections[current] = []
        elif current is not None:
            sections[current].append(line)

    def _extract(name: str) -> str:
        raw = "\n".join(sections.get(name, []))
        return raw.strip()

    system = _extract("System Prompt")
    user_template = _extract("User Message Template")

    if not system:
        raise ValueError(f"No '## System Prompt' section found in {path}")
    if not user_template:
        raise ValueError(f"No '## User Message Template' section found in {path}")

    return system, user_template


def _load_all() -> dict[str, Prompt]:
    cache: dict[str, Prompt] = {}
    for stage in _VALID_STAGES:
        path = _PROMPTS_DIR / f"{stage}.md"
        system, user_template = _parse_prompt_file(path)
        cache[stage] = Prompt(stage=stage, system=system, user_template=user_template)
    return cache


_cache: dict[str, Prompt] = _load_all()


def load(stage: str) -> Prompt:
    """Return the cached Prompt for the given pipeline stage.

    Raises KeyError if stage is not one of the valid ingestion stages.
    """
    try:
        return _cache[stage]
    except KeyError:
        raise KeyError(
            f"Unknown prompt stage {stage!r}. Valid stages: {_VALID_STAGES}"
        ) from None
