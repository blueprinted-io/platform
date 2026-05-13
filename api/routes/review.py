"""Review Queue and Claiming API.

§8.1  Global Review Queue — filtered view of submitted records
§8.2  Claiming Model — claim, release, expiry
§14   Review claim expiry (ARQ cron job, every 15 minutes)

Claimable entity types: tasks, workflows, principles
Queue-visible but not claimable: facts, concepts
"""

import dataclasses
import uuid
from datetime import UTC, datetime, timedelta
from typing import Annotated, cast

import sqlalchemy as sa
import structlog
from fastapi import APIRouter, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from api.auth import Role
from api.dependencies import DBSession, require_role
from api.models.concept import Concept
from api.models.fact import Fact
from api.models.principle import Principle
from api.models.review_claim import ReviewClaim
from api.models.task import Task
from api.models.user import User
from api.models.workflow import Workflow
from api.schemas.base import ConfirmRequest
from api.schemas.review import (
    ClaimInfo,
    ClaimResponse,
    ReviewActionResponse,
    ReviewQueueItem,
    ReviewQueueResponse,
    ReviewReturnRequest,
)
from api.services import lifecycle

log = structlog.get_logger(__name__)

router = APIRouter(prefix="/review", tags=["review"])

_Reviewer = Annotated[User, require_role(Role.CONTRIBUTOR, Role.ADMIN)]

# Claim expiry default in hours. Pulls from system_settings once that API exists (Sprint 10).
REVIEW_CLAIM_EXPIRY_HOURS_DEFAULT: int = 48

_CLAIMABLE_TYPES = {"tasks", "workflows", "principles"}
_ALL_REVIEW_TYPES = {"tasks", "workflows", "principles", "facts", "concepts"}

# Mapping from URL path segment to the singular entity_type stored in review_claims
_TYPE_TO_SINGULAR: dict[str, str] = {
    "tasks": "task",
    "workflows": "workflow",
    "principles": "principle",
    "facts": "fact",
    "concepts": "concept",
}

# Domain-scoped types: domain access must be checked on these
_DOMAIN_SCOPED_TYPES = {"tasks", "workflows", "principles"}

# Union of all governed record types; all share LifecycleMixin fields plus title
_AnyRecord = Task | Workflow | Principle | Fact | Concept
# Subset that carries a domain field
_DomainRecord = Task | Workflow | Principle


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


@dataclasses.dataclass
class _RawQueueItem:
    id: uuid.UUID
    record_type: str
    title: str
    domain: str | None
    status: str
    updated_at: datetime
    created_by: uuid.UUID


async def _get_active_claim(
    session: AsyncSession, entity_type: str, entity_id: uuid.UUID
) -> ReviewClaim | None:
    """Return the active (not released, not expired) claim for this entity, or None."""
    result = await session.execute(
        sa.select(ReviewClaim).where(
            ReviewClaim.entity_type == entity_type,
            ReviewClaim.entity_id == entity_id,
            ReviewClaim.released_at.is_(None),
            ReviewClaim.expires_at > sa.func.now(),
        )
    )
    return result.scalar_one_or_none()


async def _get_record(
    session: AsyncSession, entity_type: str, entity_id: uuid.UUID
) -> _AnyRecord:
    """Fetch a governed record by type and ID. Raises 422 for unknown type, 404 if not found."""
    record: _AnyRecord | None
    if entity_type == "tasks":
        record = await session.get(Task, entity_id)
    elif entity_type == "workflows":
        record = await session.get(Workflow, entity_id)
    elif entity_type == "principles":
        record = await session.get(Principle, entity_id)
    elif entity_type == "facts":
        record = await session.get(Fact, entity_id)
    elif entity_type == "concepts":
        record = await session.get(Concept, entity_id)
    else:
        raise HTTPException(
            status_code=422,
            detail=f"Unknown entity type '{entity_type}'. "
            f"Valid types: {', '.join(sorted(_ALL_REVIEW_TYPES))}.",
        )
    if record is None:
        raise HTTPException(status_code=404, detail="Record not found.")
    return record


