"""ARQ worker entrypoint.

Start with: arq workers.main.WorkerSettings

The startup hook is LOAD-BEARING — do not remove. See §14 of the spec.
Without it, ingestion chunks left in `processing` state after a worker crash
are silently skipped on resume, producing missing candidates with no error.
"""

import json
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

from api import prompts as prompt_store
from api.config import Settings, get_settings
from api.database import create_engine
from api.logging import configure_logging
from api.models.concept import Concept
from api.models.fact import Fact
from api.models.ingestion import Ingestion, IngestionCandidate, IngestionChunk
from api.models.principle import Principle
from api.models.task import Task
from api.models.workflow import Workflow
from api.prompts import Prompt
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


_TRIAGE_CATEGORIES = frozenset(
    {"task_candidate", "principle_candidate", "reference_material", "skip"}
)


async def _call_llm(
    base_url: str,
    model: str,
    api_key: str,
    system: str,
    user: str,
    timeout: int,
) -> str:
    """POST a chat-completions request and return the assistant message content.

    Raises httpx.HTTPStatusError on non-2xx responses.
    """
    headers: dict[str, str] = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    async with httpx.AsyncClient() as http:
        response = await http.post(
            f"{base_url}/chat/completions",
            json={
                "model": model,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
            },
            headers=headers,
            timeout=timeout,
        )
        response.raise_for_status()
    return str(response.json()["choices"][0]["message"]["content"])


def _validate_task(candidate: dict[str, Any]) -> str | None:
    """Return an error string if the task candidate is missing required fields."""
    required = {"title", "outcome", "procedure_name", "steps"}
    missing = required - candidate.keys()
    if missing:
        return f"Missing required fields: {sorted(missing)}"
    if not candidate.get("steps"):
        return "steps array must not be empty"
    return None


def _validate_principle(candidate: dict[str, Any]) -> str | None:
    """Return an error string if the principle candidate is missing required fields."""
    required = {"title", "summary", "explanation"}
    missing = required - candidate.keys()
    if missing:
        return f"Missing required fields: {sorted(missing)}"
    return None


