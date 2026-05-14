"""Pydantic schemas for ingestion pipeline API (§11)."""

import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, field_validator


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
    reviewed_by: uuid.UUID | None
    reviewed_at: datetime | None


class CandidateReviewRequest(BaseModel):
    """Body for PATCH /ingestions/{id}/candidates/{candidate_id}."""

    action: Literal["accept", "discard"]
    proposed_json: dict[str, Any] | None = None
    review_note: str | None = None


class CandidateCommitRequest(BaseModel):
    """Body for POST /ingestions/{id}/candidates/{candidate_id}/commit."""

    domain: str
    target_status: Literal["draft", "submitted"] = "draft"


class CandidateCommitResponse(BaseModel):
    """Response from the commit endpoint."""

    candidate_id: uuid.UUID
    committed_record_id: uuid.UUID
    record_type: str
    target_status: str


# ---------------------------------------------------------------------------
# HTML ingestion schemas (§11.10, §11.11)
# ---------------------------------------------------------------------------


class HtmlIngestionRequest(BaseModel):
    """Body for POST /ingestions/html (§11.10)."""

    url: str
    mode: Literal["single", "site-nav"] = "single"
    force: bool = False

    @field_validator("url")
    @classmethod
    def url_must_be_http(cls, v: str) -> str:
        if not v.startswith(("http://", "https://")):
            raise ValueError("URL scheme must be http:// or https://")
        return v


class NavPageResponse(BaseModel):
    """A discovered nav page from an HTML site-nav crawl (§11.11, §11.15)."""

    model_config = {"from_attributes": True}

    id: uuid.UUID
    ingestion_id: uuid.UUID
    url: str
    title: str | None
    nav_level: int
    parent_id: uuid.UUID | None
    nav_status: str
    error_detail: str | None
    chunk_count: int


class NavSelectRequest(BaseModel):
    """Body for POST /ingestions/{id}/nav-select (§11.11)."""

    nav_page_ids: list[uuid.UUID]


class NavSelectResponse(BaseModel):
    """Response for POST /ingestions/{id}/nav-select."""

    queued_count: int
    ingestion_id: uuid.UUID


# ---------------------------------------------------------------------------
# JSON ingestion schemas (§11.12)
# ---------------------------------------------------------------------------


class JsonStepItem(BaseModel):
    """One step within a task item in the JSON import payload."""

    id: str
    text: str
    completion: str
    actions: list[str]
    notes: str | None


class JsonTaskItem(BaseModel):
    """Task object in the JSON import payload (§11.12, json_import_schema_spec.md)."""

    type: Literal["task"]
    title: str
    outcome: str
    software_name: str | None
    software_version: str | None
    procedure_name: str
    domain: str
    facts: list[str]
    concepts: list[str]
    dependencies: list[str]
    irreversible: bool
    task_order: list[str]
    steps: list[JsonStepItem]

    @field_validator("steps")
    @classmethod
    def steps_not_empty(cls, v: list[JsonStepItem]) -> list[JsonStepItem]:
        if not v:
            raise ValueError("steps must not be empty")
        return v


class JsonPrincipleItem(BaseModel):
    """Principle object in the JSON import payload."""

    type: Literal["principle"]
    title: str
    summary: str
    explanation: str
    analogies: str | None
    software_name: str | None
    software_version: str | None
    domain: str


JsonImportItem = JsonTaskItem | JsonPrincipleItem


class JsonIngestionRequest(BaseModel):
    """Body for POST /ingestions/json (§11.12)."""

    schema_version: str
    items: list[JsonImportItem]

    @field_validator("schema_version")
    @classmethod
    def version_must_be_supported(cls, v: str) -> str:
        if v != "1.0":
            raise ValueError(f"Unsupported schema_version '{v}'. Only '1.0' is accepted.")
        return v

    @field_validator("items")
    @classmethod
    def items_not_empty(cls, v: list[JsonImportItem]) -> list[JsonImportItem]:
        if not v:
            raise ValueError("items must contain at least one object")
        return v

    # Note: the spec requires task_order cross-references to resolve within the payload,
    # but the JSON import schema defines no top-level id field on task items. Cross-payload
    # reference validation is therefore not implementable in v1; task_order is accepted as
    # an opaque string array and not persisted.
