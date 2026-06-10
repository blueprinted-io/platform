"""Ingestion pipeline API endpoints (§11).

PDF upload, HTML URL, JSON payload, chunk list, section selection,
candidate review, and commit.
"""

import hashlib
import json
import uuid
from datetime import UTC, datetime
from typing import Annotated, Any
from urllib.parse import urlparse, urlunparse

import structlog
from fastapi import APIRouter, HTTPException, Query, Request, UploadFile, status
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from api.auth import Role
from api.dependencies import AppSettings, ArqPool, CurrentUser, DBSession, require_role
from api.limiter import limiter
from api.models.ingestion import (
    Ingestion,
    IngestionCandidate,
    IngestionChunk,
    IngestionNavPage,
)
from api.models.principle import Principle
from api.models.task import Task, TaskStep, TaskStepAction
from api.models.user import User
from api.schemas.ingestion import (
    CandidateCommitRequest,
    CandidateCommitResponse,
    CandidateReviewRequest,
    HtmlIngestionRequest,
    IngestionCandidateResponse,
    IngestionResponse,
    IngestionStatusResponse,
    JsonIngestionRequest,
    JsonPrincipleItem,
    JsonTaskItem,
    NavPageResponse,
    NavSelectRequest,
    NavSelectResponse,
    SelectChunksRequest,
    SelectChunksResponse,
)
from api.services import lifecycle
from api.services.storage import delete_ingestion_dir, save_ingestion_file

log = structlog.get_logger(__name__)

router = APIRouter(prefix="/ingestions", tags=["ingestions"])

_Writer = Annotated[User, require_role(Role.CONTRIBUTOR, Role.ADMIN)]

_ALLOWED_MIME = {"application/pdf"}
_MAX_FILENAME_LEN = 255


def _sanitise_filename(name: str) -> str:
    """Strip path components and replace unsafe characters."""
    import re
    name = name.rsplit("/", 1)[-1].rsplit("\\", 1)[-1]
    name = re.sub(r"[^\w\-.]", "_", name)
    return name[:_MAX_FILENAME_LEN] or "upload.pdf"


@router.post("", response_model=IngestionResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("10/minute")
async def create_ingestion(
    request: Request,
    file: UploadFile,
    session: DBSession,
    user: _Writer,
    settings: AppSettings,
    arq_pool: ArqPool,
) -> IngestionResponse:
    """Upload a PDF and start the chunking job (§11.9)."""
    if file.content_type not in _ALLOWED_MIME:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Unsupported file type: {file.content_type}. Only PDF is accepted.",
        )

    pdf_bytes = await file.read()

    if not pdf_bytes:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Uploaded file is empty.",
        )

    sha256 = hashlib.sha256(pdf_bytes).hexdigest()

    # Dedup: redirect to existing ingestion with the same file content (§11.9).
    existing = (
        await session.execute(
            select(Ingestion).where(Ingestion.source_sha256 == sha256)
        )
    ).scalar_one_or_none()
    if existing is not None:
        log.info(
            "ingestion_duplicate_detected",
            existing_id=str(existing.id),
            sha256=sha256,
        )
        return IngestionResponse.model_validate(existing)

    ingestion_id = uuid.uuid4()
    safe_filename = _sanitise_filename(file.filename or "upload.pdf")
    storage_path, _ = save_ingestion_file(settings, ingestion_id, safe_filename, pdf_bytes)

    ingestion = Ingestion(
        id=ingestion_id,
        source_type="pdf",
        status="pending",
        created_by=user.id,
        original_filename=safe_filename,
        storage_path=storage_path,
        source_sha256=sha256,
    )
    session.add(ingestion)
    await session.commit()
    await session.refresh(ingestion)

    if arq_pool is not None:
        await arq_pool.enqueue_job("chunk_pdf", ingestion_id=str(ingestion.id))
    else:
        log.warning("ingestion_arq_unavailable", ingestion_id=str(ingestion.id))

    log.info(
        "ingestion_created",
        ingestion_id=str(ingestion.id),
        filename=safe_filename,
        bytes=len(pdf_bytes),
    )
    return IngestionResponse.model_validate(ingestion)


