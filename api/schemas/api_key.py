"""API key Pydantic schemas (§5.3, §9.6)."""

import uuid
from datetime import datetime

from pydantic import BaseModel

from api.auth import AgentRole


class ApiKeyCreate(BaseModel):
    name: str
    role: AgentRole


class ApiKeyResponse(BaseModel):
    id: uuid.UUID
    name: str
    key_prefix: str
    role: str
    created_by: uuid.UUID
    created_at: datetime
    last_used_at: datetime | None
    revoked_at: datetime | None

    model_config = {"from_attributes": True}


class ApiKeyCreatedResponse(ApiKeyResponse):
    """Returned only on creation — includes the raw key shown once."""

    raw_key: str
