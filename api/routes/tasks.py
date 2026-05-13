"""Tasks API endpoints, including steps and fact/concept refs.

§9.5  — Tasks schema: steps, fact-refs, concept-refs
§9.3  — Lifecycle state machine
§10.1 — Immutability: confirmed tasks cannot have steps/refs added
§5.1  — Self-review prohibition
"""

import uuid
from typing import Annotated

import structlog
from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from api.auth import Role
from api.dependencies import CurrentUser, DBSession, require_role
from api.models.concept import Concept
from api.models.fact import Fact
from api.models.task import Task, TaskConceptRef, TaskFactRef, TaskStep, TaskStepAction
from api.models.user import User
from api.schemas.task import (
    ReturnRequest,
    TaskConceptRefCreate,
    TaskConceptRefResponse,
    TaskCreate,
    TaskFactRefCreate,
    TaskFactRefResponse,
    TaskResponse,
    TaskStepCreate,
    TaskStepResponse,
    TaskStepUpdate,
    TaskUpdate,
)
from api.services import lifecycle

log = structlog.get_logger(__name__)

router = APIRouter(prefix="/tasks", tags=["tasks"])

_Writer = Annotated[User, require_role(Role.CONTRIBUTOR, Role.ADMIN)]
_Admin = Annotated[User, require_role(Role.ADMIN)]


async def _get_task_with_refs(session: AsyncSession, task_id: uuid.UUID) -> Task:
    """Fetch a Task with all sub-resources loaded."""
    result = await session.execute(
        select(Task)
        .where(Task.id == task_id)
        .options(
            selectinload(Task.steps).selectinload(TaskStep.actions),
            selectinload(Task.fact_refs),
            selectinload(Task.concept_refs),
        )
    )
    task = result.scalar_one_or_none()
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found.")
    return task


@router.post("", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
async def create_task(body: TaskCreate, session: DBSession, user: _Writer) -> TaskResponse:
    task = Task(
        title=body.title,
        outcome=body.outcome,
        procedure_name=body.procedure_name,
        domain=body.domain,
        software_name=body.software_name,
        software_version=body.software_version,
        media_url=body.media_url,
        tags=body.tags,
        created_by=user.id,
        updated_by=user.id,
    )
    session.add(task)
    await session.commit()
    return TaskResponse.model_validate(await _get_task_with_refs(session, task.id))


@router.get("", response_model=list[TaskResponse])
async def list_tasks(session: DBSession, user: CurrentUser) -> list[TaskResponse]:
    result = await session.execute(
        select(Task)
        .options(
            selectinload(Task.steps).selectinload(TaskStep.actions),
            selectinload(Task.fact_refs),
            selectinload(Task.concept_refs),
        )
        .order_by(Task.created_at.desc())
    )
    return [TaskResponse.model_validate(t) for t in result.scalars().all()]


@router.get("/{task_id}", response_model=TaskResponse)
async def get_task(task_id: uuid.UUID, session: DBSession, user: CurrentUser) -> TaskResponse:
    return TaskResponse.model_validate(await _get_task_with_refs(session, task_id))


@router.patch("/{task_id}", response_model=TaskResponse)
async def update_task(
    task_id: uuid.UUID, body: TaskUpdate, session: DBSession, user: _Writer
) -> TaskResponse:
    task = await _get_task_with_refs(session, task_id)
    lifecycle.assert_can_edit(task.status)
    if body.title is not None:
        task.title = body.title
    if body.outcome is not None:
        task.outcome = body.outcome
    if body.procedure_name is not None:
        task.procedure_name = body.procedure_name
    if body.domain is not None:
        task.domain = body.domain
    if body.software_name is not None:
        task.software_name = body.software_name
    if body.software_version is not None:
        task.software_version = body.software_version
    if body.media_url is not None:
        task.media_url = body.media_url
    if body.tags is not None:
        task.tags = body.tags
    task.updated_by = user.id
    await session.commit()
    return TaskResponse.model_validate(await _get_task_with_refs(session, task.id))


@router.post("/{task_id}/submit", response_model=TaskResponse)
async def submit_task(task_id: uuid.UUID, session: DBSession, user: _Writer) -> TaskResponse:
    task = await _get_task_with_refs(session, task_id)
    lifecycle.assert_can_submit(task.status, user)
    task.status = "submitted"
    task.updated_by = user.id
    await session.commit()
    return TaskResponse.model_validate(await _get_task_with_refs(session, task.id))


@router.post("/{task_id}/confirm", response_model=TaskResponse)
async def confirm_task(task_id: uuid.UUID, session: DBSession, user: _Writer) -> TaskResponse:
    task = await _get_task_with_refs(session, task_id)
    lifecycle.assert_can_confirm(task.status, task.created_by, user)
    task.status = "confirmed"
    task.reviewed_by = user.id
    task.updated_by = user.id
    await session.commit()
    log.info("task_confirmed", task_id=str(task.id), user_id=str(user.id))
    return TaskResponse.model_validate(await _get_task_with_refs(session, task.id))


@router.post("/{task_id}/return", response_model=TaskResponse)
async def return_task(
    task_id: uuid.UUID, body: ReturnRequest, session: DBSession, user: _Writer
) -> TaskResponse:
    task = await _get_task_with_refs(session, task_id)
    lifecycle.assert_can_return(task.status, user)
    task.status = "returned"
    if body.note:
        task.change_note = body.note
    task.reviewed_by = user.id
    task.updated_by = user.id
    await session.commit()
    return TaskResponse.model_validate(await _get_task_with_refs(session, task.id))


@router.post("/{task_id}/deprecate", response_model=TaskResponse)
async def deprecate_task(task_id: uuid.UUID, session: DBSession, user: _Admin) -> TaskResponse:
    task = await _get_task_with_refs(session, task_id)
    lifecycle.assert_can_deprecate(task.status, user)
    task.status = "deprecated"
    task.updated_by = user.id
    await session.commit()
    return TaskResponse.model_validate(await _get_task_with_refs(session, task.id))


@router.post("/{task_id}/retire", response_model=TaskResponse)
async def retire_task(task_id: uuid.UUID, session: DBSession, user: _Admin) -> TaskResponse:
    task = await _get_task_with_refs(session, task_id)
    lifecycle.assert_can_retire(task.status, user)
    task.status = "retired"
    task.updated_by = user.id
    await session.commit()
    return TaskResponse.model_validate(await _get_task_with_refs(session, task.id))


# ---------------------------------------------------------------------------
# Steps
# ---------------------------------------------------------------------------

@router.post(
    "/{task_id}/steps", response_model=TaskStepResponse, status_code=status.HTTP_201_CREATED
)
async def add_step(
    task_id: uuid.UUID, body: TaskStepCreate, session: DBSession, user: _Writer
) -> TaskStepResponse:
    task = await _get_task_with_refs(session, task_id)
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
    await session.flush()  # get step.id before creating actions

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
        .options(selectinload(TaskStep.actions))
    )
    loaded_step = result.scalar_one()
    return TaskStepResponse.model_validate(loaded_step)


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
        .options(selectinload(TaskStep.actions))
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
    await session.refresh(step)

    result2 = await session.execute(
        select(TaskStep).where(TaskStep.id == step_id).options(selectinload(TaskStep.actions))
    )
    loaded_step = result2.scalar_one()
    return TaskStepResponse.model_validate(loaded_step)


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


