"""Ingestion pipeline API endpoints (§11).

PDF upload, chunk list, section selection. HTML and JSON ingestion in Sprint 6 session 2.
"""

import hashlib
import uuid
from typing import Annotated

import structlog
from fastapi import APIRouter, HTTPException, Query, UploadFile, status
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from api.auth import Role
from api.dependencies import AppSettings, ArqPool, CurrentUser, DBSession, require_role
from api.models.ingestion import Ingestion, IngestionChunk
from api.models.user import User
from api.schemas.ingestion import (
    IngestionResponse,
    IngestionStatusResponse,
    SelectChunksRequest,
    SelectChunksResponse,
)
from api.services.storage import save_ingestion_file

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
async def create_ingestion(
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
