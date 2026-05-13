"""Workflows API endpoints, including task-refs and principle-refs.

§9.5  — Workflows schema
§9.3  — Lifecycle state machine
Workflow composition is always a human act — ingestion never produces Workflow candidates.
"""

import uuid
from datetime import UTC, datetime
from typing import Annotated

import structlog
from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from api.auth import Role
from api.dependencies import CurrentUser, DBSession, require_role
from api.models.principle import Principle
from api.models.task import Task
from api.models.user import User
from api.models.workflow import Workflow, WorkflowPrincipleRef, WorkflowTaskRef
from api.schemas.workflow import (
    ReturnRequest,
    WorkflowCreate,
    WorkflowPrincipleRefCreate,
    WorkflowPrincipleRefResponse,
    WorkflowResponse,
    WorkflowTaskRefCreate,
    WorkflowTaskRefResponse,
    WorkflowUpdate,
)
from api.services import lifecycle

log = structlog.get_logger(__name__)

router = APIRouter(prefix="/workflows", tags=["workflows"])

_Writer = Annotated[User, require_role(Role.CONTRIBUTOR, Role.ADMIN)]
_Admin = Annotated[User, require_role(Role.ADMIN)]


async def _get_workflow_with_refs(session: AsyncSession, workflow_id: uuid.UUID) -> Workflow:
    result = await session.execute(
        select(Workflow)
        .where(Workflow.id == workflow_id)
        .options(
            selectinload(Workflow.task_refs),
            selectinload(Workflow.principle_refs),
        )
    )
    workflow = result.scalar_one_or_none()
    if workflow is None:
        raise HTTPException(status_code=404, detail="Workflow not found.")
    return workflow


@router.post("", response_model=WorkflowResponse, status_code=status.HTTP_201_CREATED)
async def create_workflow(
    body: WorkflowCreate, session: DBSession, user: _Writer
) -> WorkflowResponse:
    workflow = Workflow(
        title=body.title,
        objective=body.objective,
        domain=body.domain,
        tags=body.tags,
        created_by=user.id,
        updated_by=user.id,
    )
    session.add(workflow)
    await session.commit()
    return WorkflowResponse.model_validate(await _get_workflow_with_refs(session, workflow.id))


@router.get("", response_model=list[WorkflowResponse])
async def list_workflows(session: DBSession, user: CurrentUser) -> list[WorkflowResponse]:
    result = await session.execute(
        select(Workflow)
        .options(selectinload(Workflow.task_refs), selectinload(Workflow.principle_refs))
        .order_by(Workflow.created_at.desc())
    )
    return [WorkflowResponse.model_validate(w) for w in result.scalars().all()]


@router.get("/{workflow_id}", response_model=WorkflowResponse)
async def get_workflow(
    workflow_id: uuid.UUID, session: DBSession, user: CurrentUser
) -> WorkflowResponse:
    return WorkflowResponse.model_validate(await _get_workflow_with_refs(session, workflow_id))


@router.patch("/{workflow_id}", response_model=WorkflowResponse)
async def update_workflow(
    workflow_id: uuid.UUID, body: WorkflowUpdate, session: DBSession, user: _Writer
) -> WorkflowResponse:
    workflow = await _get_workflow_with_refs(session, workflow_id)
    lifecycle.assert_can_edit(workflow.status)
    if body.title is not None:
        workflow.title = body.title
    if body.objective is not None:
        workflow.objective = body.objective
    if body.domain is not None:
        workflow.domain = body.domain
    if body.tags is not None:
        workflow.tags = body.tags
    workflow.updated_by = user.id
    await session.commit()
    return WorkflowResponse.model_validate(await _get_workflow_with_refs(session, workflow.id))


@router.post("/{workflow_id}/submit", response_model=WorkflowResponse)
async def submit_workflow(
    workflow_id: uuid.UUID, session: DBSession, user: _Writer
) -> WorkflowResponse:
    workflow = await _get_workflow_with_refs(session, workflow_id)
    lifecycle.assert_can_submit(workflow.status, user)
    workflow.status = "submitted"
    workflow.updated_by = user.id
    await session.commit()
    return WorkflowResponse.model_validate(await _get_workflow_with_refs(session, workflow.id))


@router.post("/{workflow_id}/confirm", response_model=WorkflowResponse)
async def confirm_workflow(
    workflow_id: uuid.UUID, session: DBSession, user: _Writer
) -> WorkflowResponse:
    workflow = await _get_workflow_with_refs(session, workflow_id)
    lifecycle.assert_can_confirm(workflow.status, workflow.created_by, user)
    workflow.status = "confirmed"
    workflow.reviewed_by = user.id
    workflow.updated_by = user.id
    await session.commit()
    log.info("workflow_confirmed", workflow_id=str(workflow.id), user_id=str(user.id))
    return WorkflowResponse.model_validate(await _get_workflow_with_refs(session, workflow.id))


@router.post("/{workflow_id}/return", response_model=WorkflowResponse)
async def return_workflow(
    workflow_id: uuid.UUID, body: ReturnRequest, session: DBSession, user: _Writer
) -> WorkflowResponse:
    workflow = await _get_workflow_with_refs(session, workflow_id)
    lifecycle.assert_can_return(workflow.status, user)
    workflow.status = "returned"
    if body.note:
        workflow.change_note = body.note
    workflow.reviewed_by = user.id
    workflow.updated_by = user.id
    await session.commit()
    return WorkflowResponse.model_validate(await _get_workflow_with_refs(session, workflow.id))


