"""Tests for the Workflows lifecycle API.

Spec refs:
  §9.3  Lifecycle state machine
  §9.5  Workflows schema (title, objective, domain, tags, task-refs, principle-refs)
  §10.1 Immutability once confirmed
  §7    Domain scoping (Workflows are domain-scoped)
  §5.1  Human roles and self-review prohibition

Workflow-specific behaviour:
  - Workflows reference Tasks by record_id (resolves to latest confirmed version)
  - Workflows attach Principles by record_id (reusable across multiple Workflows)
  - Only confirmed Tasks may be added to a Workflow task-refs list
  - Only confirmed Principles may be attached to a Workflow
  - workflow.has_incoming_task_change: server-managed, set when a referenced Task
    gets a new confirmed version. Not settable directly.
  - workflow.has_pending_task_confirm: server-managed, set when any referenced Task
    has a submitted-but-not-yet-confirmed revision. Not settable directly.
  - Workflow composition is always a human act — the ingestion pipeline never
    produces Workflow candidates (CLAUDE.md ingestion rule)

Assumptions (flag as TEST_REVISED if Sprint 4 diverges):
  - Task refs: POST /api/v1/workflows/{id}/task-refs
  - Task ref remove: DELETE /api/v1/workflows/{workflow_id}/task-refs/{task_record_id}
  - Principle attach: POST /api/v1/workflows/{id}/principle-refs
  - Principle detach: DELETE /api/v1/workflows/{workflow_id}/principle-refs/{principle_record_id}
  - Only confirmed Tasks and Principles may be referenced

All tests are skipped pending Sprint 4 implementation.
"""

from collections.abc import Callable

import pytest
from httpx import AsyncClient

from tests.factories import principle_payload, task_payload, workflow_payload

pytestmark = pytest.mark.skip(reason="Sprint 4: Workflows API not yet implemented")


