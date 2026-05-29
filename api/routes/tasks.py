"""Tasks API endpoints, including steps.

§9.5  — Tasks schema: steps with actions, notes, images
§9.3  — Lifecycle state machine
§10.1 — No machine can confirm
§5.1  — Self-review prohibition
"""

import uuid
from typing import Annotated

import structlog
from fastapi import APIRouter, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from api.auth import Role
from api.dependencies import ArqPool, CurrentUser, DBSession, require_role
from api.models.task import Task, TaskStep, TaskStepAction
from api.models.user import User
from api.schemas.base import ConfirmRequest
from api.schemas.task import (
    ReturnRequest,
    ReviseRequest,
    TaskCreate,
    TaskDiffResponse,
    TaskResponse,
    TaskStepCreate,
    TaskStepResponse,
    TaskStepUpdate,
    TaskUpdate,
    TaskVersionSummary,
)
from api.services import lifecycle
from api.services.notifications import create_notification, notify_domain_users

log = structlog.get_logger(__name__)

router = APIRouter(prefix="/tasks", tags=["tasks"])

_Writer = Annotated[User, require_role(Role.CONTRIBUTOR, Role.ADMIN)]
_Admin = Annotated[User, require_role(Role.ADMIN)]


async def _get_task(session: AsyncSession, task_id: uuid.UUID) -> Task:
    """Fetch a Task with all sub-resources loaded."""
    result = await session.execute(
        select(Task)
        .where(Task.id == task_id)
        .options(
            selectinload(Task.steps)
            .selectinload(TaskStep.actions),
            selectinload(Task.steps)
            .selectinload(TaskStep.images),
        )
    )
    task = result.scalar_one_or_none()
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found.")
    return task


async def _get_task_by_record_version(
    session: AsyncSession, record_id: uuid.UUID, version: int
) -> Task:
    """Fetch a specific version of a Task by its stable record_id and version number."""
    result = await session.execute(
        select(Task)
        .where(Task.record_id == record_id, Task.version == version)
        .options(
            selectinload(Task.steps).selectinload(TaskStep.actions),
            selectinload(Task.steps).selectinload(TaskStep.images),
        )
    )
    task = result.scalar_one_or_none()
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found.")
    return task


