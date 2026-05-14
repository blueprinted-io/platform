"""Search API endpoint (§12.2).

GET /api/v1/search  — full-text and optional semantic search across all confirmed
                      governed records. Any authenticated user may search.
"""

from typing import Annotated

import structlog
from fastapi import APIRouter, Query

from api.dependencies import AppSettings, CurrentUser, DBSession
from api.schemas.search import SearchResponse
from api.services.search import _VALID_TYPES, run_search

log = structlog.get_logger(__name__)

router = APIRouter(prefix="/search", tags=["search"])

_MAX_LIMIT = 100
_DEFAULT_LIMIT = 20


@router.get("", response_model=SearchResponse)
async def search_records(
    q: Annotated[str, Query(min_length=1, description="Search query")],
    session: DBSession,
    user: CurrentUser,
    settings: AppSettings,
    type: Annotated[
        str | None,
        Query(description="Comma-separated record types: task,workflow,fact,concept,principle"),
    ] = None,
    domain: Annotated[str | None, Query(description="Filter by domain")] = None,
    status: Annotated[str, Query(description="Record status to search")] = "confirmed",
    semantic: Annotated[bool, Query(description="Enable semantic search")] = False,
    limit: Annotated[int, Query(ge=1, le=_MAX_LIMIT)] = _DEFAULT_LIMIT,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> SearchResponse:
    """Search across all governed record types.

    Full-text search is always performed. Semantic search (pgvector cosine
    similarity) is optional and requires embedding configuration.
    """
    record_types: list[str] | None = None
    if type is not None:
        requested = [t.strip().lower() for t in type.split(",") if t.strip()]
        record_types = [t for t in requested if t in _VALID_TYPES]

    log.info(
        "search_request",
        q=q,
        record_types=record_types,
        domain=domain,
        status=status,
        semantic=semantic,
        limit=limit,
        offset=offset,
        user_id=str(user.id),
    )

    return await run_search(
        session=session,
        settings=settings,
        q=q,
        record_types=record_types,
        domain=domain,
        status=status,
        semantic=semantic,
        limit=limit,
        offset=offset,
    )