async def _get_user_domains(session: AsyncSession, user: User) -> set[str] | None:
    """Return the set of domain names the user is assigned to.

    Returns None for admin (implicitly entitled to all domains).
    """
    if Role.ADMIN.value in user.roles:
        return None
    result = await session.execute(
        sa.text("SELECT domain FROM user_domains WHERE user_id = :uid"),
        {"uid": user.id},
    )
    return {row.domain for row in result}


async def _collect_queue_items(
    session: AsyncSession, user: User
) -> list[_RawQueueItem]:
    """Query all submitted records eligible for the user to review.

    Domain-agnostic types (fact, concept): shown to all reviewers.
    Domain-scoped types (task, workflow, principle): filtered to user's assigned domains.
    Own submissions are excluded for all users including admin.
    """
    user_domains = await _get_user_domains(session, user)
    is_admin = user_domains is None

    items: list[_RawQueueItem] = []

    # --- Domain-agnostic: Facts ---
    fact_result = await session.execute(
        sa.select(Fact).where(Fact.status == "submitted", Fact.created_by != user.id)
    )
    for fact in fact_result.scalars():
        items.append(
            _RawQueueItem(
                id=fact.id,
                record_type="fact",
                title=fact.title,
                domain=None,
                status=fact.status,
                updated_at=fact.updated_at,
                created_by=fact.created_by,
            )
        )

    # --- Domain-agnostic: Concepts ---
    concept_result = await session.execute(
        sa.select(Concept).where(
            Concept.status == "submitted", Concept.created_by != user.id
        )
    )
    for concept in concept_result.scalars():
        items.append(
            _RawQueueItem(
                id=concept.id,
                record_type="concept",
                title=concept.title,
                domain=None,
                status=concept.status,
                updated_at=concept.updated_at,
                created_by=concept.created_by,
            )
        )

    # --- Domain-scoped types ---
    # Contributor with no domain assignments sees nothing in this section.
    if is_admin or user_domains:

        # Tasks
        task_q = sa.select(Task).where(
            Task.status == "submitted", Task.created_by != user.id
        )
        if not is_admin and user_domains:
            task_q = task_q.where(Task.domain.in_(user_domains))
        task_result = await session.execute(task_q)
        for task in task_result.scalars():
            items.append(
                _RawQueueItem(
                    id=task.id,
                    record_type="task",
                    title=task.title,
                    domain=task.domain,
                    status=task.status,
                    updated_at=task.updated_at,
                    created_by=task.created_by,
                )
            )

        # Workflows
        wf_q = sa.select(Workflow).where(
            Workflow.status == "submitted", Workflow.created_by != user.id
        )
        if not is_admin and user_domains:
            wf_q = wf_q.where(Workflow.domain.in_(user_domains))
        wf_result = await session.execute(wf_q)
        for wf in wf_result.scalars():
            items.append(
                _RawQueueItem(
                    id=wf.id,
                    record_type="workflow",
                    title=wf.title,
                    domain=wf.domain,
                    status=wf.status,
                    updated_at=wf.updated_at,
                    created_by=wf.created_by,
                )
            )

        # Principles
        prn_q = sa.select(Principle).where(
            Principle.status == "submitted", Principle.created_by != user.id
        )
        if not is_admin and user_domains:
            prn_q = prn_q.where(Principle.domain.in_(user_domains))
        prn_result = await session.execute(prn_q)
        for prn in prn_result.scalars():
            items.append(
                _RawQueueItem(
                    id=prn.id,
                    record_type="principle",
                    title=prn.title,
                    domain=prn.domain,
                    status=prn.status,
                    updated_at=prn.updated_at,
                    created_by=prn.created_by,
                )
            )

    return items


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.get("/queue", response_model=ReviewQueueResponse)
async def get_review_queue(
    session: DBSession,
    user: _Reviewer,
    limit: int = 50,
    offset: int = 0,
) -> ReviewQueueResponse:
    """Return submitted records eligible for the current user to review.

    Domain-scoped records (tasks, workflows, principles) are filtered to the
    user's assigned domains. Facts and Concepts are shown to all reviewers.
    Own submissions are excluded.
    """
    raw_items = await _collect_queue_items(session, user)

    # Sort by updated_at descending (most recently submitted first)
    raw_items.sort(key=lambda i: i.updated_at, reverse=True)

    total = len(raw_items)
    page = raw_items[offset : offset + limit]

    if not page:
        return ReviewQueueResponse(items=[], total=total)

    # Bulk-fetch active claims for all items in this page
    page_ids = [i.id for i in page]
    claims_result = await session.execute(
        sa.select(ReviewClaim).where(
            ReviewClaim.entity_id.in_(page_ids),
            ReviewClaim.released_at.is_(None),
            ReviewClaim.expires_at > sa.func.now(),
        )
    )
    active_claims: dict[uuid.UUID, ReviewClaim] = {
        c.entity_id: c for c in claims_result.scalars()
    }

    queue_items = []
    for raw in page:
        claim_record = active_claims.get(raw.id)
        claim_info = (
            ClaimInfo(
                claimed_by=claim_record.claimed_by,
                expires_at=claim_record.expires_at,
            )
            if claim_record
            else None
        )
        queue_items.append(
            ReviewQueueItem(
                id=raw.id,
                record_type=raw.record_type,
                title=raw.title,
                domain=raw.domain,
                status=raw.status,
                updated_at=raw.updated_at,
                created_by=raw.created_by,
                claim=claim_info,
            )
        )

    return ReviewQueueResponse(items=queue_items, total=total)


