"""Pydantic schemas for notifications API (§13)."""

import uuid
from datetime import datetime

from pydantic import BaseModel


class NotificationResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    kind: str
    entity_type: str
    entity_id: uuid.UUID
    message: str
    created_at: datetime
    read_at: datetime | None
