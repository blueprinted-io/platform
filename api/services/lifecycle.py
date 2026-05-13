"""Shared lifecycle state machine and permission enforcement.

Governs all state transitions for Facts, Concepts, Principles, Tasks, and Workflows.

State machine (§9.3):
  draft → submitted → confirmed → deprecated
              ↓               ↑
           returned ──────────┘  (revised and resubmitted)

  confirmed → retired  (admin only, permanent)

No-machine-can-confirm (§10.2, §5.3):
  Sprint 4-9: confirm endpoints require a valid human OIDC JWT. Machine
  credentials don't exist before Sprint 10, so requiring a JWT is sufficient.
  Sprint 10 adds an explicit machine-credential rejection check.

Self-review prohibition (§5.1):
  Contributors cannot confirm or return content they created.
  Admins are exempt (break-glass for small teams).
"""

import uuid

from fastapi import HTTPException, status

from api.auth import Role
from api.models.user import User

_EDITABLE_STATUSES = {"draft", "returned"}
_CONTRIBUTOR_OR_ADMIN = {Role.CONTRIBUTOR.value, Role.ADMIN.value}


def _is_admin(user: User) -> bool:
    return Role.ADMIN.value in user.roles


def _has_role(user: User, *roles: str) -> bool:
    return any(r in user.roles for r in roles)


def assert_can_edit(status: str) -> None:
    """Raise 422 if the record is not in an editable state (draft or returned)."""
    if status not in _EDITABLE_STATUSES:
        raise HTTPException(
            status_code=422,
            detail=f"Cannot edit a record with status '{status}'.",
        )


def assert_can_mutate_refs(record_status: str) -> None:
    """Raise 422 if steps/refs cannot be added to a record in its current status."""
    if record_status not in _EDITABLE_STATUSES:
        raise HTTPException(
            status_code=422,
            detail=f"Cannot modify refs on a record with status '{record_status}'.",
        )


def assert_can_submit(record_status: str, user: User) -> None:
    """draft/returned → submitted. Requires contributor or admin."""
    if record_status not in _EDITABLE_STATUSES:
        raise HTTPException(
            status_code=422,
            detail=f"Cannot submit a record with status '{record_status}'.",
        )
    if not _has_role(user, *_CONTRIBUTOR_OR_ADMIN):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions."
        )


def assert_can_confirm(record_status: str, record_created_by: uuid.UUID, user: User) -> None:
    """submitted → confirmed. Self-review prohibition applies to contributors; admins exempt."""
    if record_status != "submitted":
        raise HTTPException(
            status_code=422,
            detail=f"Cannot confirm a record with status '{record_status}'.",
        )
    if not _has_role(user, *_CONTRIBUTOR_OR_ADMIN):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions."
        )
    if not _is_admin(user) and record_created_by == user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Self-review prohibited: you cannot confirm your own submission.",
        )


def assert_can_return(record_status: str, user: User) -> None:
    """submitted → returned. Requires contributor or admin."""
    if record_status != "submitted":
        raise HTTPException(
            status_code=422,
            detail=f"Cannot return a record with status '{record_status}'.",
        )
    if not _has_role(user, *_CONTRIBUTOR_OR_ADMIN):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions."
        )


def assert_can_deprecate(record_status: str, user: User) -> None:
    """confirmed → deprecated. Admin only."""
    if record_status != "confirmed":
        raise HTTPException(
            status_code=422,
            detail=f"Cannot deprecate a record with status '{record_status}'.",
        )
    if not _is_admin(user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin role required.")


def assert_can_retire(record_status: str, user: User) -> None:
    """confirmed → retired. Admin only. Permanent."""
    if record_status != "confirmed":
        raise HTTPException(
            status_code=422,
            detail=f"Cannot retire a record with status '{record_status}'.",
        )
    if not _is_admin(user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin role required.")
