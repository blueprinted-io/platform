"""Search API schemas (§12.2)."""

import uuid
from typing import Literal

from pydantic import BaseModel


class SearchResult(BaseModel):
    id: uuid.UUID              # version-specific primary key (for record fetch)
    record_id: uuid.UUID       # stable cross-version identifier
    record_type: str
    version: int
    title: str
    status: str
    domain: str | None
    match_type: Literal["fulltext", "semantic", "hybrid"]
    score: float
    excerpt: str


class SearchResponse(BaseModel):
    results: list[SearchResult]
    total: int
    semantic_available: bool
