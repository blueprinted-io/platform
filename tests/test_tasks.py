"""Tests for the Tasks lifecycle API.

TEST_REVISED (v4.4/v4.5 — dissolve Facts/Concepts, drop procedure_name):
  - Removed fact-ref and concept-ref tests: /fact-refs and /concept-refs endpoints
    no longer exist. Facts and concepts are string arrays on the Task record.
  - Removed test_create_task_missing_procedure_name_returns_422: procedure_name
    is no longer a field on Task.
  - Updated test_create_task_response_has_required_fields: removed procedure_name,
    has_deprecated_fact_ref, has_deprecated_concept_ref, fact_refs, concept_refs;
    added facts, concepts.
  - Updated test_create_task_missing_outcome_returns_422: removed procedure_name
    from the invalid payload (no longer a field).
  - Imports: removed concept_payload and fact_payload (factories deleted).

Spec refs:
  §9.3  Lifecycle state machine
  §9.5  Tasks schema (title, outcome, domain, facts, concepts, steps)
  §10.1 No machine can confirm
  §7    Domain scoping (Tasks are domain-scoped)
  §5.1  Human roles and self-review prohibition

Task-specific behaviour:
  - Steps (task_steps + task_step_actions) are owned by the Task
  - task.irreversible is derived: True if any step has irreversible=True
  - Steps cannot be added to or removed from a confirmed Task
  - facts and concepts are string arrays, authored as part of the task
"""

from collections.abc import Callable

import pytest
from httpx import AsyncClient

from tests.factories import (
    task_payload,
    task_step_action_payload,
    task_step_payload,
)

pytestmark = pytest.mark.asyncio


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
        json={"title": "A task"},
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
        "title", "outcome", "domain",
        "facts", "concepts",
        "irreversible", "steps",
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


@pytest.mark.asyncio
async def test_create_task_with_facts_and_concepts(
    client: AsyncClient, make_token: Callable[..., str]
) -> None:
    token = make_token(roles=["contributor"])
    response = await client.post(
        "/api/v1/tasks",
        json=task_payload(
            facts=["PostgreSQL superuser has full database access"],
            concepts=["Password rotation limits blast radius of credential compromise"],
        ),
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 201
    body = response.json()
    assert body["facts"] == ["PostgreSQL superuser has full database access"]
    assert body["concepts"] == ["Password rotation limits blast radius of credential compromise"]


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
    # TEST_REVISED: admin self-confirm requires non-empty justification (§5.1 break-glass)
    await client.post(
        f"/api/v1/tasks/{task_id}/confirm",
        json={"justification": "Admin break-glass confirm for test."},
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    deprecate_resp = await client.post(
        f"/api/v1/tasks/{task_id}/deprecate",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert deprecate_resp.status_code == 200
    assert deprecate_resp.json()["status"] == "deprecated"


# ---------------------------------------------------------------------------
# Step quality linting (§9.10)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_lint_warnings_absent_on_clean_step(
    client: AsyncClient, make_token: Callable[..., str]
) -> None:
    token = make_token(sub="test-sub-001", roles=["contributor"])
    headers = {"Authorization": f"Bearer {token}"}

    create_resp = await client.post("/api/v1/tasks", json=task_payload(), headers=headers)
    task_id = create_resp.json()["id"]

    step_resp = await client.post(
        f"/api/v1/tasks/{task_id}/steps",
        json={
            "step": "Connect to the database as the current superuser",
            "completion": "You are connected and can run queries.",
            "actions": [{"instruction": "Run: psql -U postgres"}],
        },
        headers=headers,
    )
    assert step_resp.status_code == 201

    get_resp = await client.get(f"/api/v1/tasks/{task_id}", headers=headers)
    assert get_resp.json()["lint_warnings"] == []


@pytest.mark.asyncio
async def test_lint_warns_abstract_verb(
    client: AsyncClient, make_token: Callable[..., str]
) -> None:
    token = make_token(sub="test-sub-001", roles=["contributor"])
    headers = {"Authorization": f"Bearer {token}"}

    create_resp = await client.post("/api/v1/tasks", json=task_payload(), headers=headers)
    task_id = create_resp.json()["id"]

    await client.post(
        f"/api/v1/tasks/{task_id}/steps",
        json={
            "step": "Ensure the backup exists before proceeding",
            "completion": "Backup confirmed present.",
            "actions": [{"instruction": "Check backup directory"}],
        },
        headers=headers,
    )

    get_resp = await client.get(f"/api/v1/tasks/{task_id}", headers=headers)
    warnings = get_resp.json()["lint_warnings"]
    assert any(w["rule"] == "abstract_verb" for w in warnings)


@pytest.mark.asyncio
async def test_lint_warns_missing_completion(
    client: AsyncClient, make_token: Callable[..., str]
) -> None:
    token = make_token(sub="test-sub-001", roles=["contributor"])
    headers = {"Authorization": f"Bearer {token}"}

    create_resp = await client.post("/api/v1/tasks", json=task_payload(), headers=headers)
    task_id = create_resp.json()["id"]

    await client.post(
        f"/api/v1/tasks/{task_id}/steps",
        json={
            "step": "Back up the database",
            "completion": "",
            "actions": [{"instruction": "Run: pg_dump"}],
        },
        headers=headers,
    )

    get_resp = await client.get(f"/api/v1/tasks/{task_id}", headers=headers)
    warnings = get_resp.json()["lint_warnings"]
    assert any(w["rule"] == "missing_completion" for w in warnings)


@pytest.mark.asyncio
async def test_lint_warns_empty_actions(
    client: AsyncClient, make_token: Callable[..., str]
) -> None:
    token = make_token(sub="test-sub-001", roles=["contributor"])
    headers = {"Authorization": f"Bearer {token}"}

    create_resp = await client.post("/api/v1/tasks", json=task_payload(), headers=headers)
    task_id = create_resp.json()["id"]

    await client.post(
        f"/api/v1/tasks/{task_id}/steps",
        json={
            "step": "Back up the database",
            "completion": "Backup file is present in /tmp.",
            "actions": [],
        },
        headers=headers,
    )

    get_resp = await client.get(f"/api/v1/tasks/{task_id}", headers=headers)
    warnings = get_resp.json()["lint_warnings"]
    assert any(w["rule"] == "empty_actions" for w in warnings)


@pytest.mark.asyncio
async def test_lint_warnings_suppressed_on_confirmed_task(
    client: AsyncClient, make_token: Callable[..., str]
) -> None:
    """Confirmed records do not surface lint warnings (§9.10)."""
    author_token = make_token(sub="author-task-001", roles=["contributor"])
    reviewer_token = make_token(sub="reviewer-task-001", roles=["contributor"])

    create_resp = await client.post(
        "/api/v1/tasks", json=task_payload(),
        headers={"Authorization": f"Bearer {author_token}"},
    )
    task_id = create_resp.json()["id"]

    # Add a step with no actions (would normally produce a warning)
    await client.post(
        f"/api/v1/tasks/{task_id}/steps",
        json={"step": "Back up", "completion": "Done.", "actions": []},
        headers={"Authorization": f"Bearer {author_token}"},
    )
    await client.post(f"/api/v1/tasks/{task_id}/submit", headers={"Authorization": f"Bearer {author_token}"})
    await client.post(f"/api/v1/tasks/{task_id}/confirm", headers={"Authorization": f"Bearer {reviewer_token}"})

    get_resp = await client.get(f"/api/v1/tasks/{task_id}", headers={"Authorization": f"Bearer {reviewer_token}"})
    assert get_resp.json()["lint_warnings"] == []
