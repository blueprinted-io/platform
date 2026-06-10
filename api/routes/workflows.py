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
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from api.auth import Role
from api.dependencies import ArqPool, CurrentUser, DBSession, require_role
from api.models.principle import Principle
from api.models.task import Task
from api.models.user import User
from api.models.workflow import Workflow, WorkflowPrincipleRef, WorkflowTaskRef
from api.schemas.base import ConfirmRequest
from api.schemas.workflow import (
    ReturnRequest,
    ReviseRequest,
    WorkflowCreate,
    WorkflowDiffResponse,
    WorkflowPrincipleRefCreate,
    WorkflowPrincipleRefResponse,
    WorkflowResponse,
    WorkflowTaskRefCreate,
    WorkflowTaskRefResponse,
    WorkflowUpdate,
    WorkflowVersionSummary,
)
from api.services import lifecycle, lifecycle_actions
from api.services.notifications import create_notification, notify_domain_users

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
    await lifecycle.assert_domain_active(body.domain, session)
    await lifecycle.assert_domain_access(body.domain, user, session)
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
    latest = (
        select(Workflow.record_id, func.max(Workflow.version).label("max_version"))
        .group_by(Workflow.record_id)
        .subquery()
    )
    result = await session.execute(
        select(Workflow)
        .join(
            latest,
            (Workflow.record_id == latest.c.record_id) & (Workflow.version == latest.c.max_version),
        )
        .options(selectinload(Workflow.task_refs), selectinload(Workflow.principle_refs))
        .order_by(Workflow.created_at.desc())
    )
    return [WorkflowResponse.model_validate(w) for w in result.scalars().all()]


@router.get("/{record_id}/versions", response_model=list[WorkflowVersionSummary])
async def list_workflow_versions(
    record_id: uuid.UUID, session: DBSession, user: CurrentUser
) -> list[WorkflowVersionSummary]:
    result = await session.execute(
        select(Workflow).where(Workflow.record_id == record_id).order_by(Workflow.version.desc())
    )
    workflows = result.scalars().all()
    if not workflows:
        raise HTTPException(status_code=404, detail="Workflow not found.")
    return [WorkflowVersionSummary.model_validate(w) for w in workflows]


@router.get("/{workflow_id}", response_model=WorkflowResponse)
async def get_workflow(
    workflow_id: uuid.UUID, session: DBSession, user: CurrentUser
) -> WorkflowResponse:
    return WorkflowResponse.model_validate(await _get_workflow_with_refs(session, workflow_id))


@router.get("/{workflow_id}/diff", response_model=WorkflowDiffResponse)
async def get_workflow_diff(
    workflow_id: uuid.UUID, session: DBSession, user: _Writer
) -> WorkflowDiffResponse:
    current = await _get_workflow_with_refs(session, workflow_id)
    if current.version < 2:
        raise HTTPException(status_code=404, detail="No previous version to diff against.")
    result = await session.execute(
        select(Workflow)
        .where(Workflow.record_id == current.record_id, Workflow.version == current.version - 1)
        .options(selectinload(Workflow.task_refs), selectinload(Workflow.principle_refs))
    )
    previous = result.scalar_one_or_none()
    if previous is None:
        raise HTTPException(status_code=404, detail="Previous version not found.")
    return WorkflowDiffResponse(
        current=WorkflowResponse.model_validate(current),
        previous=WorkflowResponse.model_validate(previous),
    )


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
        await lifecycle.assert_domain_active(body.domain, session)
        await lifecycle.assert_domain_access(body.domain, user, session)
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
    await lifecycle.assert_domain_access(workflow.domain, user, session)
    workflow.status = "submitted"
    workflow.updated_by = user.id
    await session.commit()
    await notify_domain_users(
        session, workflow.domain, "record_submitted", "workflow", workflow.id,
        f'Workflow "{workflow.title}" has been submitted for review.',
        exclude_user_id=user.id,
    )
    await session.commit()
    return WorkflowResponse.model_validate(await _get_workflow_with_refs(session, workflow.id))


