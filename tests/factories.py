"""Minimal valid request payload factories for governed record tests.

Each factory returns the smallest payload that satisfies required fields for
a given record type. Pass keyword overrides to vary individual fields.
"""

from typing import Any


def principle_payload(**overrides: Any) -> dict[str, Any]:
    base: dict[str, Any] = {
        "title": "Signal-to-noise in documentation",
        "summary": "Documentation should add information the code does not already express.",
        "explanation": (
            "Comments that restate what the code does are noise. "
            "Comments that explain why — a constraint, a workaround, a non-obvious invariant — "
            "are signal. Signal earns its place; noise erodes reader trust."
        ),
        "domain": "test-domain",
    }
    base.update(overrides)
    return base


def task_payload(**overrides: Any) -> dict[str, Any]:
    base: dict[str, Any] = {
        "title": "Rotate a PostgreSQL superuser password",
        "outcome": (
            "The superuser password has been changed and all dependent service credentials updated."
        ),
        "domain": "test-domain",
    }
    base.update(overrides)
    return base


def task_step_payload(**overrides: Any) -> dict[str, Any]:
    base: dict[str, Any] = {
        "step": "Connect to the database as the current superuser",
        "completion": (
            "You are connected and have verified the current user with SELECT current_user."
        ),
        "notes": None,
        "irreversible": False,
    }
    base.update(overrides)
    return base


def task_step_action_payload(**overrides: Any) -> dict[str, Any]:
    base: dict[str, Any] = {
        "instruction": "Run: psql -U postgres",
    }
    base.update(overrides)
    return base


def workflow_payload(**overrides: Any) -> dict[str, Any]:
    base: dict[str, Any] = {
        "title": "Quarterly credential rotation",
        "objective": (
            "Rotate all service credentials on a quarterly schedule "
            "to limit blast radius of any credential compromise."
        ),
        "domain": "test-domain",
    }
    base.update(overrides)
    return base
