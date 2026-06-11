"""Triage estimate review endpoints (§11.5a).

GET    /ingestions/{id}/chunks/{chunk_id}/estimates
PATCH  /ingestions/{id}/chunks/{chunk_id}/estimates/{estimate_id}
POST   /ingestions/{id}/chunks/{chunk_id}/estimates/merge
POST   /ingestions/{id}/chunks/{chunk_id}/estimates/approve
"""

import uuid

import structlog
from fastapi import APIRouter, HTTPException
from sqlalchemy import select

from api.dependencies import ArqPool, CurrentUser, DBSession
from api.models.ingestion import Ingestion, IngestionChunk, IngestionTriageEstimate
from api.schemas.triage_estimate import (
    TriageEstimateApproveResponse,
    TriageEstimateMergeRequest,
    TriageEstimateMergeResponse,
    TriageEstimatePatchRequest,
    TriageEstimateResponse,
)
from workers.queues import INGESTION_QUEUE

log = structlog.get_logger(__name__)

router = APIRouter(
    prefix="/ingestions/{ingestion_id}/chunks/{chunk_id}/estimates",
    tags=["triage-estimates"],
)

_VALID_APPROVED_TYPES = {"task", "principle"}


async def _get_chunk_or_404(
    ingestion_id: uuid.UUID,
    chunk_id: uuid.UUID,
    user_id: uuid.UUID,
    session: DBSession,
) -> IngestionChunk:
    ingestion = (
        await session.execute(select(Ingestion).where(Ingestion.id == ingestion_id))
    ).scalar_one_or_none()
    if ingestion is None or ingestion.created_by != user_id:
        raise HTTPException(status_code=404, detail="Ingestion not found.")

    chunk = (
        await session.execute(
            select(IngestionChunk).where(
                IngestionChunk.id == chunk_id,
                IngestionChunk.ingestion_id == ingestion_id,
            )
        )
    ).scalar_one_or_none()
    if chunk is None:
        raise HTTPException(status_code=404, detail="Chunk not found.")
    return chunk


@router.get("", response_model=list[TriageEstimateResponse])
async def list_estimates(
    ingestion_id: uuid.UUID,
    chunk_id: uuid.UUID,
    session: DBSession,
    user: CurrentUser,
) -> list[TriageEstimateResponse]:
    """List triage estimates for a chunk (§11.5a)."""
    await _get_chunk_or_404(ingestion_id, chunk_id, user.id, session)

    result = await session.execute(
        select(IngestionTriageEstimate)
        .where(
            IngestionTriageEstimate.chunk_id == chunk_id,
            IngestionTriageEstimate.ingestion_id == ingestion_id,
        )
        .order_by(IngestionTriageEstimate.sort_order)
    )
    return [TriageEstimateResponse.model_validate(e) for e in result.scalars().all()]


@router.patch("/{estimate_id}", response_model=TriageEstimateResponse)
async def patch_estimate(
    ingestion_id: uuid.UUID,
    chunk_id: uuid.UUID,
    estimate_id: uuid.UUID,
    body: TriageEstimatePatchRequest,
    session: DBSession,
    user: CurrentUser,
) -> TriageEstimateResponse:
    """Update an estimate's type or title, or mark it rejected (§11.5a)."""
    await _get_chunk_or_404(ingestion_id, chunk_id, user.id, session)

    estimate = (
        await session.execute(
            select(IngestionTriageEstimate).where(
                IngestionTriageEstimate.id == estimate_id,
                IngestionTriageEstimate.chunk_id == chunk_id,
            )
        )
    ).scalar_one_or_none()
    if estimate is None:
        raise HTTPException(status_code=404, detail="Estimate not found.")

    if estimate.estimate_status != "pending":
        raise HTTPException(
            status_code=422,
            detail=f"Cannot edit an estimate with status '{estimate.estimate_status}'.",
        )

    if body.approved_type is not None:
        if body.approved_type not in _VALID_APPROVED_TYPES:
            raise HTTPException(
                status_code=422,
                detail=f"approved_type must be one of {sorted(_VALID_APPROVED_TYPES)}.",
            )
        estimate.approved_type = body.approved_type

    if body.estimated_title is not None:
        estimate.estimated_title = body.estimated_title

    if body.estimate_status is not None:
        if body.estimate_status != "rejected":
            raise HTTPException(
                status_code=422,
                detail="estimate_status can only be set to 'rejected' via PATCH.",
            )
        estimate.estimate_status = "rejected"

    await session.commit()
    await session.refresh(estimate)
    return TriageEstimateResponse.model_validate(estimate)


