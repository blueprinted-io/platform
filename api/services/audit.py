"""Audit log write helpers (§9.6)."""

import uuid
from typing import Any

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from api.models.audit_log import AuditLog
from api.models.user import User

log = structlog.get_logger(__name__)


async def write_audit_event(
    session: AsyncSession,
    *,
    event_type: str,
    actor: User,
    target_id: uuid.UUID | None = None,
    target_type: str | None = None,
    detail: dict[str, Any] | None = None,
) -> AuditLog:
    """Append an entry to the audit log. Caller must commit the session."""
    actor_type = "agent" if any(r.startswith("agent:") for r in actor.roles) else "user"
    entry = AuditLog(
        event_type=event_type,
        actor_id=actor.id,
        actor_type=actor_type,
        target_id=target_id,
        target_type=target_type,
        detail=detail or {},
    )
    session.add(entry)
    log.info("audit_event", event_type=event_type, actor_id=str(actor.id))
    return entry
