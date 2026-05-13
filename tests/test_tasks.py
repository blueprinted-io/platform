"""Tests for the Tasks lifecycle API.

Spec refs:
  §9.3  Lifecycle state machine
  §9.5  Tasks schema (title, outcome, procedure_name, domain, steps, fact-refs, concept-refs)
  §10.1 Immutability once confirmed — applies to Task and all its steps
  §7    Domain scoping (Tasks are domain-scoped)
  §5.1  Human roles and self-review prohibition

Task-specific behaviour beyond the shared lifecycle:
  - Steps (task_steps + task_step_actions) are owned by the Task
  - Fact and Concept references (task_fact_refs, task_concept_refs) are by record_id,
    resolving to the latest confirmed version at read time
  - task.irreversible is derived: True if any step has irreversible=True
  - has_deprecated_fact_ref and has_deprecated_concept_ref are server-managed flags;
    they cannot be set directly and are not accepted in request bodies
  - Steps and refs cannot be added to or removed from a confirmed Task

Assumptions (flag as TEST_REVISED if Sprint 4 diverges):
  - Steps endpoint: POST /api/v1/tasks/{id}/steps
  - Step update: PATCH /api/v1/tasks/{task_id}/steps/{step_id}
  - Step delete: DELETE /api/v1/tasks/{task_id}/steps/{step_id}
  - Fact ref add: POST /api/v1/tasks/{id}/fact-refs
  - Fact ref remove: DELETE /api/v1/tasks/{task_id}/fact-refs/{fact_record_id}
  - Concept ref add: POST /api/v1/tasks/{id}/concept-refs
  - Concept ref remove: DELETE /api/v1/tasks/{task_id}/concept-refs/{concept_record_id}
  - Only confirmed Facts/Concepts may be referenced

All tests are skipped pending Sprint 4 implementation.
"""

from collections.abc import Callable

import pytest
from httpx import AsyncClient

from tests.factories import (
    concept_payload,
    fact_payload,
    task_payload,
    task_step_action_payload,
    task_step_payload,
)

pytestmark = pytest.mark.skip(reason="Sprint 4: Tasks API not yet implemented")


