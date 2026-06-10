"""Principles API endpoints."""

import uuid
from typing import Annotated

import structlog
from fastapi import APIRouter, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from api.auth import Role
from api.dependencies import ArqPool, CurrentUser, DBSession, require_role
from api.models.principle import Principle
from api.models.user import User
from api.schemas.base import ConfirmRequest
from api.schemas.principle import (
    PrincipleCreate,
    PrincipleResponse,
    PrincipleUpdate,
    PrincipleVersionSummary,
    ReturnRequest,
    ReviseRequest,
)
from api.services import lifecycle, lifecycle_actions
from api.services.notifications import create_notification, notify_domain_users

log = structlog.get_logger(__name__)

router = APIRouter(prefix="/principles", tags=["principles"])

_Writer = Annotated[User, require_role(Role.CONTRIBUTOR, Role.ADMIN)]
_Admin = Annotated[User, require_role(Role.ADMIN)]


async def _get_or_404(session: AsyncSession, principle_id: uuid.UUID) -> Principle:
    result = await session.execute(select(Principle).where(Principle.id == principle_id))
    principle = result.scalar_one_or_none()
    if principle is None:
        raise HTTPException(status_code=404, detail="Principle not found.")
    return principle


@router.post("", response_model=PrincipleResponse, status_code=status.HTTP_201_CREATED)
async def create_principle(body: PrincipleCreate, session: DBSession, user: _Writer) -> Principle:
    await lifecycle.assert_domain_active(body.domain, session)
    await lifecycle.assert_domain_access(body.domain, user, session)
    principle = Principle(
        title=body.title,
        summary=body.summary,
        explanation=body.explanation,
        analogies=body.analogies,
        domain=body.domain,
        tags=body.tags,
        created_by=user.id,
        updated_by=user.id,
    )
    session.add(principle)
    await session.commit()
    await session.refresh(principle)
    return principle


@router.get("", response_model=list[PrincipleResponse])
async def list_principles(session: DBSession, user: CurrentUser) -> list[Principle]:
    latest = (
        select(Principle.record_id, func.max(Principle.version).label("max_version"))
        .group_by(Principle.record_id)
        .subquery()
    )
    result = await session.execute(
        select(Principle)
        .join(
            latest,
            (Principle.record_id == latest.c.record_id)
            & (Principle.version == latest.c.max_version),
        )
        .order_by(Principle.created_at.desc())
    )
    return list(result.scalars().all())


@router.get("/{record_id}/versions", response_model=list[PrincipleVersionSummary])
async def list_principle_versions(
    record_id: uuid.UUID, session: DBSession, user: CurrentUser
) -> list[PrincipleVersionSummary]:
    result = await session.execute(
        select(Principle).where(Principle.record_id == record_id).order_by(Principle.version.desc())
    )
    principles = result.scalars().all()
    if not principles:
        raise HTTPException(status_code=404, detail="Principle not found.")
    return [PrincipleVersionSummary.model_validate(p) for p in principles]


@router.get("/{principle_id}", response_model=PrincipleResponse)
async def get_principle(
    principle_id: uuid.UUID, session: DBSession, user: CurrentUser
) -> Principle:
    return await _get_or_404(session, principle_id)


@router.patch("/{principle_id}", response_model=PrincipleResponse)
async def update_principle(
    principle_id: uuid.UUID, body: PrincipleUpdate, session: DBSession, user: _Writer
) -> Principle:
    principle = await _get_or_404(session, principle_id)
    lifecycle.assert_can_edit(principle.status)
    if body.title is not None:
        principle.title = body.title
    if body.summary is not None:
        principle.summary = body.summary
    if body.explanation is not None:
        principle.explanation = body.explanation
    if body.analogies is not None:
        principle.analogies = body.analogies
    if body.domain is not None:
        await lifecycle.assert_domain_active(body.domain, session)
        await lifecycle.assert_domain_access(body.domain, user, session)
        principle.domain = body.domain
    if body.tags is not None:
        principle.tags = body.tags
    principle.updated_by = user.id
    await session.commit()
    await session.refresh(principle)
    return principle


@router.post("/{principle_id}/submit", response_model=PrincipleResponse)
async def submit_principle(
    principle_id: uuid.UUID, session: DBSession, user: _Writer
) -> Principle:
    principle = await _get_or_404(session, principle_id)
    lifecycle.assert_can_submit(principle.status, user)
    await lifecycle.assert_domain_access(principle.domain, user, session)
    principle.status = "submitted"
    principle.updated_by = user.id
    await session.commit()
    await notify_domain_users(
        session, principle.domain, "record_submitted", "principle", principle.id,
        f'Principle "{principle.title}" has been submitted for review.',
        exclude_user_id=user.id,
    )
    await session.commit()
    await session.refresh(principle)
    return principle


