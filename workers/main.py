"""ARQ worker entrypoint.

Start with: arq workers.main.WorkerSettings

The startup hook is LOAD-BEARING — do not remove. See §14 of the spec.
Without it, ingestion chunks left in `processing` state after a worker crash
are silently skipped on resume, producing missing candidates with no error.
"""

import uuid
from typing import ClassVar

import httpx
import sqlalchemy as sa
import structlog
from arq.connections import RedisSettings
from arq.cron import CronJob, cron
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession
from sqlalchemy.orm import selectinload

from api.config import Settings, get_settings
from api.database import create_engine
from api.logging import configure_logging
from api.models.concept import Concept
from api.models.fact import Fact
from api.models.principle import Principle
from api.models.task import Task
from api.models.workflow import Workflow

log = structlog.get_logger(__name__)

_TABLE_FOR_TYPE: dict[str, str] = {
    "fact": "facts",
    "concept": "concepts",
    "principle": "principles",
    "task": "tasks",
    "workflow": "workflows",
}


async def _fetch_record_text(
    session: AsyncSession, record_type: str, record_id: str
) -> str | None:
    """Return the text to embed for the given record, or None if not found."""
    rid = uuid.UUID(record_id)

    if record_type == "fact":
        fact = (await session.execute(select(Fact).where(Fact.id == rid))).scalar_one_or_none()
        return f"{fact.title}. {fact.body}" if fact else None

    if record_type == "concept":
        concept = (
            await session.execute(select(Concept).where(Concept.id == rid))
        ).scalar_one_or_none()
        return f"{concept.title}. {concept.summary}. {concept.explanation}" if concept else None

    if record_type == "principle":
        principle = (
            await session.execute(select(Principle).where(Principle.id == rid))
        ).scalar_one_or_none()
        if principle is None:
            return None
        return f"{principle.title}. {principle.summary}. {principle.explanation}"

    if record_type == "task":
        task = (
            await session.execute(
                select(Task).where(Task.id == rid).options(selectinload(Task.steps))
            )
        ).scalar_one_or_none()
        if task is None:
            return None
        steps_text = " ".join(step.step for step in task.steps)
        parts = [task.title, task.outcome, steps_text]
        return ". ".join(p for p in parts if p)

    if record_type == "workflow":
        workflow = (
            await session.execute(select(Workflow).where(Workflow.id == rid))
        ).scalar_one_or_none()
        return f"{workflow.title}. {workflow.objective}" if workflow else None

    log.warning("embedding_unknown_record_type", record_type=record_type)
    return None


async def _store_embedding(
    session: AsyncSession, record_type: str, record_id: str, embedding: list[float]
) -> None:
    """Write the embedding vector to the record's embedding column."""
    table = _TABLE_FOR_TYPE.get(record_type)
    if table is None:
        log.warning("embedding_unknown_type_store", record_type=record_type)
        return
    # table comes from a hardcoded dict — not user input, so f-string is safe.
    await session.execute(
        sa.text(f"UPDATE {table} SET embedding = :embedding::vector WHERE id = :id"),  # noqa: S608
        {"embedding": str(embedding), "id": uuid.UUID(record_id)},
    )


async def generate_embedding(ctx: dict, record_type: str, record_id: str) -> None:  # type: ignore[type-arg]
    """Generate and store an embedding for the given record (§12.1, §14).

    Triggered on every confirmed state transition. If the embedding endpoint
    is not configured, the job logs a warning and exits cleanly — the record
    remains discoverable via tsvector full-text search.
    """
    settings: Settings = ctx["settings"]
    engine: AsyncEngine = ctx["db_engine"]

    if not settings.llm_embedding_base_url or not settings.llm_embedding_model:
        log.warning(
            "embedding_skipped_no_config",
            record_type=record_type,
            record_id=record_id,
        )
        return

    async with AsyncSession(engine) as session:
        text = await _fetch_record_text(session, record_type, record_id)

    if text is None:
        log.warning(
            "embedding_record_not_found",
            record_type=record_type,
            record_id=record_id,
        )
        return

    headers: dict[str, str] = {"Content-Type": "application/json"}
    api_key = settings.llm_embedding_api_key.get_secret_value()
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    try:
        async with httpx.AsyncClient() as http:
            response = await http.post(
                f"{settings.llm_embedding_base_url}/embeddings",
                json={"model": settings.llm_embedding_model, "input": text},
                headers=headers,
                timeout=settings.llm_embedding_timeout_seconds,
            )
            response.raise_for_status()
        embedding: list[float] = response.json()["data"][0]["embedding"]
    except Exception as exc:
        log.error(
            "embedding_api_failed",
            record_type=record_type,
            record_id=record_id,
            error=str(exc),
        )
        raise

    async with AsyncSession(engine) as session:
        await _store_embedding(session, record_type, record_id, embedding)
        await session.commit()

    log.info(
        "embedding_generated",
        record_type=record_type,
        record_id=record_id,
        dims=len(embedding),
    )


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
