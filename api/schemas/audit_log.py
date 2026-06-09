"""Audit log Pydantic schemas (§9.6)."""

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel


class AuditLogResponse(BaseModel):
    id: uuid.UUID
    event_type: str
    actor_id: uuid.UUID
    actor_type: str
    target_id: uuid.UUID | None
    target_type: str | None
    detail: dict[str, Any]
    created_at: datetime

    model_config = {"from_attributes": True}
