"""Concepts API endpoints."""

import uuid
from typing import Annotated

import structlog
from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.auth import Role
from api.dependencies import ArqPool, CurrentUser, DBSession, require_role
from api.models.concept import Concept
from api.models.user import User
from api.schemas.base import ConfirmRequest
from api.schemas.concept import ConceptCreate, ConceptResponse, ConceptUpdate, ReturnRequest
from api.services import lifecycle

log = structlog.get_logger(__name__)

router = APIRouter(prefix="/concepts", tags=["concepts"])

_Writer = Annotated[User, require_role(Role.CONTRIBUTOR, Role.ADMIN)]
_Admin = Annotated[User, require_role(Role.ADMIN)]


async def _get_or_404(session: AsyncSession, concept_id: uuid.UUID) -> Concept:
    result = await session.execute(select(Concept).where(Concept.id == concept_id))
    concept = result.scalar_one_or_none()
    if concept is None:
        raise HTTPException(status_code=404, detail="Concept not found.")
    return concept


@router.post("", response_model=ConceptResponse, status_code=status.HTTP_201_CREATED)
async def create_concept(body: ConceptCreate, session: DBSession, user: _Writer) -> Concept:
    concept = Concept(
        title=body.title,
        summary=body.summary,
        explanation=body.explanation,
        analogies=body.analogies,
        tags=body.tags,
        created_by=user.id,
        updated_by=user.id,
    )
    session.add(concept)
    await session.commit()
    await session.refresh(concept)
    return concept


@router.get("", response_model=list[ConceptResponse])
async def list_concepts(session: DBSession, user: CurrentUser) -> list[Concept]:
    result = await session.execute(select(Concept).order_by(Concept.created_at.desc()))
    return list(result.scalars().all())


@router.get("/{concept_id}", response_model=ConceptResponse)
async def get_concept(concept_id: uuid.UUID, session: DBSession, user: CurrentUser) -> Concept:
    return await _get_or_404(session, concept_id)


@router.patch("/{concept_id}", response_model=ConceptResponse)
async def update_concept(
    concept_id: uuid.UUID, body: ConceptUpdate, session: DBSession, user: _Writer
) -> Concept:
    concept = await _get_or_404(session, concept_id)
    lifecycle.assert_can_edit(concept.status)
    if body.title is not None:
        concept.title = body.title
    if body.summary is not None:
        concept.summary = body.summary
    if body.explanation is not None:
        concept.explanation = body.explanation
    if body.analogies is not None:
        concept.analogies = body.analogies
    if body.tags is not None:
        concept.tags = body.tags
    concept.updated_by = user.id
    await session.commit()
    await session.refresh(concept)
    return concept


@router.post("/{concept_id}/submit", response_model=ConceptResponse)
async def submit_concept(concept_id: uuid.UUID, session: DBSession, user: _Writer) -> Concept:
    concept = await _get_or_404(session, concept_id)
    lifecycle.assert_can_submit(concept.status, user)
    concept.status = "submitted"
    concept.updated_by = user.id
    await session.commit()
    await session.refresh(concept)
    return concept


@router.post("/{concept_id}/confirm", response_model=ConceptResponse)
async def confirm_concept(
    concept_id: uuid.UUID,
    session: DBSession,
    user: _Writer,
    arq_pool: ArqPool,
    body: ConfirmRequest | None = None,
) -> Concept:
    concept = await _get_or_404(session, concept_id)
    is_break_glass = lifecycle.assert_can_confirm(
        concept.status, concept.created_by, user, body.justification if body else None
    )
    concept.status = "confirmed"
    concept.self_confirmed_by_admin = is_break_glass
    concept.reviewed_by = user.id
    concept.updated_by = user.id
    await session.commit()
    await session.refresh(concept)
    if arq_pool is not None:
        await arq_pool.enqueue_job(
            "generate_embedding", record_type="concept", record_id=str(concept.id)
        )
    return concept


@router.post("/{concept_id}/return", response_model=ConceptResponse)
async def return_concept(
    concept_id: uuid.UUID, body: ReturnRequest, session: DBSession, user: _Writer
) -> Concept:
    concept = await _get_or_404(session, concept_id)
    lifecycle.assert_can_return(concept.status, user)
    concept.status = "returned"
    if body.note:
        concept.change_note = body.note
    concept.reviewed_by = user.id
    concept.updated_by = user.id
    await session.commit()
    await session.refresh(concept)
    return concept


@router.post("/{concept_id}/deprecate", response_model=ConceptResponse)
async def deprecate_concept(concept_id: uuid.UUID, session: DBSession, user: _Admin) -> Concept:
    concept = await _get_or_404(session, concept_id)
    lifecycle.assert_can_deprecate(concept.status, user)
    concept.status = "deprecated"
    concept.updated_by = user.id
    await session.commit()
    await session.refresh(concept)
    return concept


@router.post("/{concept_id}/retire", response_model=ConceptResponse)
async def retire_concept(concept_id: uuid.UUID, session: DBSession, user: _Admin) -> Concept:
    concept = await _get_or_404(session, concept_id)
    lifecycle.assert_can_retire(concept.status, user)
    concept.status = "retired"
    concept.updated_by = user.id
    await session.commit()
    await session.refresh(concept)
    return concept
