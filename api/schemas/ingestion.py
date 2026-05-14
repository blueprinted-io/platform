"""Pydantic schemas for ingestion pipeline API (§11)."""

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel


class IngestionChunkResponse(BaseModel):
    """Per-chunk summary shown on the section selection screen (§11.5)."""

    model_config = {"from_attributes": True}

    id: uuid.UUID
    chunk_index: int
    section_title: str | None
    section_level: int
    pages_json: list[int] | None
    text_preview: str
    word_count: int
    chunk_status: str
    is_scanned: bool
    candidate_count: int


class IngestionResponse(BaseModel):
    """Ingestion job summary returned on create and status endpoints."""

    model_config = {"from_attributes": True}

    id: uuid.UUID
    source_type: str
    status: str
    created_by: uuid.UUID
    created_at: datetime
    updated_at: datetime
    original_filename: str | None
    source_url: str | None
    page_count: int | None
    chunk_count: int | None
    error_detail: str | None


class IngestionStatusResponse(IngestionResponse):
    """Ingestion status with full chunk list (GET /ingestions/{id}/status)."""

    chunks: list[IngestionChunkResponse]


class SelectChunksRequest(BaseModel):
    """Body for POST /ingestions/{id}/select (§11.5)."""

    chunk_ids: list[uuid.UUID]


class SelectChunksResponse(BaseModel):
    """Response for POST /ingestions/{id}/select."""

    queued_count: int
    ingestion_id: uuid.UUID


class IngestionCandidateResponse(BaseModel):
    """Single candidate awaiting human review (§11.8)."""

    model_config = {"from_attributes": True}

    id: uuid.UUID
    ingestion_id: uuid.UUID
    chunk_id: uuid.UUID | None
    record_type: str
    proposed_json: dict[str, Any]
    candidate_status: str
    review_note: str | None
    committed_record_id: uuid.UUID | None
