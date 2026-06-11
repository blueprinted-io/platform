"""LLM triage and extraction jobs (§11.3, §14). Run on the ingestion worker.

Chunks come from either the PDF or HTML pipeline; triage and extraction are
source-agnostic.
"""

import uuid
from typing import Any

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

from api import prompts as prompt_store
from api.config import Settings
from api.models.ingestion import (
    IngestionCandidate,
    IngestionChunk,
    IngestionTriageEstimate,
)
from api.prompts import Prompt
from api.services.settings_service import LLMSettings, load_llm_settings
from workers.common import exc_str
from workers.llm import call_llm, parse_llm_json

log = structlog.get_logger(__name__)

_TRIAGE_CATEGORIES = frozenset(
    {"task_candidate", "principle_candidate", "reference_material", "skip"}
)


def _validate_task(candidate: dict[str, Any]) -> str | None:
    """Return an error string if the task candidate is missing required fields."""
    required = {"title", "outcome", "steps"}
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


async def _triage_chunk(
    engine: AsyncEngine,
    llm: LLMSettings,
    chunk: IngestionChunk,
    triage_prompt: Prompt,
) -> None:
    """Run triage on one chunk, write estimates, set status to triage_complete (§11.3 stage 3).

    Chunk status progression: queued → processing → triage_complete | done | error.
    reference_material/skip chunks skip directly to done with no estimates.
    """
    chunk_id = chunk.id
    ingestion_id = chunk.ingestion_id

    async with AsyncSession(engine) as session:
        ch = await session.get(IngestionChunk, chunk_id)
        if ch is None or ch.chunk_status != "queued":
            return
        ch.chunk_status = "processing"
        await session.commit()

    try:
        triage_system, triage_user = triage_prompt.render(
            section_title=chunk.section_title or "",
            text=chunk.text[:6000],
        )
        raw_triage = await call_llm(
            base_url=llm.triage_base_url,
            model=llm.triage_model,
            api_key=llm.triage_api_key,
            system=triage_system,
            user=triage_user,
            timeout=llm.triage_timeout,
        )
        triage_result: dict[str, Any] = parse_llm_json(
            raw_triage, chunk.section_title or "triage"
        )
        category = triage_result.get("category", "")
        if category not in _TRIAGE_CATEGORIES:
            raise ValueError(f"Triage returned unknown category: {category!r}")

        log.info(
            "chunk_triaged",
            chunk_id=str(chunk_id),
            category=category,
            confidence=triage_result.get("confidence"),
        )

        async with AsyncSession(engine) as session:
            ch = await session.get(IngestionChunk, chunk_id)
            if ch is None:
                return

            if category in ("reference_material", "skip"):
                ch.chunk_status = "done"
            else:
                raw_estimates: list[dict[str, Any]] = triage_result.get("estimates") or []
                for i, est in enumerate(raw_estimates):
                    record_type = est.get("type", "task")
                    if record_type not in ("task", "principle"):
                        record_type = "task"
                    session.add(
                        IngestionTriageEstimate(
                            ingestion_id=ingestion_id,
                            chunk_id=chunk_id,
                            record_type=record_type,
                            approved_type=record_type,
                            estimated_title=est.get("title") or chunk.section_title or "Untitled",
                            estimate_status="pending",
                            sort_order=i,
                        )
                    )

                if raw_estimates:
                    ch.chunk_status = "triage_complete"
                else:
                    # LLM returned a candidate category but no estimates — skip extraction.
                    log.warning(
                        "chunk_triage_no_estimates",
                        chunk_id=str(chunk_id),
                        category=category,
                    )
                    ch.chunk_status = "done"

            await session.commit()

        log.info("chunk_triage_complete", chunk_id=str(chunk_id), category=category)

    except Exception as exc:
        async with AsyncSession(engine) as session:
            ch = await session.get(IngestionChunk, chunk_id)
            if ch is not None:
                ch.chunk_status = "error"
                ch.error_detail = exc_str(exc)
            await session.commit()
        log.error("chunk_triage_failed", chunk_id=str(chunk_id), error=exc_str(exc))


