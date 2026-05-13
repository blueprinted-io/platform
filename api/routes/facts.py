"""Facts API endpoints.

§9.5  — Facts schema
§9.3  — Lifecycle state machine
§10.1 — Immutability once confirmed
§10.2 — No machine can confirm
§5.1  — Human roles and self-review prohibition
"""

import uuid
from typing import Annotated

import structlog
from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.auth import Role
from api.dependencies import CurrentUser, DBSession, require_role
from api.models.fact import Fact
from api.models.user import User
from api.schemas.fact import FactCreate, FactResponse, FactUpdate, ReturnRequest
from api.services import lifecycle

log = structlog.get_logger(__name__)

router = APIRouter(prefix="/facts", tags=["facts"])

_Writer = Annotated[User, require_role(Role.CONTRIBUTOR, Role.ADMIN)]
_Admin = Annotated[User, require_role(Role.ADMIN)]


async def _get_or_404(session: AsyncSession, fact_id: uuid.UUID) -> Fact:
    result = await session.execute(select(Fact).where(Fact.id == fact_id))
    fact = result.scalar_one_or_none()
    if fact is None:
        raise HTTPException(status_code=404, detail="Fact not found.")
    return fact


@router.post("", response_model=FactResponse, status_code=status.HTTP_201_CREATED)
async def create_fact(body: FactCreate, session: DBSession, user: _Writer) -> Fact:
    fact = Fact(
        title=body.title,
        body=body.body,
        tags=body.tags,
        created_by=user.id,
        updated_by=user.id,
    )
    session.add(fact)
    await session.commit()
    await session.refresh(fact)
    log.info("fact_created", fact_id=str(fact.id), user_id=str(user.id))
    return fact


@router.get("", response_model=list[FactResponse])
async def list_facts(session: DBSession, user: CurrentUser) -> list[Fact]:
    result = await session.execute(select(Fact).order_by(Fact.created_at.desc()))
    return list(result.scalars().all())


@router.get("/{fact_id}", response_model=FactResponse)
async def get_fact(fact_id: uuid.UUID, session: DBSession, user: CurrentUser) -> Fact:
    return await _get_or_404(session, fact_id)


@router.patch("/{fact_id}", response_model=FactResponse)
async def update_fact(
    fact_id: uuid.UUID, body: FactUpdate, session: DBSession, user: _Writer
) -> Fact:
    fact = await _get_or_404(session, fact_id)
    lifecycle.assert_can_edit(fact.status)
    if body.title is not None:
        fact.title = body.title
    if body.body is not None:
        fact.body = body.body
    if body.tags is not None:
        fact.tags = body.tags
    fact.updated_by = user.id
    await session.commit()
    await session.refresh(fact)
    return fact


@router.post("/{fact_id}/submit", response_model=FactResponse)
async def submit_fact(fact_id: uuid.UUID, session: DBSession, user: _Writer) -> Fact:
    fact = await _get_or_404(session, fact_id)
    lifecycle.assert_can_submit(fact.status, user)
    fact.status = "submitted"
    fact.updated_by = user.id
    await session.commit()
    await session.refresh(fact)
    log.info("fact_submitted", fact_id=str(fact.id), user_id=str(user.id))
    return fact


@router.post("/{fact_id}/confirm", response_model=FactResponse)
async def confirm_fact(fact_id: uuid.UUID, session: DBSession, user: _Writer) -> Fact:
    fact = await _get_or_404(session, fact_id)
    lifecycle.assert_can_confirm(fact.status, fact.created_by, user)
    fact.status = "confirmed"
    fact.reviewed_by = user.id
    fact.updated_by = user.id
    await session.commit()
    await session.refresh(fact)
    log.info("fact_confirmed", fact_id=str(fact.id), user_id=str(user.id))
    return fact


@router.post("/{fact_id}/return", response_model=FactResponse)
async def return_fact(
    fact_id: uuid.UUID, body: ReturnRequest, session: DBSession, user: _Writer
) -> Fact:
    fact = await _get_or_404(session, fact_id)
    lifecycle.assert_can_return(fact.status, user)
    fact.status = "returned"
    if body.note:
        fact.change_note = body.note
    fact.reviewed_by = user.id
    fact.updated_by = user.id
    await session.commit()
    await session.refresh(fact)
    log.info("fact_returned", fact_id=str(fact.id), user_id=str(user.id))
    return fact


@router.post("/{fact_id}/deprecate", response_model=FactResponse)
async def deprecate_fact(fact_id: uuid.UUID, session: DBSession, user: _Admin) -> Fact:
    fact = await _get_or_404(session, fact_id)
    lifecycle.assert_can_deprecate(fact.status, user)
    fact.status = "deprecated"
    fact.updated_by = user.id
    await session.commit()
    await session.refresh(fact)
    log.info("fact_deprecated", fact_id=str(fact.id), user_id=str(user.id))
    return fact


@router.post("/{fact_id}/retire", response_model=FactResponse)
async def retire_fact(fact_id: uuid.UUID, session: DBSession, user: _Admin) -> Fact:
    fact = await _get_or_404(session, fact_id)
    lifecycle.assert_can_retire(fact.status, user)
    fact.status = "retired"
    fact.updated_by = user.id
    await session.commit()
    await session.refresh(fact)
    log.info("fact_retired", fact_id=str(fact.id), user_id=str(user.id))
    return fact
