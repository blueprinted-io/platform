"""Schemas for Admin API endpoints (§23.11)."""

import uuid
from datetime import datetime

from pydantic import BaseModel

# ---------------------------------------------------------------------------
# System settings
# ---------------------------------------------------------------------------

class SettingResponse(BaseModel):
    key: str
    value: str | None  # None for encrypted keys (value is write-only)
    encrypted: bool
    updated_at: datetime
    updated_by_id: uuid.UUID | None

    model_config = {"from_attributes": True}


class SettingPatch(BaseModel):
    value: str | None = None
    encrypted: bool = False


class SettingsBatchPatch(BaseModel):
    settings: dict[str, SettingPatch]


# ---------------------------------------------------------------------------
# Domains
# ---------------------------------------------------------------------------

class DomainResponse(BaseModel):
    name: str
    created_at: datetime
    created_by: uuid.UUID
    disabled_at: datetime | None

    model_config = {"from_attributes": True}


class DomainCreate(BaseModel):
    name: str


# ---------------------------------------------------------------------------
# User domain assignments
# ---------------------------------------------------------------------------

class UserDomainResponse(BaseModel):
    user_id: uuid.UUID
    domain: str
    created_at: datetime

    model_config = {"from_attributes": True}


class UserDomainsReplace(BaseModel):
    domains: list[str]


# ---------------------------------------------------------------------------
# LLM connection test
# ---------------------------------------------------------------------------

class TestConnectionRequest(BaseModel):
    base_url: str
    api_key: str = ""
    # If api_key is blank, the backend decrypts and uses this system_settings key instead.
    api_key_setting: str = ""


class TestConnectionResponse(BaseModel):
    ok: bool
    models: list[str]
    error: str | None = None


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------

class HealthResponse(BaseModel):
    status: str
    db_ok: bool
    migration_head: str | None
    undelivered_notification_errors: int