@router.post("/merge", response_model=TriageEstimateMergeResponse)
async def merge_estimates(
    ingestion_id: uuid.UUID,
    chunk_id: uuid.UUID,
    body: TriageEstimateMergeRequest,
    session: DBSession,
    user: CurrentUser,
) -> TriageEstimateMergeResponse:
    """Merge multiple estimates into one (§11.5a).

    The first estimate in the list survives with the merged_title; the rest are
    marked merged and point to the survivor via merged_into_id.
    """
    await _get_chunk_or_404(ingestion_id, chunk_id, user.id, session)

    if len(body.estimate_ids) < 2:
        raise HTTPException(
            status_code=422,
            detail="At least two estimate_ids are required for a merge.",
        )

    result = await session.execute(
        select(IngestionTriageEstimate).where(
            IngestionTriageEstimate.id.in_(body.estimate_ids),
            IngestionTriageEstimate.chunk_id == chunk_id,
        )
    )
    estimates = result.scalars().all()

    if len(estimates) != len(body.estimate_ids):
        raise HTTPException(
            status_code=404,
            detail="One or more estimate IDs not found on this chunk.",
        )

    for est in estimates:
        if est.estimate_status != "pending":
            raise HTTPException(
                status_code=422,
                detail=(
                    f"Estimate {est.id} has status"
                    f" '{est.estimate_status}' and cannot be merged."
                ),
            )

    # First ID in the request survives; the rest point to it.
    survivor_id = body.estimate_ids[0]
    survivor = next(e for e in estimates if e.id == survivor_id)
    survivor.estimated_title = body.merged_title

    for est in estimates:
        if est.id != survivor_id:
            est.estimate_status = "merged"
            est.merged_into_id = survivor_id

    await session.commit()
    log.info(
        "triage_estimates_merged",
        survivor_id=str(survivor_id),
        merged_count=len(estimates) - 1,
    )
    return TriageEstimateMergeResponse(surviving_id=survivor_id)


@router.post("/approve", response_model=TriageEstimateApproveResponse)
async def approve_estimates(
    ingestion_id: uuid.UUID,
    chunk_id: uuid.UUID,
    session: DBSession,
    user: CurrentUser,
    arq_pool: ArqPool,
) -> TriageEstimateApproveResponse:
    """Approve pending estimates, moving the chunk to extraction_queued (§11.5a).

    All pending estimates are marked approved. Rejected and merged estimates are
    left as-is. If no estimates remain pending (all rejected/merged), the chunk
    moves directly to done with zero candidates and no extraction job is enqueued.
    """
    chunk = await _get_chunk_or_404(ingestion_id, chunk_id, user.id, session)

    if chunk.chunk_status != "triage_complete":
        raise HTTPException(
            status_code=422,
            detail=(
                f"Chunk must be in 'triage_complete' state to approve estimates"
                f" (current: '{chunk.chunk_status}')."
            ),
        )

    result = await session.execute(
        select(IngestionTriageEstimate).where(
            IngestionTriageEstimate.chunk_id == chunk_id,
        )
    )
    all_estimates = result.scalars().all()

    # Identify estimates whose effective outcome is extraction — pending estimates
    # whose merge chain has not been rejected. A pending estimate that is the
    # survivor of a merge and has since been rejected is already status='rejected',
    # so it won't appear in pending. The edge case we guard against: a 'merged'
    # estimate points to a survivor that was subsequently rejected. These merged
    # estimates contribute nothing to extraction but their survivor is already
    # gone from pending, so approved_count is naturally correct.
    pending = [e for e in all_estimates if e.estimate_status == "pending"]

    for est in pending:
        est.estimate_status = "approved"

    approved_count = len(pending)

    if approved_count > 0:
        chunk.chunk_status = "extraction_queued"
        await session.commit()
        if arq_pool is not None:
            await arq_pool.enqueue_job(
                "extract_chunk", chunk_id=str(chunk_id), _queue_name=INGESTION_QUEUE
            )
        else:
            log.warning("triage_approve_arq_unavailable", chunk_id=str(chunk_id))
    else:
        # All estimates were rejected or merged into a rejected estimate — skip extraction.
        chunk.chunk_status = "done"
        await session.commit()

    log.info(
        "triage_estimates_approved",
        chunk_id=str(chunk_id),
        approved=approved_count,
    )
    return TriageEstimateApproveResponse(extraction_queued=approved_count)
