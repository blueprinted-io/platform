"""Audit log read endpoint (§9.6, §5.1).

GET /audit   Audit role only, paginated, newest-first.
"""

from typing import Annotated

import structlog
from fastapi import APIRouter, Query
from sqlalchemy import select

from api.auth import Role
from api.dependencies import DBSession, require_role
from api.models.audit_log import AuditLog
from api.models.user import User
from api.schemas.audit_log import AuditLogResponse

log = structlog.get_logger(__name__)

router = APIRouter(prefix="/audit", tags=["audit"])

_Auditor = Annotated[User, require_role(Role.AUDIT, Role.ADMIN)]


@router.get("", response_model=list[AuditLogResponse])
async def list_audit_log(
    session: DBSession,
    user: _Auditor,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> list[AuditLogResponse]:
    """Return audit log entries, newest first. Accessible by Audit and Admin roles."""
    result = await session.execute(
        select(AuditLog)
        .order_by(AuditLog.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    return [AuditLogResponse.model_validate(e) for e in result.scalars().all()]
