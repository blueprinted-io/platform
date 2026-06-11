"""Shared worker plumbing: ctx init/teardown and error formatting."""

import structlog
from sqlalchemy.ext.asyncio import AsyncEngine

from api.config import get_settings
from api.database import create_engine
from api.logging import configure_logging

log = structlog.get_logger(__name__)


def exc_str(exc: BaseException) -> str:
    """Return a non-empty string describing an exception.

    Some httpx exceptions (e.g. RemoteProtocolError) have an empty str(); fall
    back to repr() so error_detail is never stored as an empty string.
    """
    return str(exc) or repr(exc)


async def init_worker_ctx(ctx: dict) -> None:  # type: ignore[type-arg]
    """Initialise settings, logging, and the database engine on the worker ctx."""
    settings = get_settings()
    configure_logging(settings.log_level)
    ctx["settings"] = settings
    ctx["db_engine"] = create_engine(settings)


async def dispose_worker_ctx(ctx: dict) -> None:  # type: ignore[type-arg]
    """Dispose the database engine created by init_worker_ctx."""
    engine: AsyncEngine | None = ctx.get("db_engine")
    if engine is not None:
        await engine.dispose()