@router.get("", response_model=list[IngestionResponse])
async def list_ingestions(
    session: DBSession,
    user: CurrentUser,
    limit: int = Query(default=20, le=100),
    offset: int = Query(default=0, ge=0),
) -> list[IngestionResponse]:
    """List ingestions created by the current user, newest first."""
    result = await session.execute(
        select(Ingestion)
        .where(Ingestion.created_by == user.id)
        .order_by(Ingestion.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    return [IngestionResponse.model_validate(i) for i in result.scalars().all()]


@router.delete("/{ingestion_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_ingestion(
    ingestion_id: uuid.UUID,
    session: DBSession,
    user: CurrentUser,
    app_settings: AppSettings,
) -> None:
    ingestion = await session.get(Ingestion, ingestion_id)
    if ingestion is None or ingestion.created_by != user.id:
        raise HTTPException(status_code=404, detail="Ingestion not found.")
    storage_path = ingestion.storage_path
    await session.delete(ingestion)
    await session.commit()
    if storage_path is not None:
        delete_ingestion_dir(app_settings, ingestion_id)


@router.get("/{ingestion_id}/status", response_model=IngestionStatusResponse)
async def get_ingestion_status(
    ingestion_id: uuid.UUID,
    session: DBSession,
    user: CurrentUser,
) -> IngestionStatusResponse:
    """Return ingestion with its full chunk list (§11.5 section selection screen)."""
    result = await session.execute(
        select(Ingestion)
        .where(Ingestion.id == ingestion_id)
        .options(selectinload(Ingestion.chunks))
    )
    ingestion = result.scalar_one_or_none()
    if ingestion is None:
        raise HTTPException(status_code=404, detail="Ingestion not found.")
    if ingestion.created_by != user.id:
        raise HTTPException(status_code=404, detail="Ingestion not found.")
    return IngestionStatusResponse.model_validate(ingestion)


@router.post("/{ingestion_id}/select", response_model=SelectChunksResponse)
async def select_chunks(
    ingestion_id: uuid.UUID,
    body: SelectChunksRequest,
    session: DBSession,
    user: _Writer,
    arq_pool: ArqPool,
) -> SelectChunksResponse:
    """Queue selected chunks for LLM triage and extraction (§11.5).

    Callable multiple times on the same ingestion. Only pending chunks are queued;
    chunks already in queued/processing/done/error/skipped are not affected.
    """
    ingestion = (
        await session.execute(select(Ingestion).where(Ingestion.id == ingestion_id))
    ).scalar_one_or_none()
    if ingestion is None or ingestion.created_by != user.id:
        raise HTTPException(status_code=404, detail="Ingestion not found.")

    if not body.chunk_ids:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="chunk_ids must not be empty.",
        )

    if ingestion.status not in ("ready", "chunking"):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Cannot select chunks on an ingestion with status '{ingestion.status}'.",
        )

    # Only queue chunks that belong to this ingestion and are currently pending.
    result = await session.execute(
        select(IngestionChunk).where(
            IngestionChunk.ingestion_id == ingestion_id,
            IngestionChunk.id.in_(body.chunk_ids),
            IngestionChunk.chunk_status == "pending",
        )
    )
    chunks_to_queue = result.scalars().all()

    for chunk in chunks_to_queue:
        chunk.chunk_status = "queued"

    await session.commit()

    queued_count = len(chunks_to_queue)

    if queued_count > 0 and arq_pool is not None:
        await arq_pool.enqueue_job("process_chunks", ingestion_id=str(ingestion_id))
    elif queued_count > 0:
        log.warning("ingestion_select_arq_unavailable", ingestion_id=str(ingestion_id))

    log.info(
        "ingestion_chunks_queued",
        ingestion_id=str(ingestion_id),
        queued=queued_count,
        requested=len(body.chunk_ids),
    )
    return SelectChunksResponse(queued_count=queued_count, ingestion_id=ingestion_id)


