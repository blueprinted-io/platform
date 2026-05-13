"""ARQ worker entrypoint.

Start with: arq workers.main.WorkerSettings

The startup hook is LOAD-BEARING — do not remove. See §14 of the spec.
Without it, ingestion chunks left in `processing` state after a worker crash
are silently skipped on resume, producing missing candidates with no error.
"""

from typing import ClassVar

import sqlalchemy as sa
import structlog
from arq.connections import RedisSettings
from arq.cron import CronJob, cron
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

from api.config import get_settings
from api.database import create_engine
from api.logging import configure_logging

log = structlog.get_logger(__name__)


async def generate_embedding(ctx: dict, record_type: str, record_id: str) -> None:  # type: ignore[type-arg]
    """Triggered on every confirmed state transition (§12.1, §14).

    Sprint 7 replaces this stub with the actual LLM embedding call.
    """
    log.info("embedding_job_noop", record_type=record_type, record_id=record_id)


async def expire_review_claims(ctx: dict) -> None:  # type: ignore[type-arg]
    """Release review claims whose expiry has passed (§8.2, §14).

    Runs every 15 minutes via cron. Sets released_at on any claim where
    released_at IS NULL AND expires_at < NOW().
    """
    engine: AsyncEngine = ctx["db_engine"]
    async with AsyncSession(engine) as session:
        result = await session.execute(
            sa.text("""
                UPDATE review_claims
                SET released_at = NOW()
                WHERE released_at IS NULL
                  AND expires_at < NOW()
            """)
        )
        expired_count: int = result.rowcount  # type: ignore[attr-defined]
        await session.commit()

    if expired_count:
        log.info("review_claims_expired", count=expired_count)


async def startup(ctx: dict) -> None:  # type: ignore[type-arg]
    """Worker startup hook — LOAD-BEARING, do not remove (§14).

    Initialises the database engine and resets any ingestion chunks left in
    `processing` state back to `queued` with a worker_restart note. This
    recovers from mid-execution crashes.

    The chunk reset query is implemented in Sprint 6 once the ingestion_chunks
    table exists.
    """
    settings = get_settings()
    configure_logging(settings.log_level)

    log.info("worker_starting")

    engine = create_engine(settings)
    ctx["settings"] = settings
    ctx["db_engine"] = engine

    # Sprint 6: reset ingestion_chunks in `processing` state to `queued` here.
    # Structure is intentional — the placeholder keeps the hook load-bearing and
    # visible so it is not accidentally removed during refactoring.
    log.info("worker_startup_hook_ran", note="chunk reset not yet implemented — Sprint 6")

    log.info("worker_ready")


async def shutdown(ctx: dict) -> None:  # type: ignore[type-arg]
    engine: AsyncEngine | None = ctx.get("db_engine")
    if engine is not None:
        await engine.dispose()
    log.info("worker_shutdown")


class WorkerSettings:
    """ARQ worker configuration."""

    functions: ClassVar[list[object]] = [generate_embedding, expire_review_claims]

    cron_jobs: ClassVar[list[CronJob]] = [
        # expire_review_claims fires at minute 0, 15, 30, 45 of every hour (§14)
        cron(expire_review_claims, minute={0, 15, 30, 45}),
    ]

    on_startup = startup
    on_shutdown = shutdown

    @property
    def redis_settings(self) -> RedisSettings:
        settings = get_settings()
        return RedisSettings.from_dsn(settings.redis_url)
