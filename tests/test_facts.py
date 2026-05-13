"""Tests for the Facts lifecycle API.

Spec refs:
  §9.3  Lifecycle state machine (draft → submitted → confirmed → deprecated/retired)
  §9.5  Facts schema (title, body, tags, embedding)
  §10.1 Immutability once confirmed
  §10.2 No machine can confirm (Sprint 4-9: requiring valid OIDC JWT is sufficient)
  §5.1  Human roles and the self-review prohibition

Assumptions captured here (flag as TEST_REVISED if Sprint 4 diverges):
  - API paths follow /api/v1/facts and /api/v1/facts/{id}/...
  - {id} is the version-specific UUID (§9.1 id field)
  - PATCH is accepted on draft and returned; rejected (422) on all other statuses
  - return endpoint accepts an optional note body
  - deprecate and retire are admin-only
  - Version is 1 on first creation; increments are not tested here (Sprint 4 to define)

All tests are skipped pending Sprint 4 implementation.
"""

from collections.abc import Callable

import pytest
from httpx import AsyncClient

from tests.factories import fact_payload

pytestmark = pytest.mark.asyncio


# ---------------------------------------------------------------------------
# Create draft  (POST /api/v1/facts)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_create_fact_unauthenticated_returns_401(client: AsyncClient) -> None:
    response = await client.post("/api/v1/facts", json=fact_payload())
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_create_fact_viewer_returns_403(
    client: AsyncClient, make_token: Callable[..., str]
) -> None:
    token = make_token(roles=["viewer"])
    response = await client.post(
        "/api/v1/facts",
        json=fact_payload(),
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_create_fact_contributor_returns_201_draft(
    client: AsyncClient, make_token: Callable[..., str]
) -> None:
    token = make_token(roles=["contributor"])
    response = await client.post(
        "/api/v1/facts",
        json=fact_payload(),
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "draft"
    assert body["title"] == fact_payload()["title"]
    assert body["body"] == fact_payload()["body"]
    assert "id" in body
    assert "record_id" in body
    assert body["version"] == 1


@pytest.mark.asyncio
async def test_create_fact_admin_returns_201_draft(
    client: AsyncClient, make_token: Callable[..., str]
) -> None:
    token = make_token(roles=["admin"])
    response = await client.post(
        "/api/v1/facts",
        json=fact_payload(title="Admin-authored fact"),
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 201
    assert response.json()["status"] == "draft"


@pytest.mark.asyncio
async def test_create_fact_missing_title_returns_422(
    client: AsyncClient, make_token: Callable[..., str]
) -> None:
    token = make_token(roles=["contributor"])
    response = await client.post(
        "/api/v1/facts",
        json={"body": "Body with no title"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_create_fact_missing_body_returns_422(
    client: AsyncClient, make_token: Callable[..., str]
) -> None:
    token = make_token(roles=["contributor"])
    response = await client.post(
        "/api/v1/facts",
        json={"title": "Title with no body"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_create_fact_with_tags(
    client: AsyncClient, make_token: Callable[..., str]
) -> None:
    token = make_token(roles=["contributor"])
    response = await client.post(
        "/api/v1/facts",
        json=fact_payload(tags=["security", "credentials"]),
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 201
    assert response.json()["tags"] == ["security", "credentials"]


@pytest.mark.asyncio
async def test_create_fact_response_has_required_fields(
    client: AsyncClient, make_token: Callable[..., str]
) -> None:
    token = make_token(roles=["contributor"])
    response = await client.post(
        "/api/v1/facts",
        json=fact_payload(),
        headers={"Authorization": f"Bearer {token}"},
    )
    body = response.json()
    required = (
        "id", "record_id", "version", "status",
        "title", "body", "tags", "created_at", "updated_at", "created_by",
    )
    for field in required:
        assert field in body, f"Missing field: {field}"


# ---------------------------------------------------------------------------
# Read  (GET /api/v1/facts/{id})
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_fact_unauthenticated_returns_401(client: AsyncClient) -> None:
    response = await client.get("/api/v1/facts/00000000-0000-0000-0000-000000000001")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_get_fact_not_found_returns_404(
    client: AsyncClient, make_token: Callable[..., str]
) -> None:
    token = make_token(roles=["viewer"])
    response = await client.get(
        "/api/v1/facts/00000000-0000-0000-0000-000000000000",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_get_fact_returns_correct_record(
    client: AsyncClient, make_token: Callable[..., str]
) -> None:
    token = make_token(roles=["contributor"])
    create_resp = await client.post(
        "/api/v1/facts",
        json=fact_payload(title="Unique title for get test"),
        headers={"Authorization": f"Bearer {token}"},
    )
    assert create_resp.status_code == 201
    fact_id = create_resp.json()["id"]

    get_resp = await client.get(
        f"/api/v1/facts/{fact_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert get_resp.status_code == 200
    assert get_resp.json()["id"] == fact_id
    assert get_resp.json()["title"] == "Unique title for get test"


@pytest.mark.asyncio
async def test_viewer_can_read_draft_fact(
    client: AsyncClient, make_token: Callable[..., str]
) -> None:
    contributor_token = make_token(sub="contrib-read-001", roles=["contributor"])
    viewer_token = make_token(sub="viewer-read-001", roles=["viewer"])

    create_resp = await client.post(
        "/api/v1/facts",
        json=fact_payload(),
        headers={"Authorization": f"Bearer {contributor_token}"},
    )
    fact_id = create_resp.json()["id"]

    get_resp = await client.get(
        f"/api/v1/facts/{fact_id}",
        headers={"Authorization": f"Bearer {viewer_token}"},
    )
    assert get_resp.status_code == 200


# ---------------------------------------------------------------------------
# List  (GET /api/v1/facts)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_list_facts_unauthenticated_returns_401(client: AsyncClient) -> None:
    response = await client.get("/api/v1/facts")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_list_facts_returns_200(
    client: AsyncClient, make_token: Callable[..., str]
) -> None:
    token = make_token(roles=["viewer"])
    response = await client.get(
        "/api/v1/facts",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200


# ---------------------------------------------------------------------------
# Update draft  (PATCH /api/v1/facts/{id})
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_patch_fact_draft_succeeds(
    client: AsyncClient, make_token: Callable[..., str]
) -> None:
    token = make_token(roles=["contributor"])
    create_resp = await client.post(
        "/api/v1/facts",
        json=fact_payload(),
        headers={"Authorization": f"Bearer {token}"},
    )
    fact_id = create_resp.json()["id"]

    patch_resp = await client.patch(
        f"/api/v1/facts/{fact_id}",
        json={"title": "Updated title"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert patch_resp.status_code == 200
    assert patch_resp.json()["title"] == "Updated title"
    assert patch_resp.json()["status"] == "draft"


@pytest.mark.asyncio
async def test_patch_fact_unauthenticated_returns_401(client: AsyncClient) -> None:
    response = await client.patch(
        "/api/v1/facts/00000000-0000-0000-0000-000000000001",
        json={"title": "Updated"},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_patch_submitted_fact_returns_422(
    client: AsyncClient, make_token: Callable[..., str]
) -> None:
    """Submitted facts cannot be edited — return them first."""
    token = make_token(roles=["contributor"])
    create_resp = await client.post(
        "/api/v1/facts",
        json=fact_payload(),
        headers={"Authorization": f"Bearer {token}"},
    )
    fact_id = create_resp.json()["id"]
    await client.post(
        f"/api/v1/facts/{fact_id}/submit",
        headers={"Authorization": f"Bearer {token}"},
    )

    patch_resp = await client.patch(
        f"/api/v1/facts/{fact_id}",
        json={"title": "Attempted edit of submitted fact"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert patch_resp.status_code == 422


# ---------------------------------------------------------------------------
# Submit  (POST /api/v1/facts/{id}/submit)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_submit_fact_transitions_to_submitted(
    client: AsyncClient, make_token: Callable[..., str]
) -> None:
    token = make_token(roles=["contributor"])
    create_resp = await client.post(
        "/api/v1/facts",
        json=fact_payload(),
        headers={"Authorization": f"Bearer {token}"},
    )
    fact_id = create_resp.json()["id"]

    submit_resp = await client.post(
        f"/api/v1/facts/{fact_id}/submit",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert submit_resp.status_code == 200
    assert submit_resp.json()["status"] == "submitted"


@pytest.mark.asyncio
async def test_submit_already_submitted_returns_422(
    client: AsyncClient, make_token: Callable[..., str]
) -> None:
    token = make_token(roles=["contributor"])
    create_resp = await client.post(
        "/api/v1/facts",
        json=fact_payload(),
        headers={"Authorization": f"Bearer {token}"},
    )
    fact_id = create_resp.json()["id"]
    await client.post(
        f"/api/v1/facts/{fact_id}/submit",
        headers={"Authorization": f"Bearer {token}"},
    )

    second_submit = await client.post(
        f"/api/v1/facts/{fact_id}/submit",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert second_submit.status_code == 422


@pytest.mark.asyncio
async def test_submit_viewer_returns_403(
    client: AsyncClient, make_token: Callable[..., str]
) -> None:
    contributor_token = make_token(sub="contrib-sub-001", roles=["contributor"])
    viewer_token = make_token(sub="viewer-sub-001", roles=["viewer"])

    create_resp = await client.post(
        "/api/v1/facts",
        json=fact_payload(),
        headers={"Authorization": f"Bearer {contributor_token}"},
    )
    fact_id = create_resp.json()["id"]

    submit_resp = await client.post(
        f"/api/v1/facts/{fact_id}/submit",
        headers={"Authorization": f"Bearer {viewer_token}"},
    )
    assert submit_resp.status_code == 403


@pytest.mark.asyncio
async def test_submit_unauthenticated_returns_401(client: AsyncClient) -> None:
    response = await client.post(
        "/api/v1/facts/00000000-0000-0000-0000-000000000001/submit"
    )
    assert response.status_code == 401


# ---------------------------------------------------------------------------
# Confirm  (POST /api/v1/facts/{id}/confirm)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_confirm_fact_transitions_to_confirmed(
    client: AsyncClient, make_token: Callable[..., str]
) -> None:
    """A different contributor (not the author) can confirm a submitted fact."""
    author_token = make_token(sub="author-conf-001", roles=["contributor"])
    reviewer_token = make_token(sub="reviewer-conf-001", roles=["contributor"])

    create_resp = await client.post(
        "/api/v1/facts",
        json=fact_payload(),
        headers={"Authorization": f"Bearer {author_token}"},
    )
    fact_id = create_resp.json()["id"]
    await client.post(
        f"/api/v1/facts/{fact_id}/submit",
        headers={"Authorization": f"Bearer {author_token}"},
    )

    confirm_resp = await client.post(
        f"/api/v1/facts/{fact_id}/confirm",
        headers={"Authorization": f"Bearer {reviewer_token}"},
    )
    assert confirm_resp.status_code == 200
    assert confirm_resp.json()["status"] == "confirmed"


@pytest.mark.asyncio
async def test_confirm_own_fact_returns_403_self_review(
    client: AsyncClient, make_token: Callable[..., str]
) -> None:
    """Self-review prohibition: a contributor cannot confirm their own submission (§5.1)."""
    token = make_token(sub="self-reviewer-001", roles=["contributor"])

    create_resp = await client.post(
        "/api/v1/facts",
        json=fact_payload(),
        headers={"Authorization": f"Bearer {token}"},
    )
    fact_id = create_resp.json()["id"]
    await client.post(
        f"/api/v1/facts/{fact_id}/submit",
        headers={"Authorization": f"Bearer {token}"},
    )

    confirm_resp = await client.post(
        f"/api/v1/facts/{fact_id}/confirm",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert confirm_resp.status_code == 403


@pytest.mark.asyncio
async def test_admin_can_confirm_own_fact(
    client: AsyncClient, make_token: Callable[..., str]
) -> None:
    """Admin break-glass: admin can confirm their own content (§5.1 small-team relief valve)."""
    admin_token = make_token(sub="admin-conf-001", roles=["admin"])

    create_resp = await client.post(
        "/api/v1/facts",
        json=fact_payload(),
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    fact_id = create_resp.json()["id"]
    await client.post(
        f"/api/v1/facts/{fact_id}/submit",
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    confirm_resp = await client.post(
        f"/api/v1/facts/{fact_id}/confirm",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert confirm_resp.status_code == 200
    assert confirm_resp.json()["status"] == "confirmed"


@pytest.mark.asyncio
async def test_confirm_unsubmitted_fact_returns_422(
    client: AsyncClient, make_token: Callable[..., str]
) -> None:
    author_token = make_token(sub="author-conf-002", roles=["contributor"])
    reviewer_token = make_token(sub="reviewer-conf-002", roles=["contributor"])

    create_resp = await client.post(
        "/api/v1/facts",
        json=fact_payload(),
        headers={"Authorization": f"Bearer {author_token}"},
    )
    fact_id = create_resp.json()["id"]

    confirm_resp = await client.post(
        f"/api/v1/facts/{fact_id}/confirm",
        headers={"Authorization": f"Bearer {reviewer_token}"},
    )
    assert confirm_resp.status_code == 422


@pytest.mark.asyncio
async def test_confirm_unauthenticated_returns_401(client: AsyncClient) -> None:
    response = await client.post(
        "/api/v1/facts/00000000-0000-0000-0000-000000000001/confirm"
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_confirm_viewer_returns_403(
    client: AsyncClient, make_token: Callable[..., str]
) -> None:
    author_token = make_token(sub="author-conf-003", roles=["contributor"])
    viewer_token = make_token(sub="viewer-conf-003", roles=["viewer"])

    create_resp = await client.post(
        "/api/v1/facts",
        json=fact_payload(),
        headers={"Authorization": f"Bearer {author_token}"},
    )
    fact_id = create_resp.json()["id"]
    await client.post(
        f"/api/v1/facts/{fact_id}/submit",
        headers={"Authorization": f"Bearer {author_token}"},
    )

    confirm_resp = await client.post(
        f"/api/v1/facts/{fact_id}/confirm",
        headers={"Authorization": f"Bearer {viewer_token}"},
    )
    assert confirm_resp.status_code == 403


@pytest.mark.asyncio
async def test_double_confirm_returns_422(
    client: AsyncClient, make_token: Callable[..., str]
) -> None:
    author_token = make_token(sub="author-conf-004", roles=["contributor"])
    reviewer_token = make_token(sub="reviewer-conf-004", roles=["contributor"])

    create_resp = await client.post(
        "/api/v1/facts",
        json=fact_payload(),
        headers={"Authorization": f"Bearer {author_token}"},
    )
    fact_id = create_resp.json()["id"]
    await client.post(
        f"/api/v1/facts/{fact_id}/submit",
        headers={"Authorization": f"Bearer {author_token}"},
    )
    await client.post(
        f"/api/v1/facts/{fact_id}/confirm",
        headers={"Authorization": f"Bearer {reviewer_token}"},
    )

    second_confirm = await client.post(
        f"/api/v1/facts/{fact_id}/confirm",
        headers={"Authorization": f"Bearer {reviewer_token}"},
    )
    assert second_confirm.status_code == 422


# ---------------------------------------------------------------------------
# Immutability after confirm  (§10.1)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_patch_confirmed_fact_returns_422(
    client: AsyncClient, make_token: Callable[..., str]
) -> None:
    """Confirmed facts are immutable — deprecate and replace to change them."""
    author_token = make_token(sub="author-immut-001", roles=["contributor"])
    reviewer_token = make_token(sub="reviewer-immut-001", roles=["contributor"])

    create_resp = await client.post(
        "/api/v1/facts",
        json=fact_payload(),
        headers={"Authorization": f"Bearer {author_token}"},
    )
    fact_id = create_resp.json()["id"]
    await client.post(
        f"/api/v1/facts/{fact_id}/submit",
        headers={"Authorization": f"Bearer {author_token}"},
    )
    await client.post(
        f"/api/v1/facts/{fact_id}/confirm",
        headers={"Authorization": f"Bearer {reviewer_token}"},
    )

    patch_resp = await client.patch(
        f"/api/v1/facts/{fact_id}",
        json={"title": "Attempted mutation of confirmed fact"},
        headers={"Authorization": f"Bearer {author_token}"},
    )
    assert patch_resp.status_code == 422


@pytest.mark.asyncio
async def test_submit_confirmed_fact_returns_422(
    client: AsyncClient, make_token: Callable[..., str]
) -> None:
    author_token = make_token(sub="author-immut-002", roles=["contributor"])
    reviewer_token = make_token(sub="reviewer-immut-002", roles=["contributor"])

    create_resp = await client.post(
        "/api/v1/facts",
        json=fact_payload(),
        headers={"Authorization": f"Bearer {author_token}"},
    )
    fact_id = create_resp.json()["id"]
    await client.post(
        f"/api/v1/facts/{fact_id}/submit",
        headers={"Authorization": f"Bearer {author_token}"},
    )
    await client.post(
        f"/api/v1/facts/{fact_id}/confirm",
        headers={"Authorization": f"Bearer {reviewer_token}"},
    )

    submit_resp = await client.post(
        f"/api/v1/facts/{fact_id}/submit",
        headers={"Authorization": f"Bearer {author_token}"},
    )
    assert submit_resp.status_code == 422


# ---------------------------------------------------------------------------
# Return  (POST /api/v1/facts/{id}/return)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_return_fact_transitions_to_returned(
    client: AsyncClient, make_token: Callable[..., str]
) -> None:
    author_token = make_token(sub="author-ret-001", roles=["contributor"])
    reviewer_token = make_token(sub="reviewer-ret-001", roles=["contributor"])

    create_resp = await client.post(
        "/api/v1/facts",
        json=fact_payload(),
        headers={"Authorization": f"Bearer {author_token}"},
    )
    fact_id = create_resp.json()["id"]
    await client.post(
        f"/api/v1/facts/{fact_id}/submit",
        headers={"Authorization": f"Bearer {author_token}"},
    )

    return_resp = await client.post(
        f"/api/v1/facts/{fact_id}/return",
        json={"note": "Please clarify the scope of the claim."},
        headers={"Authorization": f"Bearer {reviewer_token}"},
    )
    assert return_resp.status_code == 200
    assert return_resp.json()["status"] == "returned"


@pytest.mark.asyncio
async def test_returned_fact_can_be_patched(
    client: AsyncClient, make_token: Callable[..., str]
) -> None:
    author_token = make_token(sub="author-ret-002", roles=["contributor"])
    reviewer_token = make_token(sub="reviewer-ret-002", roles=["contributor"])

    create_resp = await client.post(
        "/api/v1/facts",
        json=fact_payload(),
        headers={"Authorization": f"Bearer {author_token}"},
    )
    fact_id = create_resp.json()["id"]
    await client.post(
        f"/api/v1/facts/{fact_id}/submit",
        headers={"Authorization": f"Bearer {author_token}"},
    )
    await client.post(
        f"/api/v1/facts/{fact_id}/return",
        json={"note": "Needs revision."},
        headers={"Authorization": f"Bearer {reviewer_token}"},
    )

    patch_resp = await client.patch(
        f"/api/v1/facts/{fact_id}",
        json={"body": "Revised body with clearer scope."},
        headers={"Authorization": f"Bearer {author_token}"},
    )
    assert patch_resp.status_code == 200
    assert patch_resp.json()["status"] == "returned"


@pytest.mark.asyncio
async def test_returned_fact_can_be_resubmitted(
    client: AsyncClient, make_token: Callable[..., str]
) -> None:
    author_token = make_token(sub="author-ret-003", roles=["contributor"])
    reviewer_token = make_token(sub="reviewer-ret-003", roles=["contributor"])

    create_resp = await client.post(
        "/api/v1/facts",
        json=fact_payload(),
        headers={"Authorization": f"Bearer {author_token}"},
    )
    fact_id = create_resp.json()["id"]
    await client.post(
        f"/api/v1/facts/{fact_id}/submit",
        headers={"Authorization": f"Bearer {author_token}"},
    )
    await client.post(
        f"/api/v1/facts/{fact_id}/return",
        json={"note": "Needs revision."},
        headers={"Authorization": f"Bearer {reviewer_token}"},
    )

    resubmit_resp = await client.post(
        f"/api/v1/facts/{fact_id}/submit",
        headers={"Authorization": f"Bearer {author_token}"},
    )
    assert resubmit_resp.status_code == 200
    assert resubmit_resp.json()["status"] == "submitted"


@pytest.mark.asyncio
async def test_return_draft_fact_returns_422(
    client: AsyncClient, make_token: Callable[..., str]
) -> None:
    """Can only return a submitted fact — draft has not entered review."""
    author_token = make_token(sub="author-ret-004", roles=["contributor"])
    reviewer_token = make_token(sub="reviewer-ret-004", roles=["contributor"])

    create_resp = await client.post(
        "/api/v1/facts",
        json=fact_payload(),
        headers={"Authorization": f"Bearer {author_token}"},
    )
    fact_id = create_resp.json()["id"]

    return_resp = await client.post(
        f"/api/v1/facts/{fact_id}/return",
        json={"note": "Not ready."},
        headers={"Authorization": f"Bearer {reviewer_token}"},
    )
    assert return_resp.status_code == 422


# ---------------------------------------------------------------------------
# Deprecate  (POST /api/v1/facts/{id}/deprecate)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_deprecate_confirmed_fact_transitions_to_deprecated(
    client: AsyncClient, make_token: Callable[..., str]
) -> None:
    author_token = make_token(sub="author-dep-001", roles=["contributor"])
    admin_token = make_token(sub="admin-dep-001", roles=["admin"])

    create_resp = await client.post(
        "/api/v1/facts",
        json=fact_payload(),
        headers={"Authorization": f"Bearer {author_token}"},
    )
    fact_id = create_resp.json()["id"]
    await client.post(
        f"/api/v1/facts/{fact_id}/submit",
        headers={"Authorization": f"Bearer {author_token}"},
    )
    await client.post(
        f"/api/v1/facts/{fact_id}/confirm",
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    deprecate_resp = await client.post(
        f"/api/v1/facts/{fact_id}/deprecate",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert deprecate_resp.status_code == 200
    assert deprecate_resp.json()["status"] == "deprecated"


@pytest.mark.asyncio
async def test_deprecate_non_admin_returns_403(
    client: AsyncClient, make_token: Callable[..., str]
) -> None:
    author_token = make_token(sub="author-dep-002", roles=["contributor"])
    reviewer_token = make_token(sub="reviewer-dep-002", roles=["contributor"])

    create_resp = await client.post(
        "/api/v1/facts",
        json=fact_payload(),
        headers={"Authorization": f"Bearer {author_token}"},
    )
    fact_id = create_resp.json()["id"]
    await client.post(
        f"/api/v1/facts/{fact_id}/submit",
        headers={"Authorization": f"Bearer {author_token}"},
    )
    await client.post(
        f"/api/v1/facts/{fact_id}/confirm",
        headers={"Authorization": f"Bearer {reviewer_token}"},
    )

    deprecate_resp = await client.post(
        f"/api/v1/facts/{fact_id}/deprecate",
        headers={"Authorization": f"Bearer {reviewer_token}"},
    )
    assert deprecate_resp.status_code == 403


@pytest.mark.asyncio
async def test_deprecate_unconfirmed_fact_returns_422(
    client: AsyncClient, make_token: Callable[..., str]
) -> None:
    """Only confirmed facts can be deprecated."""
    admin_token = make_token(sub="admin-dep-003", roles=["admin"])

    create_resp = await client.post(
        "/api/v1/facts",
        json=fact_payload(),
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    fact_id = create_resp.json()["id"]

    deprecate_resp = await client.post(
        f"/api/v1/facts/{fact_id}/deprecate",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert deprecate_resp.status_code == 422


# ---------------------------------------------------------------------------
# Retire  (POST /api/v1/facts/{id}/retire)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_retire_confirmed_fact_transitions_to_retired(
    client: AsyncClient, make_token: Callable[..., str]
) -> None:
    admin_token = make_token(sub="admin-rtire-001", roles=["admin"])

    create_resp = await client.post(
        "/api/v1/facts",
        json=fact_payload(),
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    fact_id = create_resp.json()["id"]
    await client.post(
        f"/api/v1/facts/{fact_id}/submit",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    await client.post(
        f"/api/v1/facts/{fact_id}/confirm",
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    retire_resp = await client.post(
        f"/api/v1/facts/{fact_id}/retire",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert retire_resp.status_code == 200
    assert retire_resp.json()["status"] == "retired"


@pytest.mark.asyncio
async def test_retire_non_admin_returns_403(
    client: AsyncClient, make_token: Callable[..., str]
) -> None:
    contributor_token = make_token(sub="contrib-rtire-001", roles=["contributor"])
    admin_token = make_token(sub="admin-rtire-002", roles=["admin"])

    create_resp = await client.post(
        "/api/v1/facts",
        json=fact_payload(),
        headers={"Authorization": f"Bearer {contributor_token}"},
    )
    fact_id = create_resp.json()["id"]
    await client.post(
        f"/api/v1/facts/{fact_id}/submit",
        headers={"Authorization": f"Bearer {contributor_token}"},
    )
    await client.post(
        f"/api/v1/facts/{fact_id}/confirm",
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    retire_resp = await client.post(
        f"/api/v1/facts/{fact_id}/retire",
        headers={"Authorization": f"Bearer {contributor_token}"},
    )
    assert retire_resp.status_code == 403


@pytest.mark.asyncio
async def test_retire_unconfirmed_fact_returns_422(
    client: AsyncClient, make_token: Callable[..., str]
) -> None:
    admin_token = make_token(sub="admin-rtire-003", roles=["admin"])

    create_resp = await client.post(
        "/api/v1/facts",
        json=fact_payload(),
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    fact_id = create_resp.json()["id"]

    retire_resp = await client.post(
        f"/api/v1/facts/{fact_id}/retire",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert retire_resp.status_code == 422
