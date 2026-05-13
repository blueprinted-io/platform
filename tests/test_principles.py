"""Tests for the Principles lifecycle API.

Spec refs:
  §9.3  Lifecycle state machine
  §9.5  Principles schema (title, summary, explanation, analogies, domain, tags, ingestion_id)
  §10.1 Immutability once confirmed
  §7    Domain scoping (Principles are domain-scoped, unlike Facts and Concepts)
  §5.1  Human roles and self-review prohibition

Key difference from Facts/Concepts: Principles are domain-scoped. A Contributor can only
create/submit/confirm Principles in their assigned domains. Admin has all domains implicitly.

All tests are skipped pending Sprint 4 implementation.
"""

from collections.abc import Callable

import pytest
from httpx import AsyncClient

from tests.factories import principle_payload

pytestmark = pytest.mark.asyncio


# ---------------------------------------------------------------------------
# Create draft  (POST /api/v1/principles)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_create_principle_unauthenticated_returns_401(client: AsyncClient) -> None:
    response = await client.post("/api/v1/principles", json=principle_payload())
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_create_principle_viewer_returns_403(
    client: AsyncClient, make_token: Callable[..., str]
) -> None:
    token = make_token(roles=["viewer"])
    response = await client.post(
        "/api/v1/principles",
        json=principle_payload(),
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_create_principle_contributor_returns_201_draft(
    client: AsyncClient, make_token: Callable[..., str]
) -> None:
    token = make_token(roles=["contributor"])
    response = await client.post(
        "/api/v1/principles",
        json=principle_payload(),
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "draft"
    assert body["version"] == 1
    assert "id" in body
    assert "record_id" in body


@pytest.mark.asyncio
async def test_create_principle_missing_summary_returns_422(
    client: AsyncClient, make_token: Callable[..., str]
) -> None:
    token = make_token(roles=["contributor"])
    response = await client.post(
        "/api/v1/principles",
        json={"title": "A principle", "explanation": "Detailed explanation."},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_create_principle_with_domain(
    client: AsyncClient, make_token: Callable[..., str]
) -> None:
    token = make_token(roles=["contributor"])
    response = await client.post(
        "/api/v1/principles",
        json=principle_payload(domain="DevOps"),
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 201
    assert response.json()["domain"] == "DevOps"


@pytest.mark.asyncio
async def test_create_principle_response_has_required_fields(
    client: AsyncClient, make_token: Callable[..., str]
) -> None:
    token = make_token(roles=["contributor"])
    response = await client.post(
        "/api/v1/principles",
        json=principle_payload(),
        headers={"Authorization": f"Bearer {token}"},
    )
    body = response.json()
    required = (
        "id", "record_id", "version", "status",
        "title", "summary", "explanation", "analogies", "domain", "tags",
        "created_at", "updated_at", "created_by",
    )
    for field in required:
        assert field in body, f"Missing field: {field}"


# ---------------------------------------------------------------------------
# Full lifecycle (happy path)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_principle_full_lifecycle_draft_to_confirmed(
    client: AsyncClient, make_token: Callable[..., str]
) -> None:
    author_token = make_token(sub="author-prn-001", roles=["contributor"])
    reviewer_token = make_token(sub="reviewer-prn-001", roles=["contributor"])

    create_resp = await client.post(
        "/api/v1/principles",
        json=principle_payload(),
        headers={"Authorization": f"Bearer {author_token}"},
    )
    assert create_resp.status_code == 201
    principle_id = create_resp.json()["id"]

    submit_resp = await client.post(
        f"/api/v1/principles/{principle_id}/submit",
        headers={"Authorization": f"Bearer {author_token}"},
    )
    assert submit_resp.status_code == 200
    assert submit_resp.json()["status"] == "submitted"

    confirm_resp = await client.post(
        f"/api/v1/principles/{principle_id}/confirm",
        headers={"Authorization": f"Bearer {reviewer_token}"},
    )
    assert confirm_resp.status_code == 200
    assert confirm_resp.json()["status"] == "confirmed"


@pytest.mark.asyncio
async def test_principle_self_review_returns_403(
    client: AsyncClient, make_token: Callable[..., str]
) -> None:
    token = make_token(sub="self-prn-001", roles=["contributor"])

    create_resp = await client.post(
        "/api/v1/principles",
        json=principle_payload(),
        headers={"Authorization": f"Bearer {token}"},
    )
    principle_id = create_resp.json()["id"]
    await client.post(
        f"/api/v1/principles/{principle_id}/submit",
        headers={"Authorization": f"Bearer {token}"},
    )

    confirm_resp = await client.post(
        f"/api/v1/principles/{principle_id}/confirm",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert confirm_resp.status_code == 403


@pytest.mark.asyncio
async def test_patch_confirmed_principle_returns_422(
    client: AsyncClient, make_token: Callable[..., str]
) -> None:
    author_token = make_token(sub="author-prn-immut-001", roles=["contributor"])
    reviewer_token = make_token(sub="reviewer-prn-immut-001", roles=["contributor"])

    create_resp = await client.post(
        "/api/v1/principles",
        json=principle_payload(),
        headers={"Authorization": f"Bearer {author_token}"},
    )
    principle_id = create_resp.json()["id"]
    await client.post(
        f"/api/v1/principles/{principle_id}/submit",
        headers={"Authorization": f"Bearer {author_token}"},
    )
    await client.post(
        f"/api/v1/principles/{principle_id}/confirm",
        headers={"Authorization": f"Bearer {reviewer_token}"},
    )

    patch_resp = await client.patch(
        f"/api/v1/principles/{principle_id}",
        json={"summary": "Attempted mutation"},
        headers={"Authorization": f"Bearer {author_token}"},
    )
    assert patch_resp.status_code == 422


# ---------------------------------------------------------------------------
# Return, deprecate, retire
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_return_principle_transitions_to_returned(
    client: AsyncClient, make_token: Callable[..., str]
) -> None:
    author_token = make_token(sub="author-prn-ret-001", roles=["contributor"])
    reviewer_token = make_token(sub="reviewer-prn-ret-001", roles=["contributor"])

    create_resp = await client.post(
        "/api/v1/principles",
        json=principle_payload(),
        headers={"Authorization": f"Bearer {author_token}"},
    )
    principle_id = create_resp.json()["id"]
    await client.post(
        f"/api/v1/principles/{principle_id}/submit",
        headers={"Authorization": f"Bearer {author_token}"},
    )

    return_resp = await client.post(
        f"/api/v1/principles/{principle_id}/return",
        json={"note": "Explanation needs more depth."},
        headers={"Authorization": f"Bearer {reviewer_token}"},
    )
    assert return_resp.status_code == 200
    assert return_resp.json()["status"] == "returned"


@pytest.mark.asyncio
async def test_deprecate_principle_admin_only(
    client: AsyncClient, make_token: Callable[..., str]
) -> None:
    admin_token = make_token(sub="admin-prn-dep-001", roles=["admin"])

    create_resp = await client.post(
        "/api/v1/principles",
        json=principle_payload(),
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    principle_id = create_resp.json()["id"]
    await client.post(
        f"/api/v1/principles/{principle_id}/submit",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    await client.post(
        f"/api/v1/principles/{principle_id}/confirm",
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    deprecate_resp = await client.post(
        f"/api/v1/principles/{principle_id}/deprecate",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert deprecate_resp.status_code == 200
    assert deprecate_resp.json()["status"] == "deprecated"


@pytest.mark.asyncio
async def test_deprecate_principle_non_admin_returns_403(
    client: AsyncClient, make_token: Callable[..., str]
) -> None:
    contributor_token = make_token(sub="contrib-prn-dep-001", roles=["contributor"])
    admin_token = make_token(sub="admin-prn-dep-002", roles=["admin"])

    create_resp = await client.post(
        "/api/v1/principles",
        json=principle_payload(),
        headers={"Authorization": f"Bearer {contributor_token}"},
    )
    principle_id = create_resp.json()["id"]
    await client.post(
        f"/api/v1/principles/{principle_id}/submit",
        headers={"Authorization": f"Bearer {contributor_token}"},
    )
    await client.post(
        f"/api/v1/principles/{principle_id}/confirm",
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    deprecate_resp = await client.post(
        f"/api/v1/principles/{principle_id}/deprecate",
        headers={"Authorization": f"Bearer {contributor_token}"},
    )
    assert deprecate_resp.status_code == 403
