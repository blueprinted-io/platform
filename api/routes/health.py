"""GET /healthz — public endpoint, no auth required.

Checks database connectivity and reports the current Alembic migration version.
Returns 200 if the DB is reachable (migration version is informational).
Returns 503 if the database is unreachable.
"""

import structlog
from fastapi import APIRouter, status
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.exc import ProgrammingError

from api.dependencies import DBSession

router = APIRouter()
log = structlog.get_logger(__name__)


@router.get("/healthz", include_in_schema=False)
async def healthz(session: DBSession) -> JSONResponse:
    try:
        await session.execute(text("SELECT 1"))
    except Exception as exc:
        log.error("healthz_db_error", error=str(exc))
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={"status": "unhealthy", "database": "unreachable"},
        )

    # Migration version is informational — absence of the table is not an error
    try:
        result = await session.execute(
            text("SELECT version_num FROM alembic_version LIMIT 1")
        )
        row = result.fetchone()
        migration_version = row[0] if row else "no_migrations_applied"
    except ProgrammingError:
        migration_version = "no_migrations_applied"

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={"status": "ok", "migration_version": migration_version},
    )
