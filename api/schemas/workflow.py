"""Workflow request and response schemas."""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from api.schemas.base import LifecycleResponse


class WorkflowTaskRefCreate(BaseModel):
    task_record_id: uuid.UUID


class WorkflowTaskRefResponse(BaseModel):
    task_record_id: uuid.UUID
    order_index: int

    model_config = ConfigDict(from_attributes=True)


class WorkflowPrincipleRefCreate(BaseModel):
    principle_record_id: uuid.UUID


class WorkflowPrincipleRefResponse(BaseModel):
    principle_record_id: uuid.UUID
    attached_at: datetime
    attached_by: uuid.UUID

    model_config = ConfigDict(from_attributes=True)


class WorkflowCreate(BaseModel):
    title: str
    objective: str
    domain: str | None = None
    tags: list[str] = []


class WorkflowUpdate(BaseModel):
    title: str | None = None
    objective: str | None = None
    domain: str | None = None
    tags: list[str] | None = None


class ReturnRequest(BaseModel):
    note: str | None = None


class WorkflowResponse(LifecycleResponse):
    title: str
    objective: str
    domain: str | None
    tags: list[str]
    has_incoming_task_change: bool
    has_pending_task_confirm: bool
    task_refs: list[WorkflowTaskRefResponse]
    principle_refs: list[WorkflowPrincipleRefResponse]
