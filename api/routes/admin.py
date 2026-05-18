"""Admin API endpoints (§23.11).

All endpoints require the Admin role.

Routes:
  GET  /admin/settings              List all settings (encrypted values masked)
  PATCH /admin/settings             Bulk upsert settings
  GET  /admin/domains               List all domains
  POST /admin/domains               Create domain
  POST /admin/domains/{name}/disable Soft-delete domain
  POST /admin/domains/{name}/enable  Re-enable domain
  GET  /admin/users/{id}/domains    List a user's domain assignments
  PUT  /admin/users/{id}/domains    Replace a user's domain assignments
  GET  /admin/health                System health summary
"""

import uuid
from typing import Annotated

import httpx
import structlog
from fastapi import APIRouter, HTTPException, status
from sqlalchemy import func, select, text
from sqlalchemy.exc import IntegrityError, ProgrammingError
from sqlalchemy.ext.asyncio import AsyncSession

from api.auth import Role
from api.dependencies import AppSettings, DBSession, require_role
from api.models.domain import Domain, UserDomain
from api.models.notification import Notification
from api.models.settings import SystemSetting
from api.models.user import User
from api.schemas.admin import (
    DomainCreate,
    DomainResponse,
    HealthResponse,
    SettingResponse,
    SettingsBatchPatch,
    TestConnectionRequest,
    TestConnectionResponse,
    UserDomainResponse,
    UserDomainsReplace,
)
from api.services.settings_service import get_setting, set_setting

log = structlog.get_logger(__name__)

router = APIRouter(prefix="/admin", tags=["admin"])

_Admin = Annotated[User, require_role(Role.ADMIN)]


# ---------------------------------------------------------------------------
# System settings
# ---------------------------------------------------------------------------

@router.get("/settings", response_model=list[SettingResponse])
async def list_settings(session: DBSession, _user: _Admin) -> list[SystemSetting]:
    result = await session.execute(select(SystemSetting).order_by(SystemSetting.key))
    rows = list(result.scalars().all())
    # Mask encrypted values — write-only
    for row in rows:
        if row.encrypted:
            row.value = None
    return rows


@router.patch("/settings", response_model=list[SettingResponse])
async def patch_settings(
    body: SettingsBatchPatch,
    session: DBSession,
    user: _Admin,
    app_settings: AppSettings,
) -> list[SystemSetting]:
    secret = app_settings.app_secret_key.get_secret_value()
    for key, patch in body.settings.items():
        if patch.value is not None:
            await set_setting(
                session,
                key=key,
                value=patch.value,
                encrypted=patch.encrypted,
                app_secret_key=secret,
                updated_by_id=user.id,
            )
    await session.commit()

    result = await session.execute(select(SystemSetting).order_by(SystemSetting.key))
    rows = list(result.scalars().all())
    for row in rows:
        if row.encrypted:
            row.value = None
    return rows


# ---------------------------------------------------------------------------
# LLM connection test
# ---------------------------------------------------------------------------

@router.post("/settings/test-connection", response_model=TestConnectionResponse)
async def test_llm_connection(
    body: TestConnectionRequest,
    session: DBSession,
    _user: _Admin,
    app_settings: AppSettings,
) -> TestConnectionResponse:
    """Probe GET {base_url}/models and return available model IDs.

    If api_key is blank and api_key_setting names a system_settings key,
    the stored (decrypted) value is used automatically.
    """
    if not body.base_url:
        return TestConnectionResponse(ok=False, models=[], error="base_url is required")

    api_key = body.api_key
    if not api_key and body.api_key_setting:
        secret = app_settings.app_secret_key.get_secret_value()
        api_key = await get_setting(session, body.api_key_setting, app_secret_key=secret) or ""

    headers: dict[str, str] = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    try:
        async with httpx.AsyncClient(timeout=10) as http:
            resp = await http.get(f"{body.base_url.rstrip('/')}/models", headers=headers)

        # 404 means the server is reachable but this provider doesn't implement /models.
        # Treat as connected with no enumerable model list.
        if resp.status_code == 404:
            return TestConnectionResponse(ok=True, models=[])

        resp.raise_for_status()
        data = resp.json()
        # OpenAI-compatible: { data: [{ id: "..." }, ...] }
        model_ids: list[str] = []
        if isinstance(data, dict) and "data" in data:
            model_ids = [m["id"] for m in data["data"] if isinstance(m, dict) and "id" in m]
        elif isinstance(data, list):
            model_ids = [m["id"] for m in data if isinstance(m, dict) and "id" in m]
        model_ids.sort()
        return TestConnectionResponse(ok=True, models=model_ids)
    except httpx.HTTPStatusError as exc:
        return TestConnectionResponse(ok=False, models=[], error=f"HTTP {exc.response.status_code}")
    except Exception as exc:
        return TestConnectionResponse(ok=False, models=[], error=str(exc))


