"""Pydantic schemas for triage estimate review endpoints (§11.5a)."""

import uuid

from pydantic import BaseModel


class TriageEstimateResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    ingestion_id: uuid.UUID
    chunk_id: uuid.UUID
    record_type: str
    approved_type: str
    estimated_title: str
    estimate_status: str
    merged_into_id: uuid.UUID | None
    sort_order: int


class TriageEstimatePatchRequest(BaseModel):
    """PATCH body — any combination of fields; omitted fields are unchanged."""

    approved_type: str | None = None
    estimated_title: str | None = None
    estimate_status: str | None = None  # only 'rejected' is valid via PATCH


class TriageEstimateMergeRequest(BaseModel):
    estimate_ids: list[uuid.UUID]
    merged_title: str


class TriageEstimateMergeResponse(BaseModel):
    surviving_id: uuid.UUID


class TriageEstimateApproveResponse(BaseModel):
    extraction_queued: int
