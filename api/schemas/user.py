"""Pydantic schemas for user API responses."""

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, field_validator

ALLOWED_LOCALES = {"en", "fr", "de", "es", "pt", "ja", "zh"}


class UserPreferencesUpdate(BaseModel):
    """Body for PATCH /api/v1/users/me/preferences."""

    locale: str | None = None
    notifications: dict[str, Any] | None = None

    @field_validator("locale")
    @classmethod
    def locale_must_be_known(cls, v: str | None) -> str | None:
        if v is not None and v not in ALLOWED_LOCALES:
            raise ValueError(f"locale '{v}' is not supported; allowed: {sorted(ALLOWED_LOCALES)}")
        return v


class UserResponse(BaseModel):
    """Response schema for GET /api/v1/users/me."""

    id: uuid.UUID
    sub: str
    email: str
    display_name: str | None
    roles: list[str]
    preferences: dict[str, Any]
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
