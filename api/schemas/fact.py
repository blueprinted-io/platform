"""Fact request and response schemas."""

from pydantic import BaseModel

from api.schemas.base import LifecycleResponse


class FactCreate(BaseModel):
    title: str
    body: str
    tags: list[str] = []


class FactUpdate(BaseModel):
    title: str | None = None
    body: str | None = None
    tags: list[str] | None = None


class ReturnRequest(BaseModel):
    note: str | None = None


class FactResponse(LifecycleResponse):
    title: str
    body: str
    tags: list[str]