@router.get("/{ingestion_id}/candidates", response_model=list[IngestionCandidateResponse])
async def list_candidates(
    ingestion_id: uuid.UUID,
    session: DBSession,
    user: _Writer,
) -> list[IngestionCandidateResponse]:
    """List all candidates for an ingestion (§11.8)."""
    ingestion = (
        await session.execute(select(Ingestion).where(Ingestion.id == ingestion_id))
    ).scalar_one_or_none()
    if ingestion is None or ingestion.created_by != user.id:
        raise HTTPException(status_code=404, detail="Ingestion not found.")

    result = await session.execute(
        select(IngestionCandidate).where(IngestionCandidate.ingestion_id == ingestion_id)
    )
    return [IngestionCandidateResponse.model_validate(c) for c in result.scalars().all()]


@router.patch(
    "/{ingestion_id}/candidates/{candidate_id}",
    response_model=IngestionCandidateResponse,
)
async def review_candidate(
    ingestion_id: uuid.UUID,
    candidate_id: uuid.UUID,
    body: CandidateReviewRequest,
    session: DBSession,
    user: _Writer,
) -> IngestionCandidateResponse:
    """Accept or discard a candidate, optionally with an edited proposed_json (§11.8)."""
    ingestion = (
        await session.execute(select(Ingestion).where(Ingestion.id == ingestion_id))
    ).scalar_one_or_none()
    if ingestion is None or ingestion.created_by != user.id:
        raise HTTPException(status_code=404, detail="Ingestion not found.")

    candidate = (
        await session.execute(
            select(IngestionCandidate).where(
                IngestionCandidate.id == candidate_id,
                IngestionCandidate.ingestion_id == ingestion_id,
            )
        )
    ).scalar_one_or_none()
    if candidate is None:
        raise HTTPException(status_code=404, detail="Candidate not found.")

    if candidate.candidate_status == "discarded":
        raise HTTPException(
            status_code=422,
            detail="Candidate has already been discarded.",
        )
    if candidate.committed_record_id is not None:
        raise HTTPException(
            status_code=422,
            detail="Candidate has already been committed.",
        )

    if body.action == "accept":
        if body.proposed_json is not None:
            candidate.proposed_json = body.proposed_json
            candidate.candidate_status = "edited"
        else:
            candidate.candidate_status = "accepted"
    else:
        candidate.candidate_status = "discarded"

    if body.review_note is not None:
        candidate.review_note = body.review_note

    candidate.reviewed_by = user.id
    candidate.reviewed_at = datetime.now(tz=UTC)

    await session.commit()
    await session.refresh(candidate)
    return IngestionCandidateResponse.model_validate(candidate)


def _build_task(
    proposed: dict[str, Any], domain: str, user_id: uuid.UUID, ingestion_id: uuid.UUID
) -> Task:
    """Construct a Task ORM object (without steps) from extraction JSON."""
    return Task(
        title=proposed["title"],
        outcome=proposed["outcome"],
        domain=domain,
        software_name=proposed.get("software_name"),
        software_version=proposed.get("software_version"),
        ingestion_id=ingestion_id,
        facts=proposed.get("facts") or None,
        concepts=proposed.get("concepts") or None,
        tags=proposed.get("tags") or [],
        created_by=user_id,
        updated_by=user_id,
    )


def _build_steps(task: Task, proposed: dict[str, Any]) -> None:
    """Attach TaskStep and TaskStepAction children to a Task."""
    for i, step_data in enumerate(proposed.get("steps", [])):
        step = TaskStep(
            task=task,
            order_index=i,
            step=step_data.get("text", ""),
            completion=step_data.get("completion", ""),
            notes=step_data.get("notes"),
            irreversible=step_data.get("irreversible", False),
        )
        for j, action_text in enumerate(step_data.get("actions", [])):
            step.actions.append(
                TaskStepAction(
                    step=step,
                    order_index=j,
                    instruction=action_text,
                )
            )
        task.steps.append(step)


