"""Principle request and response schemas."""

import uuid

from pydantic import BaseModel, ConfigDict

from api.schemas.base import LifecycleResponse


class PrincipleCreate(BaseModel):
    title: str
    summary: str
    explanation: str
    analogies: str | None = None
    domain: str
    tags: list[str] = []


class PrincipleUpdate(BaseModel):
    title: str | None = None
    summary: str | None = None
    explanation: str | None = None
    analogies: str | None = None
    domain: str | None = None
    tags: list[str] | None = None


class ReturnRequest(BaseModel):
    note: str | None = None


class ReviseRequest(BaseModel):
    note: str | None = None


class PrincipleVersionSummary(BaseModel):
    id: uuid.UUID
    version: int
    status: str

    model_config = ConfigDict(from_attributes=True)


class PrincipleResponse(LifecycleResponse):
    title: str
    summary: str
    explanation: str
    analogies: str | None
    domain: str
    tags: list[str]
    ingestion_id: uuid.UUID | None
