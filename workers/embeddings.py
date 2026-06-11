"""Embedding generation job (§12.1, §14). Runs on the default worker."""

import uuid

import httpx
import sqlalchemy as sa
import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession
from sqlalchemy.orm import selectinload

from api.config import Settings
from api.models.principle import Principle
from api.models.task import Task
from api.models.workflow import Workflow
from api.services.settings_service import load_llm_settings
from workers.common import exc_str

log = structlog.get_logger(__name__)

_TABLE_FOR_TYPE: dict[str, str] = {
    "principle": "principles",
    "task": "tasks",
    "workflow": "workflows",
}


async def _fetch_record_text(
    session: AsyncSession, record_type: str, record_id: str
) -> str | None:
    """Return the text to embed for the given record, or None if not found."""
    rid = uuid.UUID(record_id)

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
    # CAST() form required — asyncpg rejects :param::type syntax as a syntax error.
    await session.execute(
        sa.text(f"UPDATE {table} SET embedding = CAST(:embedding AS vector) WHERE id = :id"),  # noqa: S608
        {"embedding": str(embedding), "id": uuid.UUID(record_id)},
    )


async def generate_embedding(ctx: dict, record_type: str, record_id: str) -> None:  # type: ignore[type-arg]
    """Generate and store an embedding for the given record (§12.1, §14).

    Triggered on every confirmed state transition. If the embedding endpoint
    is not configured, the job logs a warning and exits cleanly — the record
    remains discoverable via tsvector full-text search.
    """
    env_settings: Settings = ctx["settings"]
    engine: AsyncEngine = ctx["db_engine"]

    async with AsyncSession(engine) as session:
        llm = await load_llm_settings(
            session, env_settings.app_secret_key.get_secret_value(), env_settings
        )
        record_text = await _fetch_record_text(session, record_type, record_id)

    if not llm.embedding_base_url or not llm.embedding_model:
        log.warning(
            "embedding_skipped_no_config",
            record_type=record_type,
            record_id=record_id,
        )
        return

    if record_text is None:
        log.warning(
            "embedding_record_not_found",
            record_type=record_type,
            record_id=record_id,
        )
        return

    headers: dict[str, str] = {"Content-Type": "application/json"}
    if llm.embedding_api_key:
        headers["Authorization"] = f"Bearer {llm.embedding_api_key}"

    try:
        async with httpx.AsyncClient() as http:
            response = await http.post(
                f"{llm.embedding_base_url}/embeddings",
                json={"model": llm.embedding_model, "input": record_text},
                headers=headers,
                timeout=llm.embedding_timeout,
            )
            response.raise_for_status()
        embedding: list[float] = response.json()["data"][0]["embedding"]
    except Exception as exc:
        log.error(
            "embedding_api_failed",
            record_type=record_type,
            record_id=record_id,
            error=exc_str(exc),
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