@router.post(
    "/{ingestion_id}/candidates/{candidate_id}/commit",
    response_model=CandidateCommitResponse,
    status_code=status.HTTP_201_CREATED,
)
async def commit_candidate(
    ingestion_id: uuid.UUID,
    candidate_id: uuid.UUID,
    body: CandidateCommitRequest,
    session: DBSession,
    user: _Writer,
) -> CandidateCommitResponse:
    """Commit an accepted candidate into the governance pipeline (§11.8).

    Creates a governed Task or Principle record at draft or submitted status.
    The pipeline may not create confirmed records — that requires a human confirm action.
    """
    ingestion = (
        await session.execute(select(Ingestion).where(Ingestion.id == ingestion_id))
    ).scalar_one_or_none()
    if ingestion is None or ingestion.created_by != user.id:
        raise HTTPException(status_code=404, detail="Ingestion not found.")

    candidate = (
        await session.execute(
            select(IngestionCandidate).where(
                IngestionCandidate.id == candidate_id,
                IngestionCandidate.ingestion_id == ingestion_id,
            )
        )
    ).scalar_one_or_none()
    if candidate is None:
        raise HTTPException(status_code=404, detail="Candidate not found.")

    if candidate.candidate_status not in ("accepted", "edited"):
        raise HTTPException(
            status_code=422,
            detail=(
                f"Candidate must be accepted or edited before committing "
                f"(current status: '{candidate.candidate_status}')."
            ),
        )
    if candidate.committed_record_id is not None:
        raise HTTPException(
            status_code=422,
            detail="Candidate has already been committed.",
        )

    await lifecycle.assert_domain_active(body.domain, session)
    await lifecycle.assert_domain_access(body.domain, user, session)

    proposed = candidate.proposed_json

    if candidate.record_type == "task":
        record: Task | Principle = _build_task(proposed, body.domain, user.id, ingestion_id)
        _build_steps(record, proposed)  # type: ignore[arg-type]
        session.add(record)
        await session.flush()  # populate record.id before reading it below

        if body.target_status == "submitted":
            lifecycle.assert_can_submit(record.status, user)
            record.status = "submitted"
            record.updated_by = user.id

    elif candidate.record_type == "principle":
        record = Principle(
            title=proposed["title"],
            summary=proposed["summary"],
            explanation=proposed["explanation"],
            analogies=proposed.get("analogies"),
            domain=body.domain,
            ingestion_id=ingestion_id,
            created_by=user.id,
            updated_by=user.id,
        )
        session.add(record)
        await session.flush()

        if body.target_status == "submitted":
            lifecycle.assert_can_submit(record.status, user)
            record.status = "submitted"
            record.updated_by = user.id

    else:
        raise HTTPException(
            status_code=422,
            detail=f"Cannot commit candidate with record_type '{candidate.record_type}'.",
        )

    committed_id = record.id
    candidate.committed_record_id = committed_id
    candidate.candidate_status = "accepted"
    candidate.reviewed_by = user.id
    candidate.reviewed_at = datetime.now(tz=UTC)

    await session.commit()

    log.info(
        "ingestion_candidate_committed",
        candidate_id=str(candidate_id),
        record_type=candidate.record_type,
        committed_record_id=str(committed_id),
        target_status=body.target_status,
    )
    return CandidateCommitResponse(
        candidate_id=candidate_id,
        committed_record_id=committed_id,
        record_type=candidate.record_type,
        target_status=body.target_status,
    )


# ---------------------------------------------------------------------------
# HTML ingestion (§11.10, §11.11)
# ---------------------------------------------------------------------------


def _normalise_url(url: str) -> str:
    """Lowercase scheme+host, strip fragment, sort query params for stable dedup."""
    parsed = urlparse(url)
    normalised = parsed._replace(
        scheme=parsed.scheme.lower(),
        netloc=parsed.netloc.lower(),
        fragment="",
    )
    return urlunparse(normalised)