# ---------------------------------------------------------------------------
# Create draft  (POST /api/v1/tasks)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_create_task_unauthenticated_returns_401(client: AsyncClient) -> None:
    response = await client.post("/api/v1/tasks", json=task_payload())
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_create_task_viewer_returns_403(
    client: AsyncClient, make_token: Callable[..., str]
) -> None:
    token = make_token(roles=["viewer"])
    response = await client.post(
        "/api/v1/tasks",
        json=task_payload(),
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_create_task_contributor_returns_201_draft(
    client: AsyncClient, make_token: Callable[..., str]
) -> None:
    token = make_token(roles=["contributor"])
    response = await client.post(
        "/api/v1/tasks",
        json=task_payload(),
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "draft"
    assert body["version"] == 1
    assert "id" in body
    assert "record_id" in body


@pytest.mark.asyncio
async def test_create_task_missing_outcome_returns_422(
    client: AsyncClient, make_token: Callable[..., str]
) -> None:
    token = make_token(roles=["contributor"])
    response = await client.post(
        "/api/v1/tasks",
        json={"title": "A task", "procedure_name": "a-task"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_create_task_missing_procedure_name_returns_422(
    client: AsyncClient, make_token: Callable[..., str]
) -> None:
    token = make_token(roles=["contributor"])
    response = await client.post(
        "/api/v1/tasks",
        json={"title": "A task", "outcome": "Something is done."},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_create_task_response_has_required_fields(
    client: AsyncClient, make_token: Callable[..., str]
) -> None:
    token = make_token(roles=["contributor"])
    response = await client.post(
        "/api/v1/tasks",
        json=task_payload(),
        headers={"Authorization": f"Bearer {token}"},
    )
    body = response.json()
    required = (
        "id", "record_id", "version", "status",
        "title", "outcome", "procedure_name", "domain",
        "irreversible", "has_deprecated_fact_ref", "has_deprecated_concept_ref",
        "steps", "fact_refs", "concept_refs",
        "created_at", "updated_at", "created_by",
    )
    for field in required:
        assert field in body, f"Missing field: {field}"


@pytest.mark.asyncio
async def test_create_task_irreversible_is_false_with_no_steps(
    client: AsyncClient, make_token: Callable[..., str]
) -> None:
    token = make_token(roles=["contributor"])
    response = await client.post(
        "/api/v1/tasks",
        json=task_payload(),
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.json()["irreversible"] is False


# ---------------------------------------------------------------------------
# Steps  (POST /api/v1/tasks/{id}/steps)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_add_step_to_draft_task(
    client: AsyncClient, make_token: Callable[..., str]
) -> None:
    token = make_token(roles=["contributor"])
    create_resp = await client.post(
        "/api/v1/tasks",
        json=task_payload(),
        headers={"Authorization": f"Bearer {token}"},
    )
    task_id = create_resp.json()["id"]

    step_resp = await client.post(
        f"/api/v1/tasks/{task_id}/steps",
        json=task_step_payload(),
        headers={"Authorization": f"Bearer {token}"},
    )
    assert step_resp.status_code == 201
    step = step_resp.json()
    assert "id" in step
    assert step["step"] == task_step_payload()["step"]
    assert step["irreversible"] is False


@pytest.mark.asyncio
async def test_add_irreversible_step_marks_task_irreversible(
    client: AsyncClient, make_token: Callable[..., str]
) -> None:
    """task.irreversible is derived: True when any step is irreversible."""
    token = make_token(roles=["contributor"])
    create_resp = await client.post(
        "/api/v1/tasks",
        json=task_payload(),
        headers={"Authorization": f"Bearer {token}"},
    )
    task_id = create_resp.json()["id"]

    await client.post(
        f"/api/v1/tasks/{task_id}/steps",
        json=task_step_payload(
            step="Drop the legacy table",
            irreversible=True,
            completion="The table no longer exists.",
        ),
        headers={"Authorization": f"Bearer {token}"},
    )

    get_resp = await client.get(
        f"/api/v1/tasks/{task_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert get_resp.json()["irreversible"] is True


@pytest.mark.asyncio
async def test_add_step_with_actions(
    client: AsyncClient, make_token: Callable[..., str]
) -> None:
    token = make_token(roles=["contributor"])
    create_resp = await client.post(
        "/api/v1/tasks",
        json=task_payload(),
        headers={"Authorization": f"Bearer {token}"},
    )
    task_id = create_resp.json()["id"]

    step_resp = await client.post(
        f"/api/v1/tasks/{task_id}/steps",
        json={
            **task_step_payload(),
            "actions": [
                task_step_action_payload(instruction="Run: psql -U postgres"),
                task_step_action_payload(instruction="Run: \\conninfo"),
            ],
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert step_resp.status_code == 201
    assert len(step_resp.json()["actions"]) == 2


@pytest.mark.asyncio
async def test_add_step_to_confirmed_task_returns_422(
    client: AsyncClient, make_token: Callable[..., str]
) -> None:
    """Confirmed tasks are immutable — steps cannot be added after confirmation."""
    author_token = make_token(sub="author-step-immut-001", roles=["contributor"])
    reviewer_token = make_token(sub="reviewer-step-immut-001", roles=["contributor"])

    create_resp = await client.post(
        "/api/v1/tasks",
        json=task_payload(),
        headers={"Authorization": f"Bearer {author_token}"},
    )
    task_id = create_resp.json()["id"]
    await client.post(
        f"/api/v1/tasks/{task_id}/submit",
        headers={"Authorization": f"Bearer {author_token}"},
    )
    await client.post(
        f"/api/v1/tasks/{task_id}/confirm",
        headers={"Authorization": f"Bearer {reviewer_token}"},
    )

    step_resp = await client.post(
        f"/api/v1/tasks/{task_id}/steps",
        json=task_step_payload(),
        headers={"Authorization": f"Bearer {author_token}"},
    )
    assert step_resp.status_code == 422


@pytest.mark.asyncio
async def test_update_step_on_draft_task(
    client: AsyncClient, make_token: Callable[..., str]
) -> None:
    token = make_token(roles=["contributor"])
    create_resp = await client.post(
        "/api/v1/tasks",
        json=task_payload(),
        headers={"Authorization": f"Bearer {token}"},
    )
    task_id = create_resp.json()["id"]
    step_resp = await client.post(
        f"/api/v1/tasks/{task_id}/steps",
        json=task_step_payload(),
        headers={"Authorization": f"Bearer {token}"},
    )
    step_id = step_resp.json()["id"]

    patch_resp = await client.patch(
        f"/api/v1/tasks/{task_id}/steps/{step_id}",
        json={"step": "Updated step label"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert patch_resp.status_code == 200
    assert patch_resp.json()["step"] == "Updated step label"


@pytest.mark.asyncio
async def test_delete_step_from_draft_task(
    client: AsyncClient, make_token: Callable[..., str]
) -> None:
    token = make_token(roles=["contributor"])
    create_resp = await client.post(
        "/api/v1/tasks",
        json=task_payload(),
        headers={"Authorization": f"Bearer {token}"},
    )
    task_id = create_resp.json()["id"]
    step_resp = await client.post(
        f"/api/v1/tasks/{task_id}/steps",
        json=task_step_payload(),
        headers={"Authorization": f"Bearer {token}"},
    )
    step_id = step_resp.json()["id"]

    delete_resp = await client.delete(
        f"/api/v1/tasks/{task_id}/steps/{step_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert delete_resp.status_code == 204


# ---------------------------------------------------------------------------
# Fact and Concept references
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_add_confirmed_fact_ref_to_task(
    client: AsyncClient, make_token: Callable[..., str]
) -> None:
    author_token = make_token(sub="author-ref-001", roles=["contributor"])
    reviewer_token = make_token(sub="reviewer-ref-001", roles=["contributor"])

    # Create and confirm a fact
    fact_resp = await client.post(
        "/api/v1/facts",
        json=fact_payload(title="Fact for task reference"),
        headers={"Authorization": f"Bearer {author_token}"},
    )
    fact_id = fact_resp.json()["id"]
    fact_record_id = fact_resp.json()["record_id"]
    await client.post(
        f"/api/v1/facts/{fact_id}/submit",
        headers={"Authorization": f"Bearer {author_token}"},
    )
    await client.post(
        f"/api/v1/facts/{fact_id}/confirm",
        headers={"Authorization": f"Bearer {reviewer_token}"},
    )

    # Create a task and add the fact ref
    task_resp = await client.post(
        "/api/v1/tasks",
        json=task_payload(),
        headers={"Authorization": f"Bearer {author_token}"},
    )
    task_id = task_resp.json()["id"]

    ref_resp = await client.post(
        f"/api/v1/tasks/{task_id}/fact-refs",
        json={"fact_record_id": fact_record_id},
        headers={"Authorization": f"Bearer {author_token}"},
    )
    assert ref_resp.status_code == 201


@pytest.mark.asyncio
async def test_add_draft_fact_ref_returns_422(
    client: AsyncClient, make_token: Callable[..., str]
) -> None:
    """Only confirmed Facts may be referenced by a Task."""
    token = make_token(roles=["contributor"])

    fact_resp = await client.post(
        "/api/v1/facts",
        json=fact_payload(),
        headers={"Authorization": f"Bearer {token}"},
    )
    fact_record_id = fact_resp.json()["record_id"]

    task_resp = await client.post(
        "/api/v1/tasks",
        json=task_payload(),
        headers={"Authorization": f"Bearer {token}"},
    )
    task_id = task_resp.json()["id"]

    ref_resp = await client.post(
        f"/api/v1/tasks/{task_id}/fact-refs",
        json={"fact_record_id": fact_record_id},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert ref_resp.status_code == 422


@pytest.mark.asyncio
async def test_add_fact_ref_to_confirmed_task_returns_422(
    client: AsyncClient, make_token: Callable[..., str]
) -> None:
    author_token = make_token(sub="author-ref-002", roles=["contributor"])
    reviewer_token = make_token(sub="reviewer-ref-002", roles=["contributor"])

    # Create and confirm a fact
    fact_resp = await client.post(
        "/api/v1/facts",
        json=fact_payload(),
        headers={"Authorization": f"Bearer {author_token}"},
    )
    fact_id = fact_resp.json()["id"]
    fact_record_id = fact_resp.json()["record_id"]
    await client.post(
        f"/api/v1/facts/{fact_id}/submit",
        headers={"Authorization": f"Bearer {author_token}"},
    )
    await client.post(
        f"/api/v1/facts/{fact_id}/confirm",
        headers={"Authorization": f"Bearer {reviewer_token}"},
    )

    # Create and confirm a task
    task_resp = await client.post(
        "/api/v1/tasks",
        json=task_payload(),
        headers={"Authorization": f"Bearer {author_token}"},
    )
    task_id = task_resp.json()["id"]
    await client.post(
        f"/api/v1/tasks/{task_id}/submit",
        headers={"Authorization": f"Bearer {author_token}"},
    )
    await client.post(
        f"/api/v1/tasks/{task_id}/confirm",
        headers={"Authorization": f"Bearer {reviewer_token}"},
    )

    ref_resp = await client.post(
        f"/api/v1/tasks/{task_id}/fact-refs",
        json={"fact_record_id": fact_record_id},
        headers={"Authorization": f"Bearer {author_token}"},
    )
    assert ref_resp.status_code == 422


@pytest.mark.asyncio
async def test_add_confirmed_concept_ref_to_task(
    client: AsyncClient, make_token: Callable[..., str]
) -> None:
    author_token = make_token(sub="author-cref-001", roles=["contributor"])
    reviewer_token = make_token(sub="reviewer-cref-001", roles=["contributor"])

    concept_resp = await client.post(
        "/api/v1/concepts",
        json=concept_payload(),
        headers={"Authorization": f"Bearer {author_token}"},
    )
    concept_id = concept_resp.json()["id"]
    concept_record_id = concept_resp.json()["record_id"]
    await client.post(
        f"/api/v1/concepts/{concept_id}/submit",
        headers={"Authorization": f"Bearer {author_token}"},
    )
    await client.post(
        f"/api/v1/concepts/{concept_id}/confirm",
        headers={"Authorization": f"Bearer {reviewer_token}"},
    )

    task_resp = await client.post(
        "/api/v1/tasks",
        json=task_payload(),
        headers={"Authorization": f"Bearer {author_token}"},
    )
    task_id = task_resp.json()["id"]

    ref_resp = await client.post(
        f"/api/v1/tasks/{task_id}/concept-refs",
        json={"concept_record_id": concept_record_id},
        headers={"Authorization": f"Bearer {author_token}"},
    )
    assert ref_resp.status_code == 201


# ---------------------------------------------------------------------------
# Full lifecycle (happy path)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_task_full_lifecycle_draft_to_confirmed(
    client: AsyncClient, make_token: Callable[..., str]
) -> None:
    author_token = make_token(sub="author-task-001", roles=["contributor"])
    reviewer_token = make_token(sub="reviewer-task-001", roles=["contributor"])

    create_resp = await client.post(
        "/api/v1/tasks",
        json=task_payload(),
        headers={"Authorization": f"Bearer {author_token}"},
    )
    assert create_resp.status_code == 201
    task_id = create_resp.json()["id"]

    # Add a step
    await client.post(
        f"/api/v1/tasks/{task_id}/steps",
        json=task_step_payload(),
        headers={"Authorization": f"Bearer {author_token}"},
    )

    submit_resp = await client.post(
        f"/api/v1/tasks/{task_id}/submit",
        headers={"Authorization": f"Bearer {author_token}"},
    )
    assert submit_resp.status_code == 200
    assert submit_resp.json()["status"] == "submitted"

    confirm_resp = await client.post(
        f"/api/v1/tasks/{task_id}/confirm",
        headers={"Authorization": f"Bearer {reviewer_token}"},
    )
    assert confirm_resp.status_code == 200
    assert confirm_resp.json()["status"] == "confirmed"


@pytest.mark.asyncio
async def test_task_self_review_returns_403(
    client: AsyncClient, make_token: Callable[..., str]
) -> None:
    token = make_token(sub="self-task-001", roles=["contributor"])

    create_resp = await client.post(
        "/api/v1/tasks",
        json=task_payload(),
        headers={"Authorization": f"Bearer {token}"},
    )
    task_id = create_resp.json()["id"]
    await client.post(
        f"/api/v1/tasks/{task_id}/submit",
        headers={"Authorization": f"Bearer {token}"},
    )

    confirm_resp = await client.post(
        f"/api/v1/tasks/{task_id}/confirm",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert confirm_resp.status_code == 403


@pytest.mark.asyncio
async def test_patch_confirmed_task_returns_422(
    client: AsyncClient, make_token: Callable[..., str]
) -> None:
    author_token = make_token(sub="author-task-immut-001", roles=["contributor"])
    reviewer_token = make_token(sub="reviewer-task-immut-001", roles=["contributor"])

    create_resp = await client.post(
        "/api/v1/tasks",
        json=task_payload(),
        headers={"Authorization": f"Bearer {author_token}"},
    )
    task_id = create_resp.json()["id"]
    await client.post(
        f"/api/v1/tasks/{task_id}/submit",
        headers={"Authorization": f"Bearer {author_token}"},
    )
    await client.post(
        f"/api/v1/tasks/{task_id}/confirm",
        headers={"Authorization": f"Bearer {reviewer_token}"},
    )

    patch_resp = await client.patch(
        f"/api/v1/tasks/{task_id}",
        json={"title": "Attempted mutation"},
        headers={"Authorization": f"Bearer {author_token}"},
    )
    assert patch_resp.status_code == 422


# ---------------------------------------------------------------------------
# Return, deprecate, retire
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_return_task_transitions_to_returned(
    client: AsyncClient, make_token: Callable[..., str]
) -> None:
    author_token = make_token(sub="author-task-ret-001", roles=["contributor"])
    reviewer_token = make_token(sub="reviewer-task-ret-001", roles=["contributor"])

    create_resp = await client.post(
        "/api/v1/tasks",
        json=task_payload(),
        headers={"Authorization": f"Bearer {author_token}"},
    )
    task_id = create_resp.json()["id"]
    await client.post(
        f"/api/v1/tasks/{task_id}/submit",
        headers={"Authorization": f"Bearer {author_token}"},
    )

    return_resp = await client.post(
        f"/api/v1/tasks/{task_id}/return",
        json={"note": "Steps are missing completion criteria."},
        headers={"Authorization": f"Bearer {reviewer_token}"},
    )
    assert return_resp.status_code == 200
    assert return_resp.json()["status"] == "returned"


@pytest.mark.asyncio
async def test_deprecate_task_admin_only(
    client: AsyncClient, make_token: Callable[..., str]
) -> None:
    admin_token = make_token(sub="admin-task-dep-001", roles=["admin"])

    create_resp = await client.post(
        "/api/v1/tasks",
        json=task_payload(),
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    task_id = create_resp.json()["id"]
    await client.post(
        f"/api/v1/tasks/{task_id}/submit",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    await client.post(
        f"/api/v1/tasks/{task_id}/confirm",
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    deprecate_resp = await client.post(
        f"/api/v1/tasks/{task_id}/deprecate",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert deprecate_resp.status_code == 200
    assert deprecate_resp.json()["status"] == "deprecated"