@router.post("", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
async def create_task(body: TaskCreate, session: DBSession, user: _Writer) -> TaskResponse:
    await lifecycle.assert_domain_active(body.domain, session)
    await lifecycle.assert_domain_access(body.domain, user, session)
    task = Task(
        title=body.title,
        outcome=body.outcome,
        domain=body.domain,
        software_name=body.software_name,
        software_version=body.software_version,
        media_url=body.media_url,
        facts=body.facts or None,
        concepts=body.concepts or None,
        tags=body.tags,
        created_by=user.id,
        updated_by=user.id,
    )
    session.add(task)
    await session.commit()
    return TaskResponse.model_validate(await _get_task(session, task.id))


@router.get("", response_model=list[TaskResponse])
async def list_tasks(session: DBSession, user: CurrentUser) -> list[TaskResponse]:
    # Only return the latest version of each record.
    latest = (
        select(Task.record_id, func.max(Task.version).label("max_version"))
        .group_by(Task.record_id)
        .subquery()
    )
    result = await session.execute(
        select(Task)
        .join(
            latest,
            (Task.record_id == latest.c.record_id) & (Task.version == latest.c.max_version),
        )
        .options(
            selectinload(Task.steps).selectinload(TaskStep.actions),
            selectinload(Task.steps).selectinload(TaskStep.images),
        )
        .order_by(Task.created_at.desc())
    )
    return [TaskResponse.model_validate(t) for t in result.scalars().all()]


@router.get("/{record_id}/versions", response_model=list[TaskVersionSummary])
async def list_task_versions(
    record_id: uuid.UUID, session: DBSession, user: CurrentUser
) -> list[TaskVersionSummary]:
    result = await session.execute(
        select(Task).where(Task.record_id == record_id).order_by(Task.version.desc())
    )
    tasks = result.scalars().all()
    if not tasks:
        raise HTTPException(status_code=404, detail="Task not found.")
    return [TaskVersionSummary.model_validate(t) for t in tasks]


@router.get("/{task_id}", response_model=TaskResponse)
async def get_task(task_id: uuid.UUID, session: DBSession, user: CurrentUser) -> TaskResponse:
    return TaskResponse.model_validate(await _get_task(session, task_id))


@router.get("/{record_id}/{version}", response_model=TaskResponse)
async def get_task_version(
    record_id: uuid.UUID, version: int, session: DBSession, user: CurrentUser
) -> TaskResponse:
    return TaskResponse.model_validate(
        await _get_task_by_record_version(session, record_id, version)
    )


@router.get("/{record_id}/{version}/diff", response_model=TaskDiffResponse)
async def get_task_diff(
    record_id: uuid.UUID, version: int, session: DBSession, user: _Writer
) -> TaskDiffResponse:
    if version < 2:
        raise HTTPException(status_code=404, detail="No previous version to diff against.")
    current = await _get_task_by_record_version(session, record_id, version)
    previous = await _get_task_by_record_version(session, record_id, version - 1)
    return TaskDiffResponse(
        current=TaskResponse.model_validate(current),
        previous=TaskResponse.model_validate(previous),
    )


@router.patch("/{task_id}", response_model=TaskResponse)
async def update_task(
    task_id: uuid.UUID, body: TaskUpdate, session: DBSession, user: _Writer
) -> TaskResponse:
    task = await _get_task(session, task_id)
    lifecycle.assert_can_edit(task.status)
    if body.title is not None:
        task.title = body.title
    if body.outcome is not None:
        task.outcome = body.outcome
    if body.domain is not None:
        await lifecycle.assert_domain_active(body.domain, session)
        await lifecycle.assert_domain_access(body.domain, user, session)
        task.domain = body.domain
    if body.software_name is not None:
        task.software_name = body.software_name
    if body.software_version is not None:
        task.software_version = body.software_version
    if body.media_url is not None:
        task.media_url = body.media_url
    if body.facts is not None:
        task.facts = body.facts or None
    if body.concepts is not None:
        task.concepts = body.concepts or None
    if body.tags is not None:
        task.tags = body.tags
    task.updated_by = user.id
    await session.commit()
    return TaskResponse.model_validate(await _get_task(session, task.id))


@router.post("/{task_id}/submit", response_model=TaskResponse)
async def submit_task(task_id: uuid.UUID, session: DBSession, user: _Writer) -> TaskResponse:
    task = await _get_task(session, task_id)
    lifecycle.assert_can_submit(task.status, user)
    await lifecycle.assert_domain_access(task.domain, user, session)
    task.status = "submitted"
    task.updated_by = user.id
    await session.commit()
    await notify_domain_users(
        session, task.domain, "record_submitted", "task", task.id,
        f'Task "{task.title}" has been submitted for review.',
        exclude_user_id=user.id,
    )
    await session.commit()
    return TaskResponse.model_validate(await _get_task(session, task.id))


@router.post("/{task_id}/confirm", response_model=TaskResponse)
async def confirm_task(
    task_id: uuid.UUID,
    session: DBSession,
    user: _Writer,
    arq_pool: ArqPool,
    body: ConfirmRequest | None = None,
) -> TaskResponse:
    task = await _get_task(session, task_id)
    await lifecycle.assert_domain_access(task.domain, user, session)
    await lifecycle.assert_no_foreign_claim("task", task.id, user, session)
    is_break_glass = lifecycle.assert_can_confirm(
        task.status, task.created_by, user, body.justification if body else None
    )
    task.status = "confirmed"
    task.self_confirmed_by_admin = is_break_glass
    task.reviewed_by = user.id
    task.updated_by = user.id
    await session.commit()
    log.info("task_confirmed", task_id=str(task.id), user_id=str(user.id))
    await create_notification(
        session, task.created_by, "record_confirmed", "task", task.id,
        f'Your task "{task.title}" has been confirmed.',
    )
    await session.commit()
    if arq_pool is not None:
        await arq_pool.enqueue_job("generate_embedding", record_type="task", record_id=str(task.id))
    return TaskResponse.model_validate(await _get_task(session, task.id))


@router.post("/{task_id}/return", response_model=TaskResponse)
async def return_task(
    task_id: uuid.UUID, body: ReturnRequest, session: DBSession, user: _Writer
) -> TaskResponse:
    task = await _get_task(session, task_id)
    lifecycle.assert_can_return(task.status, user)
    await lifecycle.assert_domain_access(task.domain, user, session)
    await lifecycle.assert_no_foreign_claim("task", task.id, user, session)
    task.status = "returned"
    if body.note:
        task.change_note = body.note
    task.reviewed_by = user.id
    task.updated_by = user.id
    await session.commit()
    await create_notification(
        session, task.created_by, "record_returned", "task", task.id,
        f'Your task "{task.title}" has been returned for changes.',
    )
    await session.commit()
    return TaskResponse.model_validate(await _get_task(session, task.id))


@router.post("/{task_id}/deprecate", response_model=TaskResponse)
async def deprecate_task(task_id: uuid.UUID, session: DBSession, user: _Admin) -> TaskResponse:
    task = await _get_task(session, task_id)
    lifecycle.assert_can_deprecate(task.status, user)
    task.status = "deprecated"
    task.updated_by = user.id
    await session.commit()
    return TaskResponse.model_validate(await _get_task(session, task.id))


@router.post("/{task_id}/retire", response_model=TaskResponse)
async def retire_task(task_id: uuid.UUID, session: DBSession, user: _Admin) -> TaskResponse:
    task = await _get_task(session, task_id)
    lifecycle.assert_can_retire(task.status, user)
    task.status = "retired"
    task.updated_by = user.id
    await session.commit()
    return TaskResponse.model_validate(await _get_task(session, task.id))


@router.post(
    "/{record_id}/{version}/revise",
    response_model=TaskResponse,
    status_code=status.HTTP_201_CREATED,
)
async def revise_task(
    record_id: uuid.UUID, version: int, session: DBSession, user: _Writer,
    body: ReviseRequest | None = None,
) -> TaskResponse:
    """Create a new draft version of a task (§9.3).

    Copies all fields and steps from the source version. The source version
    remains unchanged; the new row gets record_id/version+1 and status=draft.
    Returned tasks inherit the return note as the revision note; all other
    statuses require an explicit note in the request body.
    """
    old = await _get_task_by_record_version(session, record_id, version)
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
        select(Task).where(Task.record_id == old.record_id, Task.version == new_version)
    )
    if existing is not None:
        raise HTTPException(
            status_code=409, detail="A revised draft for this record already exists."
        )
    new_task = Task(
        record_id=old.record_id,
        version=new_version,
        status="draft",
        title=old.title,
        outcome=old.outcome,
        domain=old.domain,
        software_name=old.software_name,
        software_version=old.software_version,
        media_url=old.media_url,
        facts=old.facts,
        concepts=old.concepts,
        tags=list(old.tags),
        change_note=change_note,
        created_by=user.id,
        updated_by=user.id,
    )
    session.add(new_task)
    await session.flush()
    new_task_id = new_task.id  # capture before commit expires the object

    for old_step in old.steps:
        new_step = TaskStep(
            task_id=new_task.id,
            order_index=old_step.order_index,
            step=old_step.step,
            notes=old_step.notes,
            completion=old_step.completion,
            irreversible=old_step.irreversible,
        )
        session.add(new_step)
        await session.flush()
        for old_action in old_step.actions:
            session.add(TaskStepAction(
                step_id=new_step.id,
                order_index=old_action.order_index,
                instruction=old_action.instruction,
            ))

    await session.commit()
    log.info(
        "task_revised",
        record_id=str(record_id),
        old_version=version,
        new_version=new_version,
        user_id=str(user.id),
    )
    return TaskResponse.model_validate(await _get_task(session, new_task_id))