@router.post("/html", response_model=IngestionResponse, status_code=status.HTTP_201_CREATED)
async def create_html_ingestion(
    body: HtmlIngestionRequest,
    session: DBSession,
    user: _Writer,
    arq_pool: ArqPool,
) -> IngestionResponse:
    """Submit a URL for HTML ingestion (§11.10).

    Single-page mode renders one URL and chunks it immediately.
    Site-nav mode discovers navigable pages; the operator selects which to include.
    """
    normalised = _normalise_url(body.url)
    sha256 = hashlib.sha256(normalised.encode()).hexdigest()

    if not body.force:
        existing = (
            await session.execute(
                select(Ingestion).where(Ingestion.source_sha256 == sha256)
            )
        ).scalar_one_or_none()
        if existing is not None:
            log.info(
                "html_ingestion_duplicate_detected",
                existing_id=str(existing.id),
                url=normalised,
            )
            return IngestionResponse.model_validate(existing)

    ingestion = Ingestion(
        source_type="html",
        status="pending",
        created_by=user.id,
        source_url=body.url,
        source_sha256=sha256,
    )
    session.add(ingestion)
    await session.commit()
    await session.refresh(ingestion)

    if arq_pool is not None:
        await arq_pool.enqueue_job(
            "crawl_html",
            ingestion_id=str(ingestion.id),
            mode=body.mode,
        )
    else:
        log.warning("html_ingestion_arq_unavailable", ingestion_id=str(ingestion.id))

    log.info(
        "html_ingestion_created",
        ingestion_id=str(ingestion.id),
        url=body.url,
        mode=body.mode,
    )
    return IngestionResponse.model_validate(ingestion)


@router.get("/{ingestion_id}/nav-pages", response_model=list[NavPageResponse])
async def list_nav_pages(
    ingestion_id: uuid.UUID,
    session: DBSession,
    user: _Writer,
) -> list[NavPageResponse]:
    """List discovered nav pages for an HTML site-nav ingestion (§11.11)."""
    ingestion = (
        await session.execute(select(Ingestion).where(Ingestion.id == ingestion_id))
    ).scalar_one_or_none()
    if ingestion is None or ingestion.created_by != user.id:
        raise HTTPException(status_code=404, detail="Ingestion not found.")
    if ingestion.source_type != "html":
        raise HTTPException(
            status_code=422,
            detail="Nav pages are only available for HTML ingestions.",
        )

    result = await session.execute(
        select(IngestionNavPage)
        .where(IngestionNavPage.ingestion_id == ingestion_id)
        .order_by(IngestionNavPage.nav_level, IngestionNavPage.id)
    )
    return [NavPageResponse.model_validate(p) for p in result.scalars().all()]


@router.post("/{ingestion_id}/nav-select", response_model=NavSelectResponse)
async def select_nav_pages(
    ingestion_id: uuid.UUID,
    body: NavSelectRequest,
    session: DBSession,
    user: _Writer,
    arq_pool: ArqPool,
) -> NavSelectResponse:
    """Select nav pages to render and chunk (§11.11).

    Selected pages are queued for Playwright rendering. After rendering they
    appear as ingestion_chunks available for section selection (§11.5).
    """
    ingestion = (
        await session.execute(select(Ingestion).where(Ingestion.id == ingestion_id))
    ).scalar_one_or_none()
    if ingestion is None or ingestion.created_by != user.id:
        raise HTTPException(status_code=404, detail="Ingestion not found.")
    if ingestion.source_type != "html":
        raise HTTPException(
            status_code=422,
            detail="Nav selection is only valid for HTML ingestions.",
        )
    if ingestion.status != "ready":
        raise HTTPException(
            status_code=422,
            detail=f"Cannot select nav pages on an ingestion with status '{ingestion.status}'.",
        )
    if not body.nav_page_ids:
        raise HTTPException(
            status_code=422,
            detail="nav_page_ids must not be empty.",
        )

    result = await session.execute(
        select(IngestionNavPage).where(
            IngestionNavPage.ingestion_id == ingestion_id,
            IngestionNavPage.id.in_(body.nav_page_ids),
            IngestionNavPage.nav_status == "pending",
        )
    )
    pages_to_queue = result.scalars().all()

    for page in pages_to_queue:
        page.nav_status = "selected"

    await session.commit()

    queued_count = len(pages_to_queue)

    if queued_count > 0 and arq_pool is not None:
        await arq_pool.enqueue_job(
            "render_nav_pages",
            ingestion_id=str(ingestion_id),
        )
    elif queued_count > 0:
        log.warning("nav_select_arq_unavailable", ingestion_id=str(ingestion_id))

    log.info(
        "nav_pages_queued",
        ingestion_id=str(ingestion_id),
        queued=queued_count,
        requested=len(body.nav_page_ids),
    )
    return NavSelectResponse(queued_count=queued_count, ingestion_id=ingestion_id)