@router.post(
    "/{entity_type}/{entity_id}/claim",
    response_model=ClaimResponse,
)
async def claim_item(
    entity_type: str,
    entity_id: uuid.UUID,
    session: DBSession,
    user: _Reviewer,
) -> ReviewClaim:
    """Claim a submitted record for review.

    Only tasks, workflows, and principles are claimable. Facts and Concepts are
    domain-agnostic and not claimable — review them directly via the confirm/return
    endpoints.

    Re-claiming an item you already hold refreshes the expiry. Claiming an item
    held by another reviewer returns 409.
    """
    if entity_type not in _CLAIMABLE_TYPES:
        raise HTTPException(
            status_code=422,
            detail=f"Entity type '{entity_type}' is not claimable. "
            f"Claimable types: {', '.join(sorted(_CLAIMABLE_TYPES))}.",
        )

    record = await _get_record(session, entity_type, entity_id)

    if record.status != "submitted":
        raise HTTPException(
            status_code=422,
            detail=f"Cannot claim a record with status '{record.status}'. "
            "Only submitted records can be claimed.",
        )

    if record.created_by == user.id and Role.ADMIN.value not in user.roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Self-review prohibited: you cannot claim your own submission.",
        )

    singular_type = _TYPE_TO_SINGULAR[entity_type]
    active_claim = await _get_active_claim(session, singular_type, entity_id)

    if active_claim is not None:
        if active_claim.claimed_by == user.id:
            # Re-claiming own active claim: refresh expiry
            active_claim.expires_at = datetime.now(UTC) + timedelta(
                hours=REVIEW_CLAIM_EXPIRY_HOURS_DEFAULT
            )
            await session.commit()
            await session.refresh(active_claim)
            log.info(
                "review_claim_refreshed",
                entity_type=singular_type,
                entity_id=str(entity_id),
                user_id=str(user.id),
            )
            return active_claim
        else:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="This item is already claimed by another reviewer.",
            )

    # Create new claim
    claim = ReviewClaim(
        entity_type=singular_type,
        entity_id=entity_id,
        claimed_by=user.id,
        expires_at=datetime.now(UTC) + timedelta(hours=REVIEW_CLAIM_EXPIRY_HOURS_DEFAULT),
    )
    session.add(claim)
    await session.commit()
    await session.refresh(claim)
    log.info(
        "review_claim_created",
        entity_type=singular_type,
        entity_id=str(entity_id),
        user_id=str(user.id),
    )
    return claim


@router.post(
    "/{entity_type}/{entity_id}/release",
    response_model=ClaimResponse,
)
async def release_claim(
    entity_type: str,
    entity_id: uuid.UUID,
    session: DBSession,
    user: _Reviewer,
) -> ReviewClaim:
    """Explicitly release a claim you hold, returning the item to the unclaimed queue."""
    if entity_type not in _ALL_REVIEW_TYPES:
        raise HTTPException(
            status_code=422,
            detail=f"Unknown entity type '{entity_type}'.",
        )

    singular_type = _TYPE_TO_SINGULAR.get(entity_type, entity_type)
    active_claim = await _get_active_claim(session, singular_type, entity_id)

    if active_claim is None:
        raise HTTPException(
            status_code=404,
            detail="No active claim found for this item.",
        )

    if active_claim.claimed_by != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not hold the active claim on this item.",
        )

    active_claim.released_at = datetime.now(UTC)
    await session.commit()
    await session.refresh(active_claim)
    log.info(
        "review_claim_released",
        entity_type=singular_type,
        entity_id=str(entity_id),
        user_id=str(user.id),
    )
    return active_claim