async def _process_single_chunk(
    engine: AsyncEngine,
    settings: Settings,
    chunk: IngestionChunk,
    triage_prompt: Prompt,
    task_prompt: Prompt,
    principle_prompt: Prompt,
) -> None:
    """Triage one chunk, extract candidates, persist results.

    Chunk status progression: queued → processing → done | error.
    Any exception marks the chunk error and records the detail.
    """
    chunk_id = chunk.id
    ingestion_id = chunk.ingestion_id

    # Mark processing before any LLM call so the startup hook can recover on crash.
    async with AsyncSession(engine) as session:
        ch = await session.get(IngestionChunk, chunk_id)
        if ch is None or ch.chunk_status != "queued":
            return
        ch.chunk_status = "processing"
        await session.commit()

    try:
        # ------------------------------------------------------------------ #
        # Stage 3: triage
        # ------------------------------------------------------------------ #
        triage_system, triage_user = triage_prompt.render(
            section_title=chunk.section_title or "",
            text=chunk.text[:6000],
        )
        raw_triage = await _call_llm(
            base_url=settings.resolved_triage_base_url(),
            model=settings.resolved_triage_model(),
            api_key=settings.resolved_triage_api_key(),
            system=triage_system,
            user=triage_user,
            timeout=settings.llm_triage_timeout_seconds,
        )
        triage_result: dict[str, Any] = json.loads(raw_triage)
        category = triage_result.get("category", "")
        if category not in _TRIAGE_CATEGORIES:
            raise ValueError(f"Triage returned unknown category: {category!r}")

        log.info(
            "chunk_triaged",
            chunk_id=str(chunk_id),
            category=category,
            confidence=triage_result.get("confidence"),
        )

        # ------------------------------------------------------------------ #
        # Stage 4: extraction
        # ------------------------------------------------------------------ #
        candidates: list[IngestionCandidate] = []

        if category in ("reference_material", "skip"):
            pass  # no extraction; chunk marked done with zero candidates

        elif category == "task_candidate":
            extraction_system, extraction_user = task_prompt.render(
                section_title=chunk.section_title or "",
                text=chunk.text,
            )
            raw_extraction = await _call_llm(
                base_url=settings.resolved_extraction_base_url(),
                model=settings.resolved_extraction_model(),
                api_key=settings.resolved_extraction_api_key(),
                system=extraction_system,
                user=extraction_user,
                timeout=settings.llm_extraction_timeout_seconds,
            )
            extraction_result: dict[str, Any] = json.loads(raw_extraction)
            for task_json in extraction_result.get("tasks", []):
                err = _validate_task(task_json)
                status = "invalid" if err else "pending"
                candidates.append(
                    IngestionCandidate(
                        ingestion_id=ingestion_id,
                        chunk_id=chunk_id,
                        record_type="task",
                        proposed_json=task_json,
                        candidate_status=status,
                        review_note=err,
                    )
                )

        elif category == "principle_candidate":
            extraction_system, extraction_user = principle_prompt.render(
                section_title=chunk.section_title or "",
                text=chunk.text,
            )
            raw_extraction = await _call_llm(
                base_url=settings.resolved_extraction_base_url(),
                model=settings.resolved_extraction_model(),
                api_key=settings.resolved_extraction_api_key(),
                system=extraction_system,
                user=extraction_user,
                timeout=settings.llm_extraction_timeout_seconds,
            )
            extraction_result = json.loads(raw_extraction)
            for principle_json in extraction_result.get("principles", []):
                err = _validate_principle(principle_json)
                status = "invalid" if err else "pending"
                candidates.append(
                    IngestionCandidate(
                        ingestion_id=ingestion_id,
                        chunk_id=chunk_id,
                        record_type="principle",
                        proposed_json=principle_json,
                        candidate_status=status,
                        review_note=err,
                    )
                )

        # ------------------------------------------------------------------ #
        # Persist candidates and mark done
        # ------------------------------------------------------------------ #
        valid_count = sum(1 for c in candidates if c.candidate_status == "pending")
        async with AsyncSession(engine) as session:
            for candidate in candidates:
                session.add(candidate)
            ch = await session.get(IngestionChunk, chunk_id)
            if ch is not None:
                ch.chunk_status = "done"
                ch.candidate_count = valid_count
            await session.commit()

        log.info(
            "chunk_processed",
            chunk_id=str(chunk_id),
            category=category,
            candidates_total=len(candidates),
            candidates_valid=valid_count,
        )

    except Exception as exc:
        async with AsyncSession(engine) as session:
            ch = await session.get(IngestionChunk, chunk_id)
            if ch is not None:
                ch.chunk_status = "error"
                ch.error_detail = str(exc)
            await session.commit()
        log.error(
            "chunk_processing_failed",
            chunk_id=str(chunk_id),
            error=str(exc),
        )


async def process_chunks(ctx: dict, ingestion_id: str) -> None:  # type: ignore[type-arg]
    """Run LLM triage and extraction on queued chunks (SS11.3 stages 3-4, SS14).

    Only processes chunks in `queued` state. Chunks in any other state are skipped.
    When LLM is not configured, queued chunks are marked done with no candidates.
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

    triage_prompt = prompt_store.load("triage")
    task_prompt = prompt_store.load("extract_task")
    principle_prompt = prompt_store.load("extract_principle")

    async with AsyncSession(engine) as session:
        result = await session.execute(
            select(IngestionChunk).where(
                IngestionChunk.ingestion_id == iid,
                IngestionChunk.chunk_status == "queued",
            )
        )
        queued_chunks = result.scalars().all()

    log.info(
        "process_chunks_started",
        ingestion_id=ingestion_id,
        chunk_count=len(queued_chunks),
    )

    for chunk in queued_chunks:
        await _process_single_chunk(
            engine, settings, chunk, triage_prompt, task_prompt, principle_prompt
        )


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