async def _extract_from_estimate(
    engine: AsyncEngine,
    llm: LLMSettings,
    estimate_id: uuid.UUID,
    chunk: IngestionChunk,
    task_prompt: Prompt,
    principle_prompt: Prompt,
) -> IngestionCandidate | None:
    """Run extraction for one approved estimate, returning the candidate (or None on error)."""
    async with AsyncSession(engine) as session:
        estimate = await session.get(IngestionTriageEstimate, estimate_id)
        if estimate is None or estimate.estimate_status != "approved":
            return None

        # Idempotency guard: skip if a candidate was already created for this
        # chunk+type in a previous (crashed) run of this job.
        existing = (
            await session.execute(
                select(IngestionCandidate).where(
                    IngestionCandidate.chunk_id == chunk.id,
                    IngestionCandidate.record_type == estimate.approved_type,
                )
            )
        ).scalars().first()
        if existing is not None:
            log.info(
                "extract_candidate_already_exists",
                estimate_id=str(estimate_id),
                chunk_id=str(chunk.id),
            )
            return None

        record_type = estimate.approved_type
        section_label = estimate.estimated_title or chunk.section_title or ""

        if record_type == "task":
            ext_system, ext_user = task_prompt.render(
                section_title=section_label,
                text=chunk.text,
            )
        else:
            ext_system, ext_user = principle_prompt.render(
                section_title=section_label,
                text=chunk.text,
            )

    raw = await call_llm(
        base_url=llm.extraction_base_url,
        model=llm.extraction_model,
        api_key=llm.extraction_api_key,
        system=ext_system,
        user=ext_user,
        timeout=llm.extraction_timeout,
    )
    extraction_result = parse_llm_json(raw, section_label)

    if record_type == "task":
        items = extraction_result.get("tasks", [])
        validate = _validate_task
    else:
        items = extraction_result.get("principles", [])
        validate = _validate_principle

    if not items:
        log.warning("extract_no_items", estimate_id=str(estimate_id), record_type=record_type)
        return None

    if len(items) > 1:
        log.warning(
            "extract_items_discarded",
            estimate_id=str(estimate_id),
            record_type=record_type,
            total=len(items),
            kept=1,
        )

    candidate_json = items[0]
    err = validate(candidate_json)
    return IngestionCandidate(
        ingestion_id=chunk.ingestion_id,
        chunk_id=chunk.id,
        record_type=record_type,
        proposed_json=candidate_json,
        candidate_status="invalid" if err else "pending",
        review_note=err,
    )


async def extract_chunk(ctx: dict, chunk_id: str) -> None:  # type: ignore[type-arg]
    """Run targeted extraction on approved estimates for one chunk (§11.3 stage 5).

    Reads all approved estimates, calls the extraction LLM once per estimate,
    creates one IngestionCandidate per estimate, then marks the chunk done.
    Chunk status: extraction_queued → extracting → done | error.
    The startup hook resets extracting → extraction_queued on crash.
    """
    engine: AsyncEngine = ctx["db_engine"]
    env_settings: Settings = ctx["settings"]
    cid = uuid.UUID(chunk_id)

    async with AsyncSession(engine) as session:
        llm = await load_llm_settings(
            session, env_settings.app_secret_key.get_secret_value(), env_settings
        )
        chunk = await session.get(IngestionChunk, cid)
        if chunk is None or chunk.chunk_status != "extraction_queued":
            return
        chunk.chunk_status = "extracting"
        await session.commit()

    async with AsyncSession(engine) as session:
        chunk = await session.get(IngestionChunk, cid)
        if chunk is None:
            return

        result = await session.execute(
            select(IngestionTriageEstimate).where(
                IngestionTriageEstimate.chunk_id == cid,
                IngestionTriageEstimate.estimate_status == "approved",
            )
        )
        estimates = result.scalars().all()

    if not estimates:
        async with AsyncSession(engine) as session:
            ch = await session.get(IngestionChunk, cid)
            if ch is not None:
                ch.chunk_status = "done"
            await session.commit()
        return

    task_prompt = prompt_store.load("extract_task")
    principle_prompt = prompt_store.load("extract_principle")

    candidates: list[IngestionCandidate] = []
    errors: list[str] = []

    for estimate in estimates:
        try:
            candidate = await _extract_from_estimate(
                engine, llm, estimate.id, chunk, task_prompt, principle_prompt
            )
            if candidate is not None:
                candidates.append(candidate)
        except Exception as exc:
            errors.append(f"estimate {estimate.id}: {exc}")
            log.error("extract_estimate_failed", estimate_id=str(estimate.id), error=exc_str(exc))

    if errors and not candidates:
        async with AsyncSession(engine) as session:
            ch = await session.get(IngestionChunk, cid)
            if ch is not None:
                ch.chunk_status = "error"
                ch.error_detail = "; ".join(errors)
            await session.commit()
        return

    valid_count = sum(1 for c in candidates if c.candidate_status == "pending")
    async with AsyncSession(engine) as session:
        for candidate in candidates:
            session.add(candidate)
        ch = await session.get(IngestionChunk, cid)
        if ch is not None:
            ch.chunk_status = "done"
            ch.candidate_count = valid_count
        await session.commit()

    log.info(
        "chunk_extracted",
        chunk_id=chunk_id,
        candidates_total=len(candidates),
        candidates_valid=valid_count,
        errors=len(errors),
    )


async def process_chunks(ctx: dict, ingestion_id: str) -> None:  # type: ignore[type-arg]
    """Run LLM triage on queued chunks (§11.3 stage 3, §14).

    Each chunk moves to triage_complete (with estimates) or done (skip/reference_material).
    Extraction runs separately via extract_chunk after the operator approves estimates.
    When LLM is not configured, queued chunks are marked done with no candidates.
    """
    env_settings: Settings = ctx["settings"]
    engine: AsyncEngine = ctx["db_engine"]
    iid = uuid.UUID(ingestion_id)

    async with AsyncSession(engine) as session:
        llm = await load_llm_settings(
            session, env_settings.app_secret_key.get_secret_value(), env_settings
        )

    if not llm.triage_base_url:
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
        await _triage_chunk(engine, llm, chunk, triage_prompt)
