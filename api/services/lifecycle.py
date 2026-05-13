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
  Admins are exempt (break-glass for small teams) but must supply a non-empty
  justification when confirming their own content (§5.1 break-glass flow).

Domain enforcement (§7.3):
  Contributors must be assigned to a record's domain to create, submit, or
  review (confirm/return) domain-scoped records. Admin bypasses all checks.
  Facts and Concepts are domain-agnostic — no enforcement applied.
"""

import uuid

import sqlalchemy as sa
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

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


def assert_can_confirm(
    record_status: str,
    record_created_by: uuid.UUID,
    user: User,
    justification: str | None,
) -> bool:
    """submitted → confirmed. Returns True if self_confirmed_by_admin should be set.

    Self-review prohibition applies to contributors; admins are exempt but must
    supply a non-empty justification when confirming their own content (§5.1).
    """
    if record_status != "submitted":
        raise HTTPException(
            status_code=422,
            detail=f"Cannot confirm a record with status '{record_status}'.",
        )
    if not _has_role(user, *_CONTRIBUTOR_OR_ADMIN):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions."
        )
    is_self_confirm = record_created_by == user.id
    if not _is_admin(user) and is_self_confirm:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Self-review prohibited: you cannot confirm your own submission.",
        )
    if _is_admin(user) and is_self_confirm:
        if not justification or not justification.strip():
            raise HTTPException(
                status_code=422,
                detail=(
                    "Admin break-glass confirm requires a non-empty justification (§5.1)."
                ),
            )
        return True
    return False


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


async def assert_domain_active(domain: str, session: AsyncSession) -> None:
    """Raise 422 if the domain does not exist or is disabled (§7.3)."""
    result = await session.execute(
        sa.text("SELECT disabled_at FROM domains WHERE name = :name"),
        {"name": domain},
    )
    row = result.fetchone()
    if row is None:
        raise HTTPException(
            status_code=422,
            detail=f"Domain '{domain}' does not exist.",
        )
    if row.disabled_at is not None:
        raise HTTPException(
            status_code=422,
            detail=f"Domain '{domain}' is disabled and cannot be used.",
        )


async def assert_domain_access(domain: str, user: User, session: AsyncSession) -> None:
    """Raise 403 if the contributor is not assigned to the domain (§7.3).

    Admin bypasses this check implicitly — this function should not be called
    for admin users, but is safe to call regardless.
    """
    if _is_admin(user):
        return
    result = await session.execute(
        sa.text(
            "SELECT 1 FROM user_domains WHERE user_id = :uid AND domain = :domain"
        ),
        {"uid": user.id, "domain": domain},
    )
    if result.fetchone() is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"You are not assigned to domain '{domain}'.",
        )
