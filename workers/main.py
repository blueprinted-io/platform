"""Default ARQ worker entrypoint (§14).

Start with: arq workers.main.WorkerSettings

Owns fast jobs: embedding generation and the review-claim-expiry cron.
Ingestion jobs run on the dedicated ingestion worker — see workers/ingestion.py.
"""

from typing import ClassVar

import structlog
from arq.connections import RedisSettings
from arq.cron import CronJob, cron

from api.config import get_settings
from workers.common import dispose_worker_ctx, init_worker_ctx
from workers.embeddings import generate_embedding
from workers.maintenance import expire_review_claims

log = structlog.get_logger(__name__)


async def startup(ctx: dict) -> None:  # type: ignore[type-arg]
    """Initialise settings, logging, and the database engine."""
    await init_worker_ctx(ctx)
    log.info("worker_ready", worker="default")


async def shutdown(ctx: dict) -> None:  # type: ignore[type-arg]
    await dispose_worker_ctx(ctx)
    log.info("worker_shutdown", worker="default")


class WorkerSettings:
    """ARQ default worker configuration."""

    functions: ClassVar[list[object]] = [
        generate_embedding,
        expire_review_claims,
    ]

    cron_jobs: ClassVar[list[CronJob]] = [
        # expire_review_claims fires at minute 0, 15, 30, 45 of every hour (§14)
        cron(expire_review_claims, minute={0, 15, 30, 45}),
    ]

    on_startup = startup
    on_shutdown = shutdown

    redis_settings: ClassVar[RedisSettings] = RedisSettings.from_dsn(
        get_settings().redis_url
    )
