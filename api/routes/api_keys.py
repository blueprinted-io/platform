"""Admin API key management endpoints (§5.3, §9.6).

GET    /admin/api-keys              List all API keys (no raw keys)
POST   /admin/api-keys              Create a key (returns raw key once)
DELETE /admin/api-keys/{id}         Revoke a key
"""

import hashlib
import secrets
import uuid
from datetime import UTC, datetime, timedelta
from typing import Annotated

import structlog
from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from api.auth import AgentRole, Role
from api.dependencies import DBSession, require_role
from api.models.api_key import ApiKey
from api.models.user import User
from api.schemas.api_key import ApiKeyCreate, ApiKeyCreatedResponse, ApiKeyResponse
from api.services.audit import write_audit_event

log = structlog.get_logger(__name__)

router = APIRouter(prefix="/admin/api-keys", tags=["api-keys"])

_Admin = Annotated[User, require_role(Role.ADMIN)]

_VALID_AGENT_ROLES = {r.value for r in AgentRole}
_KEY_BODY_LENGTH = 36  # 36 bytes → 48 URL-safe base64 chars → 288 bits entropy


def _generate_key() -> tuple[str, str, str]:
    """Return (raw_key, key_prefix, key_hash)."""
    body = secrets.token_urlsafe(_KEY_BODY_LENGTH)
    raw = f"bp_{body}"
    prefix = raw[:8]
    digest = hashlib.sha256(raw.encode()).hexdigest()
    return raw, prefix, digest


@router.get("", response_model=list[ApiKeyResponse])
async def list_api_keys(session: DBSession, user: _Admin) -> list[ApiKeyResponse]:
    """List all API keys. Raw keys are never returned."""
    result = await session.execute(
        select(ApiKey).order_by(ApiKey.created_at.desc())
    )
    return [ApiKeyResponse.model_validate(k) for k in result.scalars().all()]


@router.post("", response_model=ApiKeyCreatedResponse, status_code=status.HTTP_201_CREATED)
async def create_api_key(
    body: ApiKeyCreate,
    session: DBSession,
    user: _Admin,
) -> ApiKeyCreatedResponse:
    """Create a scoped API key. The raw key is returned once — store it securely."""
    if body.role.value not in _VALID_AGENT_ROLES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"role must be one of {sorted(_VALID_AGENT_ROLES)}.",
        )

    raw_key, prefix, key_hash = _generate_key()

    expires_at = (
        datetime.now(UTC) + timedelta(days=body.expires_at_days)
        if body.expires_at_days is not None
        else None
    )
    api_key = ApiKey(
        name=body.name,
        key_prefix=prefix,
        key_hash=key_hash,
        role=body.role.value,
        created_by=user.id,
        expires_at=expires_at,
    )
    session.add(api_key)

    await session.flush()  # populate api_key.id before audit log
    await write_audit_event(
        session,
        event_type="api_key_created",
        actor=user,
        target_id=api_key.id,
        target_type="api_key",
        detail={"name": api_key.name, "role": api_key.role},
    )

    await session.commit()
    await session.refresh(api_key)

    log.info("api_key_created", api_key_id=str(api_key.id), name=api_key.name, role=api_key.role)

    base = ApiKeyResponse.model_validate(api_key).model_dump()
    return ApiKeyCreatedResponse(**base, raw_key=raw_key)


@router.delete("/{key_id}", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_api_key(
    key_id: uuid.UUID,
    session: DBSession,
    user: _Admin,
) -> None:
    """Revoke an API key. Immediate effect — any bearer using this key gets 401."""
    api_key = (
        await session.execute(select(ApiKey).where(ApiKey.id == key_id))
    ).scalar_one_or_none()

    if api_key is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="API key not found.")

    if api_key.revoked_at is not None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="API key is already revoked.",
        )

    api_key.revoked_at = datetime.now(UTC)
    api_key.revoked_by = user.id

    await write_audit_event(
        session,
        event_type="api_key_revoked",
        actor=user,
        target_id=api_key.id,
        target_type="api_key",
        detail={"name": api_key.name, "role": api_key.role},
    )

    await session.commit()
    log.info("api_key_revoked", api_key_id=str(api_key.id))
