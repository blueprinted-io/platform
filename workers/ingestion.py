"""Ingestion ARQ worker entrypoint (§14).

Start with: arq workers.ingestion.WorkerSettings

Owns the ingestion pipeline jobs (PDF chunking, HTML crawling/rendering, LLM
triage and extraction) on the dedicated `ingestion` queue, isolating
long-running LLM work from the fast jobs on the default worker. Every enqueue
of these jobs must pass _queue_name=INGESTION_QUEUE.

The startup hook is LOAD-BEARING — do not remove. See §14 of the spec.
Without it, ingestion chunks left in `processing` state after a worker crash
are silently skipped on resume, producing missing candidates with no error.
It runs on this worker only; running it on both workers would double-enqueue
orphaned extraction jobs.

HTML ingestion jobs (crawl_html, render_nav_pages) require Playwright with
Chromium. Run `playwright install chromium` after installing dependencies.
"""

from typing import ClassVar

import sqlalchemy as sa
import structlog
from arq.connections import RedisSettings
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.config import get_settings
from api.models.ingestion import IngestionChunk
from workers.common import dispose_worker_ctx, init_worker_ctx
from workers.extraction import extract_chunk, process_chunks
from workers.ingestion_html import crawl_html, render_nav_pages
from workers.ingestion_pdf import chunk_pdf
from workers.queues import INGESTION_QUEUE

log = structlog.get_logger(__name__)


async def startup(ctx: dict) -> None:  # type: ignore[type-arg]
    """Ingestion worker startup hook — LOAD-BEARING, do not remove (§14).

    Initialises the database engine and resets any ingestion chunks left in
    `processing` state back to `queued` with a worker_restart note. This
    recovers from mid-execution crashes.
    """
    await init_worker_ctx(ctx)
    engine = ctx["db_engine"]

    # Reset any chunks left in `processing` state by a previous worker crash (§14).
    # Without this, crashed in-flight chunks are silently skipped on resume.
    async with AsyncSession(engine) as session:
        result = await session.execute(
            sa.text("""
                UPDATE ingestion_chunks
                SET chunk_status = 'queued',
                    error_detail  = 'Reset from processing state after worker restart'
                WHERE chunk_status = 'processing'
            """)
        )
        reset_count: int = result.rowcount  # type: ignore[attr-defined]
        await session.commit()

    if reset_count:
        log.warning("worker_startup_chunks_reset", count=reset_count)

    # Reset extracting → extraction_queued for chunks whose extract_chunk job
    # was mid-execution when the worker crashed (prevents duplicate candidates).
    async with AsyncSession(engine) as session:
        result2 = await session.execute(
            sa.text("""
                UPDATE ingestion_chunks
                SET chunk_status = 'extraction_queued',
                    error_detail  = 'Reset from extracting state after worker restart'
                WHERE chunk_status = 'extracting'
            """)
        )
        extracting_reset: int = result2.rowcount  # type: ignore[attr-defined]
        await session.commit()

    if extracting_reset:
        log.warning("worker_startup_extracting_reset", count=extracting_reset)

    # Re-enqueue extract_chunk jobs for extraction_queued chunks (covers both
    # chunks that were reset above and any whose ARQ job was lost before pickup).
    arq_pool = ctx.get("redis")
    if arq_pool is not None:
        async with AsyncSession(engine) as session:
            requeue_result = await session.execute(
                select(IngestionChunk).where(
                    IngestionChunk.chunk_status == "extraction_queued"
                )
            )
            orphaned = requeue_result.scalars().all()

        for chunk in orphaned:
            await arq_pool.enqueue_job(
                "extract_chunk", chunk_id=str(chunk.id), _queue_name=INGESTION_QUEUE
            )

        if orphaned:
            log.warning("worker_startup_extraction_requeued", count=len(orphaned))

    log.info("worker_ready", worker="ingestion")


async def shutdown(ctx: dict) -> None:  # type: ignore[type-arg]
    await dispose_worker_ctx(ctx)
    log.info("worker_shutdown", worker="ingestion")


class WorkerSettings:
    """ARQ ingestion worker configuration."""

    queue_name: ClassVar[str] = INGESTION_QUEUE

    functions: ClassVar[list[object]] = [
        chunk_pdf,
        process_chunks,
        extract_chunk,
        crawl_html,
        render_nav_pages,
    ]

    on_startup = startup
    on_shutdown = shutdown

    redis_settings: ClassVar[RedisSettings] = RedisSettings.from_dsn(
        get_settings().redis_url
    )