# ---------------------------------------------------------------------------
# Domains
# ---------------------------------------------------------------------------

@router.get("/domains", response_model=list[DomainResponse])
async def list_domains(session: DBSession, _user: _Admin) -> list[Domain]:
    result = await session.execute(select(Domain).order_by(Domain.name))
    return list(result.scalars().all())


@router.post("/domains", response_model=DomainResponse, status_code=status.HTTP_201_CREATED)
async def create_domain(body: DomainCreate, session: DBSession, user: _Admin) -> Domain:
    domain = Domain(name=body.name, created_by=user.id)
    session.add(domain)
    try:
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise HTTPException(status_code=409, detail="Domain already exists.") from exc
    await session.refresh(domain)
    return domain


@router.post("/domains/{name}/disable", response_model=DomainResponse)
async def disable_domain(name: str, session: DBSession, user: _Admin) -> Domain:
    domain = await _get_domain_or_404(session, name)
    if domain.disabled_at is not None:
        raise HTTPException(status_code=409, detail="Domain is already disabled.")
    domain.disabled_at = func.now()
    await session.commit()
    await session.refresh(domain)
    return domain


@router.post("/domains/{name}/enable", response_model=DomainResponse)
async def enable_domain(name: str, session: DBSession, user: _Admin) -> Domain:
    domain = await _get_domain_or_404(session, name)
    if domain.disabled_at is None:
        raise HTTPException(status_code=409, detail="Domain is already active.")
    domain.disabled_at = None
    await session.commit()
    await session.refresh(domain)
    return domain


# ---------------------------------------------------------------------------
# User domain assignments
# ---------------------------------------------------------------------------

@router.get("/users/{user_id}/domains", response_model=list[UserDomainResponse])
async def get_user_domains(
    user_id: uuid.UUID, session: DBSession, _user: _Admin
) -> list[UserDomain]:
    result = await session.execute(
        select(UserDomain).where(UserDomain.user_id == user_id).order_by(UserDomain.domain)
    )
    return list(result.scalars().all())


@router.put("/users/{user_id}/domains", response_model=list[UserDomainResponse])
async def replace_user_domains(
    user_id: uuid.UUID,
    body: UserDomainsReplace,
    session: DBSession,
    user: _Admin,
) -> list[UserDomain]:
    target = await session.get(User, user_id)
    if target is None:
        raise HTTPException(status_code=404, detail="User not found.")

    existing = (
        await session.execute(
            select(UserDomain).where(UserDomain.user_id == user_id)
        )
    ).scalars().all()
    for row in existing:
        await session.delete(row)

    new_rows = []
    for domain_name in body.domains:
        row = UserDomain(user_id=user_id, domain=domain_name, created_by=user.id)
        session.add(row)
        new_rows.append(row)

    try:
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise HTTPException(
            status_code=422, detail="One or more domain names are invalid."
        ) from exc

    return new_rows


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------

@router.get("/health", response_model=HealthResponse)
async def admin_health(session: DBSession, _user: _Admin) -> HealthResponse:
    db_ok = True
    try:
        await session.execute(text("SELECT 1"))
    except Exception:
        db_ok = False

    migration_head: str | None = None
    try:
        row = (await session.execute(
            text("SELECT version_num FROM alembic_version LIMIT 1")
        )).fetchone()
        migration_head = row[0] if row else None
    except ProgrammingError:
        pass

    error_count = (
        await session.execute(
            select(func.count()).select_from(Notification).where(
                Notification.delivery_error.is_not(None)
            )
        )
    ).scalar_one()

    return HealthResponse(
        status="ok" if db_ok else "degraded",
        db_ok=db_ok,
        migration_head=migration_head,
        undelivered_notification_errors=error_count,
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _get_domain_or_404(session: AsyncSession, name: str) -> Domain:
    domain = await session.get(Domain, name)
    if domain is None:
        raise HTTPException(status_code=404, detail="Domain not found.")
    return domain
