"""Shared lifecycle response schema for all governed record types.

§9.1 — identity fields (id, record_id, version)
§9.2 — lifecycle fields
"""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class LifecycleResponse(BaseModel):
    """Base response schema carrying the shared identity and lifecycle fields."""

    id: uuid.UUID
    record_id: uuid.UUID
    version: int
    status: str
    created_at: datetime
    updated_at: datetime
    created_by: uuid.UUID

    model_config = ConfigDict(from_attributes=True)
