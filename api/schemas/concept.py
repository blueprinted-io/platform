"""Concept request and response schemas."""

from pydantic import BaseModel

from api.schemas.base import LifecycleResponse


class ConceptCreate(BaseModel):
    title: str
    summary: str
    explanation: str
    analogies: str | None = None
    tags: list[str] = []


class ConceptUpdate(BaseModel):
    title: str | None = None
    summary: str | None = None
    explanation: str | None = None
    analogies: str | None = None
    tags: list[str] | None = None


class ReturnRequest(BaseModel):
    note: str | None = None


class ConceptResponse(LifecycleResponse):
    title: str
    summary: str
    explanation: str
    analogies: str | None
    tags: list[str]
