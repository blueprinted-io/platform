"""Step quality linting for Task records (§9.10).

Rules are non-blocking — they produce advisory warnings, not errors.
Warnings are computed on response, never stored.
"""

from dataclasses import dataclass
from typing import Any

_ABSTRACT_VERBS = frozenset({"ensure", "handle", "manage", "maintain", "support", "address"})


@dataclass
class LintWarning:
    step_index: int
    rule: str
    message: str


def lint_steps(steps: list[Any]) -> list[LintWarning]:
    """Compute lint warnings for a list of TaskStep-like objects.

    Accepts any objects with .step (str), .completion (str), and .actions (list).
    """
    warnings: list[LintWarning] = []
    for i, step in enumerate(steps):
        first_word = step.step.split()[0].lower().rstrip(".,;:") if step.step.strip() else ""
        if first_word in _ABSTRACT_VERBS:
            warnings.append(LintWarning(
                step_index=i,
                rule="abstract_verb",
                message=f'Step begins with abstract verb "{first_word}". Use a concrete action instead.',  # noqa: E501
            ))
        if not step.completion or not step.completion.strip():
            warnings.append(LintWarning(
                step_index=i,
                rule="missing_completion",
                message="Step has no completion criterion.",
            ))
        if not step.actions:
            warnings.append(LintWarning(
                step_index=i,
                rule="empty_actions",
                message="Step has no actions.",
            ))
    return warnings
