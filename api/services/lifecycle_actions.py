"""Shared lifecycle mutations for governed records (tasks, workflows, principles).

Centralises confirm / return / deprecate / retire so:
- Audit events are written in one place (§9.6).
- Route handlers stay thin — they own pre-checks (domain, foreign claim) and
  post-steps (notifications, embedding enqueue) but not the mutation logic.

Each function:
  1. Asserts the transition is legal (delegates to lifecycle.py assertions).
  2. Mutates the record in place.
  3. Writes an audit_log entry.
  4. Commits the session.

Callers must NOT commit between calling one of these functions and reading the
returned record — the commit happens inside, and the session is left clean.
"""

from typing import Any

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from api.models.user import User
from api.services import lifecycle
from api.services.audit import write_audit_event

log = structlog.get_logger(__name__)


def _base_detail(record: Any, record_type: str) -> dict:
    return {
        "record_type": record_type,
        "record_id": str(record.record_id),
        "version": record.version,
    }


async def confirm_record(
    record: Any,
    session: AsyncSession,
    user: User,
    justification: str | None,
    record_type: str,
) -> bool:
    """submitted → confirmed. Returns True if this was a break-glass confirm.

    Callers must have already run assert_domain_access and assert_no_foreign_claim.
    """
    is_break_glass = lifecycle.assert_can_confirm(
        record.status, record.created_by, user, justification
    )
    record.status = "confirmed"
    record.self_confirmed_by_admin = is_break_glass
    record.reviewed_by = user.id
    record.updated_by = user.id

    detail = _base_detail(record, record_type)
    if is_break_glass:
        detail["justification"] = justification

    await write_audit_event(
        session,
        event_type="break_glass_confirm" if is_break_glass else "record_confirmed",
        actor=user,
        target_id=record.id,
        target_type=record_type,
        detail=detail,
    )
    log.info("record_confirmed", record_type=record_type, record_id=str(record.id), user_id=str(user.id), break_glass=is_break_glass)
    await session.commit()
    return is_break_glass


async def return_record(
    record: Any,
    session: AsyncSession,
    user: User,
    note: str | None,
    severity: str | None,
    record_type: str,
) -> None:
    """submitted → returned."""
    lifecycle.assert_can_return(record.status, user)
    record.status = "returned"
    if note:
        record.change_note = note
    record.return_severity = severity
    record.reviewed_by = user.id
    record.updated_by = user.id

    detail = _base_detail(record, record_type)
    if note:
        detail["note"] = note
    if severity:
        detail["severity"] = severity

    await write_audit_event(
        session,
        event_type="record_returned",
        actor=user,
        target_id=record.id,
        target_type=record_type,
        detail=detail,
    )
    await session.commit()


async def deprecate_record(
    record: Any,
    session: AsyncSession,
    user: User,
    record_type: str,
) -> None:
    """confirmed → deprecated."""
    lifecycle.assert_can_deprecate(record.status, user)
    record.status = "deprecated"
    record.updated_by = user.id

    await write_audit_event(
        session,
        event_type="record_deprecated",
        actor=user,
        target_id=record.id,
        target_type=record_type,
        detail=_base_detail(record, record_type),
    )
    await session.commit()


async def retire_record(
    record: Any,
    session: AsyncSession,
    user: User,
    record_type: str,
) -> None:
    """confirmed → retired (permanent)."""
    lifecycle.assert_can_retire(record.status, user)
    record.status = "retired"
    record.updated_by = user.id

    await write_audit_event(
        session,
        event_type="record_retired",
        actor=user,
        target_id=record.id,
        target_type=record_type,
        detail=_base_detail(record, record_type),
    )
    await session.commit()