# ---------------------------------------------------------------------------
# Create draft  (POST /api/v1/workflows)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_create_workflow_unauthenticated_returns_401(client: AsyncClient) -> None:
    response = await client.post("/api/v1/workflows", json=workflow_payload())
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_create_workflow_viewer_returns_403(
    client: AsyncClient, make_token: Callable[..., str]
) -> None:
    token = make_token(roles=["viewer"])
    response = await client.post(
        "/api/v1/workflows",
        json=workflow_payload(),
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_create_workflow_contributor_returns_201_draft(
    client: AsyncClient, make_token: Callable[..., str]
) -> None:
    token = make_token(roles=["contributor"])
    response = await client.post(
        "/api/v1/workflows",
        json=workflow_payload(),
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "draft"
    assert body["version"] == 1
    assert "id" in body
    assert "record_id" in body


@pytest.mark.asyncio
async def test_create_workflow_missing_objective_returns_422(
    client: AsyncClient, make_token: Callable[..., str]
) -> None:
    token = make_token(roles=["contributor"])
    response = await client.post(
        "/api/v1/workflows",
        json={"title": "A workflow"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_create_workflow_response_has_required_fields(
    client: AsyncClient, make_token: Callable[..., str]
) -> None:
    token = make_token(roles=["contributor"])
    response = await client.post(
        "/api/v1/workflows",
        json=workflow_payload(),
        headers={"Authorization": f"Bearer {token}"},
    )
    body = response.json()
    required = (
        "id", "record_id", "version", "status",
        "title", "objective", "domain", "tags",
        "task_refs", "principle_refs",
        "has_incoming_task_change", "has_pending_task_confirm",
        "created_at", "updated_at", "created_by",
    )
    for field in required:
        assert field in body, f"Missing field: {field}"


# ---------------------------------------------------------------------------
# Task references  (POST /api/v1/workflows/{id}/task-refs)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_add_confirmed_task_ref_to_workflow(
    client: AsyncClient, make_token: Callable[..., str]
) -> None:
    author_token = make_token(sub="author-wf-tref-001", roles=["contributor"])
    reviewer_token = make_token(sub="reviewer-wf-tref-001", roles=["contributor"])

    # Create and confirm a task
    task_resp = await client.post(
        "/api/v1/tasks",
        json=task_payload(),
        headers={"Authorization": f"Bearer {author_token}"},
    )
    task_id = task_resp.json()["id"]
    task_record_id = task_resp.json()["record_id"]
    await client.post(
        f"/api/v1/tasks/{task_id}/submit",
        headers={"Authorization": f"Bearer {author_token}"},
    )
    await client.post(
        f"/api/v1/tasks/{task_id}/confirm",
        headers={"Authorization": f"Bearer {reviewer_token}"},
    )

    # Create a workflow and add the task ref
    wf_resp = await client.post(
        "/api/v1/workflows",
        json=workflow_payload(),
        headers={"Authorization": f"Bearer {author_token}"},
    )
    wf_id = wf_resp.json()["id"]

    ref_resp = await client.post(
        f"/api/v1/workflows/{wf_id}/task-refs",
        json={"task_record_id": task_record_id},
        headers={"Authorization": f"Bearer {author_token}"},
    )
    assert ref_resp.status_code == 201


@pytest.mark.asyncio
async def test_add_unconfirmed_task_ref_returns_422(
    client: AsyncClient, make_token: Callable[..., str]
) -> None:
    """Only confirmed Tasks may be referenced in a Workflow."""
    token = make_token(roles=["contributor"])

    task_resp = await client.post(
        "/api/v1/tasks",
        json=task_payload(),
        headers={"Authorization": f"Bearer {token}"},
    )
    task_record_id = task_resp.json()["record_id"]

    wf_resp = await client.post(
        "/api/v1/workflows",
        json=workflow_payload(),
        headers={"Authorization": f"Bearer {token}"},
    )
    wf_id = wf_resp.json()["id"]

    ref_resp = await client.post(
        f"/api/v1/workflows/{wf_id}/task-refs",
        json={"task_record_id": task_record_id},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert ref_resp.status_code == 422


@pytest.mark.asyncio
async def test_add_task_ref_to_confirmed_workflow_returns_422(
    client: AsyncClient, make_token: Callable[..., str]
) -> None:
    author_token = make_token(sub="author-wf-immut-001", roles=["contributor"])
    reviewer_token = make_token(sub="reviewer-wf-immut-001", roles=["contributor"])

    # Create and confirm a task
    task_resp = await client.post(
        "/api/v1/tasks",
        json=task_payload(),
        headers={"Authorization": f"Bearer {author_token}"},
    )
    task_id = task_resp.json()["id"]
    task_record_id = task_resp.json()["record_id"]
    await client.post(
        f"/api/v1/tasks/{task_id}/submit",
        headers={"Authorization": f"Bearer {author_token}"},
    )
    await client.post(
        f"/api/v1/tasks/{task_id}/confirm",
        headers={"Authorization": f"Bearer {reviewer_token}"},
    )

    # Create and confirm the workflow
    wf_resp = await client.post(
        "/api/v1/workflows",
        json=workflow_payload(),
        headers={"Authorization": f"Bearer {author_token}"},
    )
    wf_id = wf_resp.json()["id"]
    await client.post(
        f"/api/v1/workflows/{wf_id}/submit",
        headers={"Authorization": f"Bearer {author_token}"},
    )
    await client.post(
        f"/api/v1/workflows/{wf_id}/confirm",
        headers={"Authorization": f"Bearer {reviewer_token}"},
    )

    ref_resp = await client.post(
        f"/api/v1/workflows/{wf_id}/task-refs",
        json={"task_record_id": task_record_id},
        headers={"Authorization": f"Bearer {author_token}"},
    )
    assert ref_resp.status_code == 422


# ---------------------------------------------------------------------------
# Principle references  (POST /api/v1/workflows/{id}/principle-refs)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_attach_confirmed_principle_to_workflow(
    client: AsyncClient, make_token: Callable[..., str]
) -> None:
    author_token = make_token(sub="author-wf-pref-001", roles=["contributor"])
    reviewer_token = make_token(sub="reviewer-wf-pref-001", roles=["contributor"])

    principle_resp = await client.post(
        "/api/v1/principles",
        json=principle_payload(),
        headers={"Authorization": f"Bearer {author_token}"},
    )
    principle_id = principle_resp.json()["id"]
    principle_record_id = principle_resp.json()["record_id"]
    await client.post(
        f"/api/v1/principles/{principle_id}/submit",
        headers={"Authorization": f"Bearer {author_token}"},
    )
    await client.post(
        f"/api/v1/principles/{principle_id}/confirm",
        headers={"Authorization": f"Bearer {reviewer_token}"},
    )

    wf_resp = await client.post(
        "/api/v1/workflows",
        json=workflow_payload(),
        headers={"Authorization": f"Bearer {author_token}"},
    )
    wf_id = wf_resp.json()["id"]

    ref_resp = await client.post(
        f"/api/v1/workflows/{wf_id}/principle-refs",
        json={"principle_record_id": principle_record_id},
        headers={"Authorization": f"Bearer {author_token}"},
    )
    assert ref_resp.status_code == 201


@pytest.mark.asyncio
async def test_attach_unconfirmed_principle_returns_422(
    client: AsyncClient, make_token: Callable[..., str]
) -> None:
    token = make_token(roles=["contributor"])

    principle_resp = await client.post(
        "/api/v1/principles",
        json=principle_payload(),
        headers={"Authorization": f"Bearer {token}"},
    )
    principle_record_id = principle_resp.json()["record_id"]

    wf_resp = await client.post(
        "/api/v1/workflows",
        json=workflow_payload(),
        headers={"Authorization": f"Bearer {token}"},
    )
    wf_id = wf_resp.json()["id"]

    ref_resp = await client.post(
        f"/api/v1/workflows/{wf_id}/principle-refs",
        json={"principle_record_id": principle_record_id},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert ref_resp.status_code == 422


# ---------------------------------------------------------------------------
# Full lifecycle (happy path)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_workflow_full_lifecycle_draft_to_confirmed(
    client: AsyncClient, make_token: Callable[..., str]
) -> None:
    author_token = make_token(sub="author-wf-001", roles=["contributor"])
    reviewer_token = make_token(sub="reviewer-wf-001", roles=["contributor"])

    create_resp = await client.post(
        "/api/v1/workflows",
        json=workflow_payload(),
        headers={"Authorization": f"Bearer {author_token}"},
    )
    assert create_resp.status_code == 201
    wf_id = create_resp.json()["id"]

    submit_resp = await client.post(
        f"/api/v1/workflows/{wf_id}/submit",
        headers={"Authorization": f"Bearer {author_token}"},
    )
    assert submit_resp.status_code == 200
    assert submit_resp.json()["status"] == "submitted"

    confirm_resp = await client.post(
        f"/api/v1/workflows/{wf_id}/confirm",
        headers={"Authorization": f"Bearer {reviewer_token}"},
    )
    assert confirm_resp.status_code == 200
    assert confirm_resp.json()["status"] == "confirmed"


@pytest.mark.asyncio
async def test_workflow_self_review_returns_403(
    client: AsyncClient, make_token: Callable[..., str]
) -> None:
    token = make_token(sub="self-wf-001", roles=["contributor"])

    create_resp = await client.post(
        "/api/v1/workflows",
        json=workflow_payload(),
        headers={"Authorization": f"Bearer {token}"},
    )
    wf_id = create_resp.json()["id"]
    await client.post(
        f"/api/v1/workflows/{wf_id}/submit",
        headers={"Authorization": f"Bearer {token}"},
    )

    confirm_resp = await client.post(
        f"/api/v1/workflows/{wf_id}/confirm",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert confirm_resp.status_code == 403


@pytest.mark.asyncio
async def test_patch_confirmed_workflow_returns_422(
    client: AsyncClient, make_token: Callable[..., str]
) -> None:
    author_token = make_token(sub="author-wf-immut-002", roles=["contributor"])
    reviewer_token = make_token(sub="reviewer-wf-immut-002", roles=["contributor"])

    create_resp = await client.post(
        "/api/v1/workflows",
        json=workflow_payload(),
        headers={"Authorization": f"Bearer {author_token}"},
    )
    wf_id = create_resp.json()["id"]
    await client.post(
        f"/api/v1/workflows/{wf_id}/submit",
        headers={"Authorization": f"Bearer {author_token}"},
    )
    await client.post(
        f"/api/v1/workflows/{wf_id}/confirm",
        headers={"Authorization": f"Bearer {reviewer_token}"},
    )

    patch_resp = await client.patch(
        f"/api/v1/workflows/{wf_id}",
        json={"title": "Attempted mutation"},
        headers={"Authorization": f"Bearer {author_token}"},
    )
    assert patch_resp.status_code == 422


# ---------------------------------------------------------------------------
# Return, deprecate
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_return_workflow_transitions_to_returned(
    client: AsyncClient, make_token: Callable[..., str]
) -> None:
    author_token = make_token(sub="author-wf-ret-001", roles=["contributor"])
    reviewer_token = make_token(sub="reviewer-wf-ret-001", roles=["contributor"])

    create_resp = await client.post(
        "/api/v1/workflows",
        json=workflow_payload(),
        headers={"Authorization": f"Bearer {author_token}"},
    )
    wf_id = create_resp.json()["id"]
    await client.post(
        f"/api/v1/workflows/{wf_id}/submit",
        headers={"Authorization": f"Bearer {author_token}"},
    )

    return_resp = await client.post(
        f"/api/v1/workflows/{wf_id}/return",
        json={"note": "Objective is too vague."},
        headers={"Authorization": f"Bearer {reviewer_token}"},
    )
    assert return_resp.status_code == 200
    assert return_resp.json()["status"] == "returned"


@pytest.mark.asyncio
async def test_deprecate_workflow_admin_only(
    client: AsyncClient, make_token: Callable[..., str]
) -> None:
    admin_token = make_token(sub="admin-wf-dep-001", roles=["admin"])

    create_resp = await client.post(
        "/api/v1/workflows",
        json=workflow_payload(),
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    wf_id = create_resp.json()["id"]
    await client.post(
        f"/api/v1/workflows/{wf_id}/submit",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    await client.post(
        f"/api/v1/workflows/{wf_id}/confirm",
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    deprecate_resp = await client.post(
        f"/api/v1/workflows/{wf_id}/deprecate",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert deprecate_resp.status_code == 200
    assert deprecate_resp.json()["status"] == "deprecated"
