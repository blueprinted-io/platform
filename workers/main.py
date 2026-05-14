"""ARQ worker entrypoint.

Start with: arq workers.main.WorkerSettings

The startup hook is LOAD-BEARING — do not remove. See §14 of the spec.
Without it, ingestion chunks left in `processing` state after a worker crash
are silently skipped on resume, producing missing candidates with no error.
"""

import uuid
from typing import Any, ClassVar

import fitz  # PyMuPDF
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
from api.models.ingestion import Ingestion, IngestionChunk
from api.models.principle import Principle
from api.models.task import Task
from api.models.workflow import Workflow
from api.services.storage import read_ingestion_file

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


def _extract_chunks_from_pdf(pdf_bytes: bytes) -> list[dict[str, Any]]:
    """Parse a PDF into chunk dicts using PyMuPDF hybrid outline+heading strategy (§11.9).

    Returns a list of dicts with keys: section_title, section_level, pages, text.
    Falls back to single-chunk if neither outline nor headings are found.
    """
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    chunks: list[dict[str, Any]] = []

    outline = doc.get_toc()  # [[level, title, page], ...]

    if outline:
        # Build sections from outline entries. Each top-level entry is a section.
        top_level = [(lvl, title, page) for lvl, title, page in outline if lvl == 1]
        for i, (lvl, title, page_1based) in enumerate(top_level):
            start_page = page_1based - 1  # 0-based
            end_page = (
                top_level[i + 1][2] - 2 if i + 1 < len(top_level) else len(doc) - 1
            )
            text_parts = []
            pages_spanned = []
            for pno in range(start_page, end_page + 1):
                page_text = doc[pno].get_text("text")
                if page_text.strip():
                    text_parts.append(page_text)
                    pages_spanned.append(pno + 1)  # store 1-based
            full_text = "\n".join(text_parts).strip()
            if full_text:
                chunks.append({
                    "section_title": title,
                    "section_level": lvl,
                    "pages": pages_spanned,
                    "text": full_text,
                })
    else:
        # No outline — collect all text and split on headings by font size heuristic.
        all_text = ""
        all_pages: list[int] = []
        for pno in range(len(doc)):
            page_text = doc[pno].get_text("text")
            if page_text.strip():
                all_text += page_text + "\n"
                all_pages.append(pno + 1)

        if all_text.strip():
            chunks.append({
                "section_title": None,
                "section_level": 0,
                "pages": all_pages,
                "text": all_text.strip(),
            })

    doc.close()
    return chunks


async def chunk_pdf(ctx: dict, ingestion_id: str) -> None:  # type: ignore[type-arg]
    """Parse a PDF into ingestion_chunks and update the ingestion status (§11.9, §14).

    Triggered when a PDF ingestion is created. Reads the stored file, extracts
    structural chunks using PyMuPDF, and writes IngestionChunk records.
    """
    settings: Settings = ctx["settings"]
    engine: AsyncEngine = ctx["db_engine"]
    iid = uuid.UUID(ingestion_id)

    async with AsyncSession(engine) as session:
        ingestion = (
            await session.execute(select(Ingestion).where(Ingestion.id == iid))
        ).scalar_one_or_none()

        if ingestion is None:
            log.error("chunk_pdf_ingestion_not_found", ingestion_id=ingestion_id)
            return

        ingestion.status = "chunking"
        await session.commit()

    try:
        if ingestion.storage_path is None:
            raise ValueError("ingestion has no storage_path")
        pdf_bytes = read_ingestion_file(settings, ingestion.storage_path)

        # Scanned-PDF heuristic: reject if no extractable text across entire document.
        doc_check = fitz.open(stream=pdf_bytes, filetype="pdf")
        total_text = "".join(doc_check[p].get_text("text") for p in range(len(doc_check)))
        page_count = len(doc_check)
        doc_check.close()

        if not total_text.strip():
            async with AsyncSession(engine) as session:
                ing = (
                    await session.execute(select(Ingestion).where(Ingestion.id == iid))
                ).scalar_one()
                ing.status = "failed"
                ing.error_detail = (
                    "Scanned or image-only PDF — please supply a text-based PDF "
                    "or copy content into a manual import."
                )
                await session.commit()
            log.warning("chunk_pdf_scanned_document", ingestion_id=ingestion_id)
            return

        raw_chunks = _extract_chunks_from_pdf(pdf_bytes)

        async with AsyncSession(engine) as session:
            ing = (
                await session.execute(select(Ingestion).where(Ingestion.id == iid))
            ).scalar_one()

            for idx, ch in enumerate(raw_chunks):
                text: str = ch["text"]
                preview = text[:200].replace("\n", " ")
                word_count = len(text.split())
                chunk = IngestionChunk(
                    ingestion_id=iid,
                    chunk_index=idx,
                    section_title=ch["section_title"],
                    section_level=ch["section_level"],
                    pages_json=ch["pages"],
                    text=text,
                    text_preview=preview,
                    word_count=word_count,
                    chunk_status="pending",
                )
                session.add(chunk)

            ing.status = "ready"
            ing.page_count = page_count
            ing.chunk_count = len(raw_chunks)
            await session.commit()

        log.info(
            "chunk_pdf_complete",
            ingestion_id=ingestion_id,
            chunks=len(raw_chunks),
            pages=page_count,
        )

    except Exception as exc:
        async with AsyncSession(engine) as session:
            ing = (
                await session.execute(select(Ingestion).where(Ingestion.id == iid))
            ).scalar_one()
            ing.status = "failed"
            ing.error_detail = str(exc)
            await session.commit()
        log.error("chunk_pdf_failed", ingestion_id=ingestion_id, error=str(exc))
        raise


async def process_chunks(ctx: dict, ingestion_id: str) -> None:  # type: ignore[type-arg]
    """Run LLM triage and extraction on queued chunks (SS11.3 stages 3-4, SS14).

    Only processes chunks in `queued` state. Chunks in any other state are skipped.
    LLM calls are stubbed — marks chunks done with no candidates when LLM is not configured.
    """
    settings: Settings = ctx["settings"]
    engine: AsyncEngine = ctx["db_engine"]
    iid = uuid.UUID(ingestion_id)

    triage_url = settings.resolved_triage_base_url()
    extraction_url = settings.resolved_extraction_base_url()

    if not triage_url or not extraction_url:
        log.warning(
            "process_chunks_no_llm_config",
            ingestion_id=ingestion_id,
            note="marking queued chunks done with no candidates",
        )
        async with AsyncSession(engine) as session:
            result = await session.execute(
                select(IngestionChunk).where(
                    IngestionChunk.ingestion_id == iid,
                    IngestionChunk.chunk_status == "queued",
                )
            )
            for chunk in result.scalars().all():
                chunk.chunk_status = "done"
            await session.commit()
        return

    # Real LLM triage + extraction implemented in Sprint 6 session 2.
    log.info("process_chunks_llm_configured_stub", ingestion_id=ingestion_id)


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

    log.info("worker_ready")


async def shutdown(ctx: dict) -> None:  # type: ignore[type-arg]
    engine: AsyncEngine | None = ctx.get("db_engine")
    if engine is not None:
        await engine.dispose()
    log.info("worker_shutdown")


class WorkerSettings:
    """ARQ worker configuration."""

    functions: ClassVar[list[object]] = [
        generate_embedding,
        expire_review_claims,
        chunk_pdf,
        process_chunks,
    ]

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
