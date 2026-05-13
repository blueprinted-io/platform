"""Pydantic schemas for user API responses."""

import uuid
from datetime import datetime

from pydantic import BaseModel


class UserResponse(BaseModel):
    """Response schema for GET /api/v1/users/me."""

    id: uuid.UUID
    sub: str
    email: str
    display_name: str | None
    roles: list[str]
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
