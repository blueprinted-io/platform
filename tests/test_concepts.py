"""Tests for the Concepts lifecycle API.

Spec refs:
  §9.3  Lifecycle state machine
  §9.5  Concepts schema (title, summary, explanation, analogies, tags, embedding)
  §10.1 Immutability once confirmed
  §5.1  Human roles and self-review prohibition

Concepts share the same lifecycle state machine and access-control rules as Facts.
Tests here focus on Concept-specific fields and a condensed lifecycle path.
The full edge-case coverage for the shared lifecycle rules lives in test_facts.py.

All tests are skipped pending Sprint 4 implementation.
"""

from collections.abc import Callable

import pytest
from httpx import AsyncClient

from tests.factories import concept_payload

pytestmark = pytest.mark.asyncio


# ---------------------------------------------------------------------------
# Create draft  (POST /api/v1/concepts)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_create_concept_unauthenticated_returns_401(client: AsyncClient) -> None:
    response = await client.post("/api/v1/concepts", json=concept_payload())
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_create_concept_viewer_returns_403(
    client: AsyncClient, make_token: Callable[..., str]
) -> None:
    token = make_token(roles=["viewer"])
    response = await client.post(
        "/api/v1/concepts",
        json=concept_payload(),
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_create_concept_contributor_returns_201_draft(
    client: AsyncClient, make_token: Callable[..., str]
) -> None:
    token = make_token(roles=["contributor"])
    response = await client.post(
        "/api/v1/concepts",
        json=concept_payload(),
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "draft"
    assert body["version"] == 1
    assert "id" in body
    assert "record_id" in body


@pytest.mark.asyncio
async def test_create_concept_missing_summary_returns_422(
    client: AsyncClient, make_token: Callable[..., str]
) -> None:
    token = make_token(roles=["contributor"])
    response = await client.post(
        "/api/v1/concepts",
        json={
            "title": "Idempotency",
            "explanation": "Repeated application has no additional effect.",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_create_concept_missing_explanation_returns_422(
    client: AsyncClient, make_token: Callable[..., str]
) -> None:
    token = make_token(roles=["contributor"])
    response = await client.post(
        "/api/v1/concepts",
        json={"title": "Idempotency", "summary": "Same result every time."},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_create_concept_with_analogies(
    client: AsyncClient, make_token: Callable[..., str]
) -> None:
    token = make_token(roles=["contributor"])
    analogies = "Like pressing a lift button repeatedly — the lift still comes once."
    response = await client.post(
        "/api/v1/concepts",
        json=concept_payload(analogies=analogies),
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 201
    assert response.json()["analogies"] == analogies


@pytest.mark.asyncio
async def test_create_concept_response_has_required_fields(
    client: AsyncClient, make_token: Callable[..., str]
) -> None:
    token = make_token(roles=["contributor"])
    response = await client.post(
        "/api/v1/concepts",
        json=concept_payload(),
        headers={"Authorization": f"Bearer {token}"},
    )
    body = response.json()
    required = (
        "id", "record_id", "version", "status",
        "title", "summary", "explanation", "analogies", "tags",
        "created_at", "updated_at", "created_by",
    )
    for field in required:
        assert field in body, f"Missing field: {field}"


# ---------------------------------------------------------------------------
# Read  (GET /api/v1/concepts/{id})
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_concept_not_found_returns_404(
    client: AsyncClient, make_token: Callable[..., str]
) -> None:
    token = make_token(roles=["viewer"])
    response = await client.get(
        "/api/v1/concepts/00000000-0000-0000-0000-000000000000",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_get_concept_returns_correct_record(
    client: AsyncClient, make_token: Callable[..., str]
) -> None:
    token = make_token(roles=["contributor"])
    create_resp = await client.post(
        "/api/v1/concepts",
        json=concept_payload(title="Unique concept for get test"),
        headers={"Authorization": f"Bearer {token}"},
    )
    concept_id = create_resp.json()["id"]

    get_resp = await client.get(
        f"/api/v1/concepts/{concept_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert get_resp.status_code == 200
    assert get_resp.json()["id"] == concept_id


# ---------------------------------------------------------------------------
# Full lifecycle (happy path)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_concept_full_lifecycle_draft_to_confirmed(
    client: AsyncClient, make_token: Callable[..., str]
) -> None:
    author_token = make_token(sub="author-cpt-001", roles=["contributor"])
    reviewer_token = make_token(sub="reviewer-cpt-001", roles=["contributor"])

    # Create draft
    create_resp = await client.post(
        "/api/v1/concepts",
        json=concept_payload(),
        headers={"Authorization": f"Bearer {author_token}"},
    )
    assert create_resp.status_code == 201
    concept_id = create_resp.json()["id"]

    # Submit
    submit_resp = await client.post(
        f"/api/v1/concepts/{concept_id}/submit",
        headers={"Authorization": f"Bearer {author_token}"},
    )
    assert submit_resp.status_code == 200
    assert submit_resp.json()["status"] == "submitted"

    # Confirm (different user)
    confirm_resp = await client.post(
        f"/api/v1/concepts/{concept_id}/confirm",
        headers={"Authorization": f"Bearer {reviewer_token}"},
    )
    assert confirm_resp.status_code == 200
    assert confirm_resp.json()["status"] == "confirmed"


@pytest.mark.asyncio
async def test_concept_self_review_returns_403(
    client: AsyncClient, make_token: Callable[..., str]
) -> None:
    token = make_token(sub="self-cpt-001", roles=["contributor"])

    create_resp = await client.post(
        "/api/v1/concepts",
        json=concept_payload(),
        headers={"Authorization": f"Bearer {token}"},
    )
    concept_id = create_resp.json()["id"]
    await client.post(
        f"/api/v1/concepts/{concept_id}/submit",
        headers={"Authorization": f"Bearer {token}"},
    )

    confirm_resp = await client.post(
        f"/api/v1/concepts/{concept_id}/confirm",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert confirm_resp.status_code == 403


@pytest.mark.asyncio
async def test_patch_confirmed_concept_returns_422(
    client: AsyncClient, make_token: Callable[..., str]
) -> None:
    author_token = make_token(sub="author-cpt-immut-001", roles=["contributor"])
    reviewer_token = make_token(sub="reviewer-cpt-immut-001", roles=["contributor"])

    create_resp = await client.post(
        "/api/v1/concepts",
        json=concept_payload(),
        headers={"Authorization": f"Bearer {author_token}"},
    )
    concept_id = create_resp.json()["id"]
    await client.post(
        f"/api/v1/concepts/{concept_id}/submit",
        headers={"Authorization": f"Bearer {author_token}"},
    )
    await client.post(
        f"/api/v1/concepts/{concept_id}/confirm",
        headers={"Authorization": f"Bearer {reviewer_token}"},
    )

    patch_resp = await client.patch(
        f"/api/v1/concepts/{concept_id}",
        json={"summary": "Attempted mutation"},
        headers={"Authorization": f"Bearer {author_token}"},
    )
    assert patch_resp.status_code == 422


# ---------------------------------------------------------------------------
# Return, deprecate, retire
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_return_concept_transitions_to_returned(
    client: AsyncClient, make_token: Callable[..., str]
) -> None:
    author_token = make_token(sub="author-cpt-ret-001", roles=["contributor"])
    reviewer_token = make_token(sub="reviewer-cpt-ret-001", roles=["contributor"])

    create_resp = await client.post(
        "/api/v1/concepts",
        json=concept_payload(),
        headers={"Authorization": f"Bearer {author_token}"},
    )
    concept_id = create_resp.json()["id"]
    await client.post(
        f"/api/v1/concepts/{concept_id}/submit",
        headers={"Authorization": f"Bearer {author_token}"},
    )

    return_resp = await client.post(
        f"/api/v1/concepts/{concept_id}/return",
        json={"note": "The explanation is unclear."},
        headers={"Authorization": f"Bearer {reviewer_token}"},
    )
    assert return_resp.status_code == 200
    assert return_resp.json()["status"] == "returned"


@pytest.mark.asyncio
async def test_deprecate_concept_admin_only(
    client: AsyncClient, make_token: Callable[..., str]
) -> None:
    admin_token = make_token(sub="admin-cpt-dep-001", roles=["admin"])

    create_resp = await client.post(
        "/api/v1/concepts",
        json=concept_payload(),
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    concept_id = create_resp.json()["id"]
    await client.post(
        f"/api/v1/concepts/{concept_id}/submit",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    await client.post(
        f"/api/v1/concepts/{concept_id}/confirm",
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    deprecate_resp = await client.post(
        f"/api/v1/concepts/{concept_id}/deprecate",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert deprecate_resp.status_code == 200
    assert deprecate_resp.json()["status"] == "deprecated"


@pytest.mark.asyncio
async def test_deprecate_concept_non_admin_returns_403(
    client: AsyncClient, make_token: Callable[..., str]
) -> None:
    contributor_token = make_token(sub="contrib-cpt-dep-001", roles=["contributor"])
    admin_token = make_token(sub="admin-cpt-dep-002", roles=["admin"])

    create_resp = await client.post(
        "/api/v1/concepts",
        json=concept_payload(),
        headers={"Authorization": f"Bearer {contributor_token}"},
    )
    concept_id = create_resp.json()["id"]
    await client.post(
        f"/api/v1/concepts/{concept_id}/submit",
        headers={"Authorization": f"Bearer {contributor_token}"},
    )
    await client.post(
        f"/api/v1/concepts/{concept_id}/confirm",
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    deprecate_resp = await client.post(
        f"/api/v1/concepts/{concept_id}/deprecate",
        headers={"Authorization": f"Bearer {contributor_token}"},
    )
    assert deprecate_resp.status_code == 403