@router.post("/{workflow_id}/confirm", response_model=WorkflowResponse)
async def confirm_workflow(
    workflow_id: uuid.UUID,
    session: DBSession,
    user: _Writer,
    arq_pool: ArqPool,
    body: ConfirmRequest | None = None,
) -> WorkflowResponse:
    workflow = await _get_workflow_with_refs(session, workflow_id)
    await lifecycle.assert_domain_access(workflow.domain, user, session)
    await lifecycle.assert_no_foreign_claim("workflow", workflow.id, user, session)
    await lifecycle_actions.confirm_record(
        workflow, session, user, body.justification if body else None, "workflow"
    )
    await create_notification(
        session, workflow.created_by, "record_confirmed", "workflow", workflow.id,
        f'Your workflow "{workflow.title}" has been confirmed.',
    )
    await session.commit()
    if arq_pool is not None:
        await arq_pool.enqueue_job(
            "generate_embedding", record_type="workflow", record_id=str(workflow.id)
        )
    return WorkflowResponse.model_validate(await _get_workflow_with_refs(session, workflow.id))


@router.post("/{workflow_id}/return", response_model=WorkflowResponse)
async def return_workflow(
    workflow_id: uuid.UUID, body: ReturnRequest, session: DBSession, user: _Writer
) -> WorkflowResponse:
    workflow = await _get_workflow_with_refs(session, workflow_id)
    await lifecycle.assert_domain_access(workflow.domain, user, session)
    await lifecycle.assert_no_foreign_claim("workflow", workflow.id, user, session)
    await lifecycle_actions.return_record(
        workflow, session, user, body.note, body.severity, "workflow"
    )
    await create_notification(
        session, workflow.created_by, "record_returned", "workflow", workflow.id,
        f'Your workflow "{workflow.title}" has been returned for changes.',
    )
    await session.commit()
    return WorkflowResponse.model_validate(await _get_workflow_with_refs(session, workflow.id))


@router.post("/{workflow_id}/deprecate", response_model=WorkflowResponse)
async def deprecate_workflow(
    workflow_id: uuid.UUID, session: DBSession, user: _Admin
) -> WorkflowResponse:
    workflow = await _get_workflow_with_refs(session, workflow_id)
    await lifecycle_actions.deprecate_record(workflow, session, user, "workflow")
    return WorkflowResponse.model_validate(await _get_workflow_with_refs(session, workflow.id))


@router.post("/{workflow_id}/retire", response_model=WorkflowResponse)
async def retire_workflow(
    workflow_id: uuid.UUID, session: DBSession, user: _Admin
) -> WorkflowResponse:
    workflow = await _get_workflow_with_refs(session, workflow_id)
    await lifecycle_actions.retire_record(workflow, session, user, "workflow")
    return WorkflowResponse.model_validate(await _get_workflow_with_refs(session, workflow.id))


@router.post(
    "/{workflow_id}/revise",
    response_model=WorkflowResponse,
    status_code=status.HTTP_201_CREATED,
)
async def revise_workflow(
    workflow_id: uuid.UUID, session: DBSession, user: _Writer,
    body: ReviseRequest | None = None,
) -> WorkflowResponse:
    """Create a new draft version of a workflow (§9.3).

    Returned workflows inherit the return note; all other statuses require an explicit note.
    """
    old = await _get_workflow_with_refs(session, workflow_id)
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
        select(Workflow).where(Workflow.record_id == old.record_id, Workflow.version == new_version)
    )
    if existing is not None:
        raise HTTPException(
            status_code=409, detail="A revised draft for this record already exists."
        )

    new_wf = Workflow(
        record_id=old.record_id,
        version=new_version,
        status="draft",
        title=old.title,
        objective=old.objective,
        domain=old.domain,
        tags=list(old.tags),
        change_note=change_note,
        created_by=user.id,
        updated_by=user.id,
    )
    session.add(new_wf)
    await session.flush()
    new_wf_id = new_wf.id

    for task_ref in old.task_refs:
        session.add(WorkflowTaskRef(
            workflow_id=new_wf.id,
            task_record_id=task_ref.task_record_id,
            order_index=task_ref.order_index,
        ))
    for principle_ref in old.principle_refs:
        session.add(WorkflowPrincipleRef(
            workflow_id=new_wf.id,
            principle_record_id=principle_ref.principle_record_id,
            attached_at=datetime.now(tz=UTC),
            attached_by=user.id,
        ))

    await session.commit()
    log.info(
        "workflow_revised",
        old_workflow_id=str(workflow_id),
        new_workflow_id=str(new_wf_id),
        new_version=new_version,
        user_id=str(user.id),
    )
    return WorkflowResponse.model_validate(await _get_workflow_with_refs(session, new_wf_id))


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
    if task_result.scalars().first() is None:
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
    if p_result.scalars().first() is None:
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
