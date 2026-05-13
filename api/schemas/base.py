"""Shared lifecycle response schema for all governed record types.

§9.1 — identity fields (id, record_id, version)
§9.2 — lifecycle fields
§5.1 — break-glass confirm request
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
    self_confirmed_by_admin: bool

    model_config = ConfigDict(from_attributes=True)


class ConfirmRequest(BaseModel):
    """Optional body for confirm endpoints.

    justification is required (non-empty) only when an admin confirms their own
    content (§5.1 break-glass). For normal confirms the body may be omitted entirely
    or sent with justification=None.
    """

    justification: str | None = None