# ---------------------------------------------------------------------------
# Fact refs
# ---------------------------------------------------------------------------

@router.post(
    "/{task_id}/fact-refs",
    response_model=TaskFactRefResponse,
    status_code=status.HTTP_201_CREATED,
)
async def add_fact_ref(
    task_id: uuid.UUID, body: TaskFactRefCreate, session: DBSession, user: _Writer
) -> TaskFactRefResponse:
    task = await _get_task_with_refs(session, task_id)
    lifecycle.assert_can_mutate_refs(task.status)

    # Only confirmed Facts may be referenced (§9.5)
    fact_result = await session.execute(
        select(Fact).where(Fact.record_id == body.fact_record_id, Fact.status == "confirmed")
    )
    if fact_result.scalar_one_or_none() is None:
        raise HTTPException(status_code=422, detail="No confirmed Fact found with that record_id.")

    next_index = len(task.fact_refs)
    ref = TaskFactRef(task_id=task.id, fact_record_id=body.fact_record_id, order_index=next_index)
    session.add(ref)
    await session.commit()
    await session.refresh(ref)
    return TaskFactRefResponse.model_validate(ref)


@router.delete("/{task_id}/fact-refs/{fact_record_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_fact_ref(
    task_id: uuid.UUID, fact_record_id: uuid.UUID, session: DBSession, user: _Writer
) -> None:
    task_result = await session.execute(select(Task).where(Task.id == task_id))
    task = task_result.scalar_one_or_none()
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found.")
    lifecycle.assert_can_mutate_refs(task.status)

    ref_result = await session.execute(
        select(TaskFactRef).where(
            TaskFactRef.task_id == task_id,
            TaskFactRef.fact_record_id == fact_record_id,
        )
    )
    ref = ref_result.scalar_one_or_none()
    if ref is None:
        raise HTTPException(status_code=404, detail="Fact ref not found.")
    await session.delete(ref)
    await session.commit()


# ---------------------------------------------------------------------------
# Concept refs
# ---------------------------------------------------------------------------

@router.post(
    "/{task_id}/concept-refs",
    response_model=TaskConceptRefResponse,
    status_code=status.HTTP_201_CREATED,
)
async def add_concept_ref(
    task_id: uuid.UUID, body: TaskConceptRefCreate, session: DBSession, user: _Writer
) -> TaskConceptRefResponse:
    task = await _get_task_with_refs(session, task_id)
    lifecycle.assert_can_mutate_refs(task.status)

    concept_result = await session.execute(
        select(Concept).where(
            Concept.record_id == body.concept_record_id, Concept.status == "confirmed"
        )
    )
    if concept_result.scalar_one_or_none() is None:
        raise HTTPException(
            status_code=422, detail="No confirmed Concept found with that record_id."
        )

    next_index = len(task.concept_refs)
    ref = TaskConceptRef(
        task_id=task.id,
        concept_record_id=body.concept_record_id,
        order_index=next_index,
    )
    session.add(ref)
    await session.commit()
    await session.refresh(ref)
    return TaskConceptRefResponse.model_validate(ref)


@router.delete(
    "/{task_id}/concept-refs/{concept_record_id}", status_code=status.HTTP_204_NO_CONTENT
)
async def remove_concept_ref(
    task_id: uuid.UUID, concept_record_id: uuid.UUID, session: DBSession, user: _Writer
) -> None:
    task_result = await session.execute(select(Task).where(Task.id == task_id))
    task = task_result.scalar_one_or_none()
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found.")
    lifecycle.assert_can_mutate_refs(task.status)

    ref_result = await session.execute(
        select(TaskConceptRef).where(
            TaskConceptRef.task_id == task_id,
            TaskConceptRef.concept_record_id == concept_record_id,
        )
    )
    ref = ref_result.scalar_one_or_none()
    if ref is None:
        raise HTTPException(status_code=404, detail="Concept ref not found.")
    await session.delete(ref)
    await session.commit()