# ---------------------------------------------------------------------------
# JSON ingestion (§11.12)
# ---------------------------------------------------------------------------


def _canonical_json(payload: dict[str, Any]) -> bytes:
    """Canonical JSON: sorted keys, no whitespace — for stable SHA-256 dedup."""
    return json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()


@router.post("/json", response_model=IngestionResponse, status_code=status.HTTP_201_CREATED)
async def create_json_ingestion(
    body: JsonIngestionRequest,
    session: DBSession,
    user: _Writer,
) -> IngestionResponse:
    """Submit a pre-structured JSON payload for ingestion (§11.12).

    JSON ingestion bypasses chunking and LLM extraction. Items are converted
    directly to ingestion_candidates and the ingestion is immediately ready for
    candidate review.
    """
    raw_payload = body.model_dump()
    sha256 = hashlib.sha256(_canonical_json(raw_payload)).hexdigest()

    existing = (
        await session.execute(
            select(Ingestion).where(Ingestion.source_sha256 == sha256)
        )
    ).scalar_one_or_none()
    if existing is not None:
        log.info(
            "json_ingestion_duplicate_detected",
            existing_id=str(existing.id),
            sha256=sha256,
        )
        return IngestionResponse.model_validate(existing)

    ingestion = Ingestion(
        source_type="json",
        status="ready",
        created_by=user.id,
        source_sha256=sha256,
        chunk_count=0,
    )
    session.add(ingestion)
    await session.flush()  # populate ingestion.id before creating candidates

    for item in body.items:
        if isinstance(item, JsonTaskItem):
            proposed: dict[str, Any] = {
                "type": "task",
                "title": item.title,
                "outcome": item.outcome,
                "software_name": item.software_name,
                "software_version": item.software_version,
                "domain": item.domain,
                "facts": item.facts,
                "concepts": item.concepts,
                "dependencies": item.dependencies,
                "irreversible": item.irreversible,
                "task_order": item.task_order,
                "steps": [
                    {
                        "id": s.id,
                        "text": s.text,
                        "completion": s.completion,
                        "actions": s.actions,
                        "notes": s.notes,
                    }
                    for s in item.steps
                ],
            }
            record_type = "task"
        else:
            assert isinstance(item, JsonPrincipleItem)
            proposed = {
                "type": "principle",
                "title": item.title,
                "summary": item.summary,
                "explanation": item.explanation,
                "analogies": item.analogies,
                "software_name": item.software_name,
                "software_version": item.software_version,
                "domain": item.domain,
            }
            record_type = "principle"

        candidate = IngestionCandidate(
            ingestion_id=ingestion.id,
            chunk_id=None,
            record_type=record_type,
            proposed_json=proposed,
            candidate_status="pending",
        )
        session.add(candidate)

    await session.commit()
    await session.refresh(ingestion)

    log.info(
        "json_ingestion_created",
        ingestion_id=str(ingestion.id),
        item_count=len(body.items),
    )
    return IngestionResponse.model_validate(ingestion)