@router.post("/{workflow_id}/deprecate", response_model=WorkflowResponse)
async def deprecate_workflow(
    workflow_id: uuid.UUID, session: DBSession, user: _Admin
) -> WorkflowResponse:
    workflow = await _get_workflow_with_refs(session, workflow_id)
    lifecycle.assert_can_deprecate(workflow.status, user)
    workflow.status = "deprecated"
    workflow.updated_by = user.id
    await session.commit()
    return WorkflowResponse.model_validate(await _get_workflow_with_refs(session, workflow.id))


@router.post("/{workflow_id}/retire", response_model=WorkflowResponse)
async def retire_workflow(
    workflow_id: uuid.UUID, session: DBSession, user: _Admin
) -> WorkflowResponse:
    workflow = await _get_workflow_with_refs(session, workflow_id)
    lifecycle.assert_can_retire(workflow.status, user)
    workflow.status = "retired"
    workflow.updated_by = user.id
    await session.commit()
    return WorkflowResponse.model_validate(await _get_workflow_with_refs(session, workflow.id))


# ---------------------------------------------------------------------------
# Task refs
# ---------------------------------------------------------------------------

@router.post(
    "/{workflow_id}/task-refs",
    response_model=WorkflowTaskRefResponse,
    status_code=status.HTTP_201_CREATED,
)
async def add_task_ref(
    workflow_id: uuid.UUID, body: WorkflowTaskRefCreate, session: DBSession, user: _Writer
) -> WorkflowTaskRefResponse:
    workflow = await _get_workflow_with_refs(session, workflow_id)
    lifecycle.assert_can_mutate_refs(workflow.status)

    # Only confirmed Tasks may be referenced (§9.5)
    task_result = await session.execute(
        select(Task).where(Task.record_id == body.task_record_id, Task.status == "confirmed")
    )
    if task_result.scalar_one_or_none() is None:
        raise HTTPException(status_code=422, detail="No confirmed Task found with that record_id.")

    next_index = len(workflow.task_refs)
    ref = WorkflowTaskRef(
        workflow_id=workflow.id,
        task_record_id=body.task_record_id,
        order_index=next_index,
    )
    session.add(ref)
    await session.commit()
    await session.refresh(ref)
    return WorkflowTaskRefResponse.model_validate(ref)


@router.delete(
    "/{workflow_id}/task-refs/{task_record_id}", status_code=status.HTTP_204_NO_CONTENT
)
async def remove_task_ref(
    workflow_id: uuid.UUID, task_record_id: uuid.UUID, session: DBSession, user: _Writer
) -> None:
    wf_result = await session.execute(select(Workflow).where(Workflow.id == workflow_id))
    workflow = wf_result.scalar_one_or_none()
    if workflow is None:
        raise HTTPException(status_code=404, detail="Workflow not found.")
    lifecycle.assert_can_mutate_refs(workflow.status)

    ref_result = await session.execute(
        select(WorkflowTaskRef).where(
            WorkflowTaskRef.workflow_id == workflow_id,
            WorkflowTaskRef.task_record_id == task_record_id,
        )
    )
    ref = ref_result.scalar_one_or_none()
    if ref is None:
        raise HTTPException(status_code=404, detail="Task ref not found.")
    await session.delete(ref)
    await session.commit()


# ---------------------------------------------------------------------------
# Principle refs
# ---------------------------------------------------------------------------

@router.post(
    "/{workflow_id}/principle-refs",
    response_model=WorkflowPrincipleRefResponse,
    status_code=status.HTTP_201_CREATED,
)
async def attach_principle(
    workflow_id: uuid.UUID, body: WorkflowPrincipleRefCreate, session: DBSession, user: _Writer
) -> WorkflowPrincipleRefResponse:
    workflow = await _get_workflow_with_refs(session, workflow_id)
    lifecycle.assert_can_mutate_refs(workflow.status)

    # Only confirmed Principles may be attached (§9.5)
    p_result = await session.execute(
        select(Principle).where(
            Principle.record_id == body.principle_record_id, Principle.status == "confirmed"
        )
    )
    if p_result.scalar_one_or_none() is None:
        raise HTTPException(
            status_code=422, detail="No confirmed Principle found with that record_id."
        )

    ref = WorkflowPrincipleRef(
        workflow_id=workflow.id,
        principle_record_id=body.principle_record_id,
        attached_at=datetime.now(tz=UTC),
        attached_by=user.id,
    )
    session.add(ref)
    await session.commit()
    await session.refresh(ref)
    return WorkflowPrincipleRefResponse.model_validate(ref)


@router.delete(
    "/{workflow_id}/principle-refs/{principle_record_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def detach_principle(
    workflow_id: uuid.UUID,
    principle_record_id: uuid.UUID,
    session: DBSession,
    user: _Writer,
) -> None:
    wf_result = await session.execute(select(Workflow).where(Workflow.id == workflow_id))
    workflow = wf_result.scalar_one_or_none()
    if workflow is None:
        raise HTTPException(status_code=404, detail="Workflow not found.")
    lifecycle.assert_can_mutate_refs(workflow.status)

    ref_result = await session.execute(
        select(WorkflowPrincipleRef).where(
            WorkflowPrincipleRef.workflow_id == workflow_id,
            WorkflowPrincipleRef.principle_record_id == principle_record_id,
        )
    )
    ref = ref_result.scalar_one_or_none()
    if ref is None:
        raise HTTPException(status_code=404, detail="Principle ref not found.")
    await session.delete(ref)
    await session.commit()
