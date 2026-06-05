"""Relationship response schema. §9.4"""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class RelationshipResponse(BaseModel):
    id: uuid.UUID
    source_id: uuid.UUID
    source_type: str
    target_id: uuid.UUID
    target_type: str
    kind: str
    created_at: datetime
    created_by: uuid.UUID
    agent_suggested: bool
    note: str | None = None

    model_config = ConfigDict(from_attributes=True)
