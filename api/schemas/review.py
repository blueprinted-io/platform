"""Pydantic schemas for the Review Queue and Claiming API.

§8.1 — Global Review Queue
§8.2 — Claiming Model
"""

import uuid
from datetime import datetime

from pydantic import BaseModel


class ClaimInfo(BaseModel):
    """Active claim summary embedded in queue items."""

    claimed_by: uuid.UUID
    expires_at: datetime


class ReviewQueueItem(BaseModel):
    """One item in the global review queue."""

    model_config = {"from_attributes": True}

    id: uuid.UUID
    record_type: str
    title: str
    domain: str | None
    status: str
    updated_at: datetime
    created_by: uuid.UUID
    claim: ClaimInfo | None = None


class ReviewQueueResponse(BaseModel):
    """Paginated review queue response."""

    items: list[ReviewQueueItem]
    total: int


class ClaimResponse(BaseModel):
    """Response body for claim and release operations."""

    model_config = {"from_attributes": True}

    id: uuid.UUID
    entity_type: str
    entity_id: uuid.UUID
    claimed_by: uuid.UUID
    claimed_at: datetime
    expires_at: datetime
    released_at: datetime | None


class ReviewReturnRequest(BaseModel):
    """Optional body for review return operations."""

    note: str | None = None


class ReviewActionResponse(BaseModel):
    """Minimal response for review confirm/return actions."""

    id: uuid.UUID
    record_type: str
    status: str