@router.post(
    "/{entity_type}/{entity_id}/confirm",
    response_model=ReviewActionResponse,
)
async def confirm_via_review(
    entity_type: str,
    entity_id: uuid.UUID,
    session: DBSession,
    user: _Reviewer,
    body: ConfirmRequest | None = None,
) -> ReviewActionResponse:
    """Confirm a submitted record and release any active claim held by the current user.

    Applies the same lifecycle rules as the record-level confirm endpoints.
    Domain access is checked for domain-scoped types (tasks, workflows, principles).
    """
    if entity_type not in _ALL_REVIEW_TYPES:
        raise HTTPException(status_code=422, detail=f"Unknown entity type '{entity_type}'.")

    record = await _get_record(session, entity_type, entity_id)

    if entity_type in _DOMAIN_SCOPED_TYPES:
        domain_record = cast(_DomainRecord, record)
        await lifecycle.assert_domain_access(domain_record.domain, user, session)

    is_break_glass = lifecycle.assert_can_confirm(
        record.status, record.created_by, user, body.justification if body else None
    )
    record.status = "confirmed"
    record.self_confirmed_by_admin = is_break_glass
    record.reviewed_by = user.id
    record.updated_by = user.id

    # Release own claim if held (claim is advisory; release is best-effort)
    singular_type = _TYPE_TO_SINGULAR.get(entity_type, entity_type)
    if entity_type in _CLAIMABLE_TYPES:
        active_claim = await _get_active_claim(session, singular_type, entity_id)
        if active_claim is not None and active_claim.claimed_by == user.id:
            active_claim.released_at = datetime.now(UTC)

    await session.commit()
    log.info(
        "review_confirmed",
        entity_type=singular_type,
        entity_id=str(entity_id),
        user_id=str(user.id),
    )
    # Sprint 7: enqueue generate_embedding(record_type=singular_type, record_id=str(entity_id))
    return ReviewActionResponse(
        id=record.id,
        record_type=singular_type,
        status=record.status,
    )


@router.post(
    "/{entity_type}/{entity_id}/return",
    response_model=ReviewActionResponse,
)
async def return_via_review(
    entity_type: str,
    entity_id: uuid.UUID,
    body: ReviewReturnRequest,
    session: DBSession,
    user: _Reviewer,
) -> ReviewActionResponse:
    """Return a submitted record to the author and release any active claim.

    Applies the same lifecycle rules as the record-level return endpoints.
    """
    if entity_type not in _ALL_REVIEW_TYPES:
        raise HTTPException(status_code=422, detail=f"Unknown entity type '{entity_type}'.")

    record = await _get_record(session, entity_type, entity_id)

    if entity_type in _DOMAIN_SCOPED_TYPES:
        domain_record = cast(_DomainRecord, record)
        await lifecycle.assert_domain_access(domain_record.domain, user, session)

    lifecycle.assert_can_return(record.status, user)
    record.status = "returned"
    if body.note:
        record.change_note = body.note
    record.reviewed_by = user.id
    record.updated_by = user.id

    # Release own claim if held
    singular_type = _TYPE_TO_SINGULAR.get(entity_type, entity_type)
    if entity_type in _CLAIMABLE_TYPES:
        active_claim = await _get_active_claim(session, singular_type, entity_id)
        if active_claim is not None and active_claim.claimed_by == user.id:
            active_claim.released_at = datetime.now(UTC)

    await session.commit()
    log.info(
        "review_returned",
        entity_type=singular_type,
        entity_id=str(entity_id),
        user_id=str(user.id),
    )
    return ReviewActionResponse(
        id=record.id,
        record_type=singular_type,
        status=record.status,
    )
