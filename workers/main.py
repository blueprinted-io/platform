"""ARQ worker entrypoint.

Start with: arq workers.main.WorkerSettings

The startup hook is LOAD-BEARING — do not remove. See §14 of the spec.
Without it, ingestion chunks left in `processing` state after a worker crash
are silently skipped on resume, producing missing candidates with no error.
"""

from typing import ClassVar

import structlog
from arq.connections import RedisSettings

from api.config import get_settings
from api.logging import configure_logging

log = structlog.get_logger(__name__)


async def generate_embedding(ctx: dict, record_type: str, record_id: str) -> None:  # type: ignore[type-arg]
    """Triggered on every confirmed state transition (§12.1, §14).

    Sprint 7 replaces this stub with the actual LLM embedding call.
    """
    log.info("embedding_job_noop", record_type=record_type, record_id=record_id)


async def startup(ctx: dict) -> None:  # type: ignore[type-arg]
    """Worker startup hook — LOAD-BEARING, do not remove (§14).

    Resets any ingestion chunks left in `processing` state back to `queued`
    with a worker_restart note. This recovers from mid-execution crashes.

    Sprint 4: implement the actual reset query once ingestion_chunks table exists.
    """
    settings = get_settings()
    configure_logging(settings.log_level)

    log.info("worker_starting")

    # Sprint 4: add database engine initialisation and the chunk reset query here.
    # The structure is intentional — placeholder code makes the load-bearing
    # nature of this hook visible and prevents accidental removal during refactoring.
    log.info(
        "worker_startup_hook_ran",
        note="chunk reset not yet implemented — Sprint 4",
    )

    ctx["settings"] = settings
    log.info("worker_ready")


async def shutdown(ctx: dict) -> None:  # type: ignore[type-arg]
    log.info("worker_shutdown")


class WorkerSettings:
    """ARQ worker configuration."""

    functions: ClassVar[list[object]] = [generate_embedding]

    on_startup = startup
    on_shutdown = shutdown

    @property
    def redis_settings(self) -> RedisSettings:
        settings = get_settings()
        return RedisSettings.from_dsn(settings.redis_url)