# ---------------------------------------------------------------------------
# Steps
# ---------------------------------------------------------------------------

@router.post(
    "/{task_id}/steps", response_model=TaskStepResponse, status_code=status.HTTP_201_CREATED
)
async def add_step(
    task_id: uuid.UUID, body: TaskStepCreate, session: DBSession, user: _Writer
) -> TaskStepResponse:
    task = await _get_task(session, task_id)
    lifecycle.assert_can_mutate_refs(task.status)

    next_index = len(task.steps)
    step = TaskStep(
        task_id=task.id,
        order_index=next_index,
        step=body.step,
        completion=body.completion,
        notes=body.notes,
        irreversible=body.irreversible,
    )
    session.add(step)
    await session.flush()

    for i, action_body in enumerate(body.actions):
        session.add(TaskStepAction(
            step_id=step.id,
            order_index=i,
            instruction=action_body.instruction,
        ))

    await session.commit()

    result = await session.execute(
        select(TaskStep)
        .where(TaskStep.id == step.id)
        .options(selectinload(TaskStep.actions), selectinload(TaskStep.images))
    )
    return TaskStepResponse.model_validate(result.scalar_one())


@router.patch("/{task_id}/steps/{step_id}", response_model=TaskStepResponse)
async def update_step(
    task_id: uuid.UUID,
    step_id: uuid.UUID,
    body: TaskStepUpdate,
    session: DBSession,
    user: _Writer,
) -> TaskStepResponse:
    task_result = await session.execute(select(Task).where(Task.id == task_id))
    task = task_result.scalar_one_or_none()
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found.")
    lifecycle.assert_can_mutate_refs(task.status)

    result = await session.execute(
        select(TaskStep)
        .where(TaskStep.id == step_id, TaskStep.task_id == task_id)
        .options(selectinload(TaskStep.actions), selectinload(TaskStep.images))
    )
    step = result.scalar_one_or_none()
    if step is None:
        raise HTTPException(status_code=404, detail="Step not found.")

    if body.step is not None:
        step.step = body.step
    if body.completion is not None:
        step.completion = body.completion
    if body.notes is not None:
        step.notes = body.notes
    if body.irreversible is not None:
        step.irreversible = body.irreversible

    await session.commit()

    result2 = await session.execute(
        select(TaskStep)
        .where(TaskStep.id == step_id)
        .options(selectinload(TaskStep.actions), selectinload(TaskStep.images))
    )
    return TaskStepResponse.model_validate(result2.scalar_one())


@router.delete("/{task_id}/steps/{step_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_step(
    task_id: uuid.UUID, step_id: uuid.UUID, session: DBSession, user: _Writer
) -> None:
    task_result = await session.execute(select(Task).where(Task.id == task_id))
    task = task_result.scalar_one_or_none()
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found.")
    lifecycle.assert_can_mutate_refs(task.status)

    step_result = await session.execute(
        select(TaskStep).where(TaskStep.id == step_id, TaskStep.task_id == task_id)
    )
    step = step_result.scalar_one_or_none()
    if step is None:
        raise HTTPException(status_code=404, detail="Step not found.")

    await session.delete(step)
    await session.commit()