@router.post("/{principle_id}/confirm", response_model=PrincipleResponse)
async def confirm_principle(
    principle_id: uuid.UUID,
    session: DBSession,
    user: _Writer,
    arq_pool: ArqPool,
    body: ConfirmRequest | None = None,
) -> Principle:
    principle = await _get_or_404(session, principle_id)
    await lifecycle.assert_domain_access(principle.domain, user, session)
    await lifecycle.assert_no_foreign_claim("principle", principle.id, user, session)
    await lifecycle_actions.confirm_record(
        principle, session, user, body.justification if body else None, "principle"
    )
    await create_notification(
        session, principle.created_by, "record_confirmed", "principle", principle.id,
        f'Your principle "{principle.title}" has been confirmed.',
    )
    await session.commit()
    await session.refresh(principle)
    if arq_pool is not None:
        await arq_pool.enqueue_job(
            "generate_embedding", record_type="principle", record_id=str(principle.id)
        )
    return principle


@router.post("/{principle_id}/return", response_model=PrincipleResponse)
async def return_principle(
    principle_id: uuid.UUID, body: ReturnRequest, session: DBSession, user: _Writer
) -> Principle:
    principle = await _get_or_404(session, principle_id)
    await lifecycle.assert_domain_access(principle.domain, user, session)
    await lifecycle.assert_no_foreign_claim("principle", principle.id, user, session)
    await lifecycle_actions.return_record(principle, session, user, body.note, body.severity, "principle")
    await create_notification(
        session, principle.created_by, "record_returned", "principle", principle.id,
        f'Your principle "{principle.title}" has been returned for changes.',
    )
    await session.commit()
    await session.refresh(principle)
    return principle


@router.post("/{principle_id}/deprecate", response_model=PrincipleResponse)
async def deprecate_principle(
    principle_id: uuid.UUID, session: DBSession, user: _Admin
) -> Principle:
    principle = await _get_or_404(session, principle_id)
    await lifecycle_actions.deprecate_record(principle, session, user, "principle")
    await session.refresh(principle)
    return principle


@router.post("/{principle_id}/retire", response_model=PrincipleResponse)
async def retire_principle(
    principle_id: uuid.UUID, session: DBSession, user: _Admin
) -> Principle:
    principle = await _get_or_404(session, principle_id)
    await lifecycle_actions.retire_record(principle, session, user, "principle")
    await session.refresh(principle)
    return principle


@router.post(
    "/{principle_id}/revise",
    response_model=PrincipleResponse,
    status_code=status.HTTP_201_CREATED,
)
async def revise_principle(
    principle_id: uuid.UUID, session: DBSession, user: _Writer,
    body: ReviseRequest | None = None,
) -> Principle:
    """Create a new draft version of a principle (§9.3).

    Returned principles inherit the return note; all other statuses require an explicit note.
    """
    old = await _get_or_404(session, principle_id)
    lifecycle.assert_can_revise(old.created_by, user)
    await lifecycle.assert_domain_access(old.domain, user, session)

    note = body.note if body else None
    if old.status != "returned" and not (note and note.strip()):
        raise HTTPException(
            status_code=422,
            detail="A revision note is required when revising a record that has not been returned.",
        )

    change_note = old.change_note if old.status == "returned" else note

    new_version = old.version + 1
    existing = await session.scalar(
        select(Principle).where(
            Principle.record_id == old.record_id, Principle.version == new_version
        )
    )
    if existing is not None:
        raise HTTPException(
            status_code=409, detail="A revised draft for this record already exists."
        )

    new_principle = Principle(
        record_id=old.record_id,
        version=new_version,
        status="draft",
        title=old.title,
        summary=old.summary,
        explanation=old.explanation,
        analogies=old.analogies,
        domain=old.domain,
        tags=list(old.tags),
        change_note=change_note,
        created_by=user.id,
        updated_by=user.id,
    )
    session.add(new_principle)
    await session.flush()
    new_principle_id = new_principle.id

    await session.commit()
    log.info(
        "principle_revised",
        old_principle_id=str(principle_id),
        new_principle_id=str(new_principle_id),
        new_version=new_version,
        user_id=str(user.id),
    )
    result = await session.execute(select(Principle).where(Principle.id == new_principle_id))
    return result.scalar_one()
