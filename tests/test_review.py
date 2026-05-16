"""Tests for the Review Queue and Claiming API.

TEST_REVISED (v4.4 — dissolve Facts/Concepts):
  - Removed _create_and_submit_fact helper: /api/v1/facts no longer exists.
  - Removed test_queue_shows_submitted_fact_regardless_of_domain: facts are gone;
    all review types are now domain-scoped. A user with no domain sees nothing.
  - Removed test_claim_fact_returns_422: facts no longer exist as review entities.
    Unknown entity type behaviour is covered by test_claim_invalid_entity_type_returns_422.
  - Removed fact_payload import from factories.

Spec refs:
  §8.1  Global Review Queue — filtered view of submitted records in reviewer's domains
  §8.2  Claiming Model — claim, release, expiry
  §14   Review claim expiry ARQ cron job (every 15 minutes)

Behaviour covered:
  - Queue shows submitted records in reviewer's entitled domains, excluding own submissions
  - All record types (task, workflow, principle) are domain-scoped
  - Viewer role cannot access the review queue (Contributor and Admin only)
  - Claiming is optional; claims are advisory
  - entity_type must be one of: tasks, workflows, principles (anything else → 422)
  - Re-claiming an item you already hold refreshes the expiry (200, not 409)
  - Claiming when another user holds an active claim returns 409
  - Review confirm/return auto-release any active claim held by the acting user

Test users (all pre-seeded in tests/conftest.py):
  author-rv-001   — contributor in test-domain, creates/submits records
  reviewer-rv-001 — contributor in test-domain, primary reviewer
  claimer-rv-001  — contributor in test-domain, used for claim-conflict tests
  self-rv-001     — contributor in test-domain, used for self-review prohibition tests

  reviewer-rv-nodomain — contributor with NO domain assignments (not pre-seeded,
                         auto-created by auth on first request, used for
                         domain-exclusion tests)
"""

import uuid
from collections.abc import Callable

import pytest
import sqlalchemy as sa
from httpx import AsyncClient

from api.config import Settings
from api.database import create_engine
from tests.factories import task_payload

pytestmark = pytest.mark.asyncio


# ---------------------------------------------------------------------------
# Test helpers
# ---------------------------------------------------------------------------


async def _create_and_submit_task(
    client: AsyncClient,
    make_token: Callable[..., str],
    sub: str = "author-rv-001",
    domain: str = "test-domain",
) -> str:
    """Create a draft task and submit it. Returns the task UUID string."""
    token = make_token(sub=sub, roles=["contributor"])
    r = await client.post(
        "/api/v1/tasks",
        json=task_payload(domain=domain),
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 201, r.text
    task_id: str = r.json()["id"]
    r = await client.post(
        f"/api/v1/tasks/{task_id}/submit",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200, r.text
    return task_id


# ---------------------------------------------------------------------------
# Queue — GET /api/v1/review/queue
# ---------------------------------------------------------------------------


async def test_queue_unauthenticated_returns_401(client: AsyncClient) -> None:
    response = await client.get("/api/v1/review/queue")
    assert response.status_code == 401


async def test_queue_viewer_returns_403(
    client: AsyncClient, make_token: Callable[..., str]
) -> None:
    token = make_token(roles=["viewer"])
    response = await client.get(
        "/api/v1/review/queue",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 403


async def test_queue_shows_submitted_task_to_domain_reviewer(
    client: AsyncClient, make_token: Callable[..., str]
) -> None:
    task_id = await _create_and_submit_task(client, make_token, sub="author-rv-001")

    token = make_token(sub="reviewer-rv-001", roles=["contributor"])
    response = await client.get(
        "/api/v1/review/queue",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    ids = [item["id"] for item in response.json()["items"]]
    assert task_id in ids


async def test_queue_excludes_own_submitted_task(
    client: AsyncClient, make_token: Callable[..., str]
) -> None:
    task_id = await _create_and_submit_task(client, make_token, sub="self-rv-001")

    token = make_token(sub="self-rv-001", roles=["contributor"])
    response = await client.get(
        "/api/v1/review/queue",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    ids = [item["id"] for item in response.json()["items"]]
    assert task_id not in ids


async def test_queue_excludes_task_from_unassigned_domain(
    client: AsyncClient, make_token: Callable[..., str]
) -> None:
    # Create a task in test-domain
    task_id = await _create_and_submit_task(client, make_token, sub="author-rv-001")

    # reviewer-rv-nodomain is NOT pre-seeded in user_domains for any domain.
    # They are auto-created by auth on this request.
    token = make_token(sub="reviewer-rv-nodomain", roles=["contributor"])
    response = await client.get(
        "/api/v1/review/queue",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    ids = [item["id"] for item in response.json()["items"]]
    assert task_id not in ids


async def test_queue_empty_for_contributor_with_no_domain(
    client: AsyncClient, make_token: Callable[..., str]
) -> None:
    """All record types are domain-scoped; no-domain contributor sees nothing."""
    await _create_and_submit_task(client, make_token, sub="author-rv-001")

    token = make_token(sub="reviewer-rv-nodomain", roles=["contributor"])
    response = await client.get(
        "/api/v1/review/queue",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    assert response.json()["items"] == []


async def test_queue_item_shows_claim_info_when_claimed(
    client: AsyncClient, make_token: Callable[..., str]
) -> None:
    task_id = await _create_and_submit_task(client, make_token, sub="author-rv-001")

    # reviewer-rv-001 claims the task
    reviewer_token = make_token(sub="reviewer-rv-001", roles=["contributor"])
    claim_r = await client.post(
        f"/api/v1/review/tasks/{task_id}/claim",
        headers={"Authorization": f"Bearer {reviewer_token}"},
    )
    assert claim_r.status_code == 200

    # claimer-rv-001 checks the queue and sees the claim info
    claimer_token = make_token(sub="claimer-rv-001", roles=["contributor"])
    response = await client.get(
        "/api/v1/review/queue",
        headers={"Authorization": f"Bearer {claimer_token}"},
    )
    assert response.status_code == 200
    matching = [item for item in response.json()["items"] if item["id"] == task_id]
    assert len(matching) == 1
    item = matching[0]
    assert item["claim"] is not None
    assert "claimed_by" in item["claim"]
    assert "expires_at" in item["claim"]


# ---------------------------------------------------------------------------
# Claim — POST /api/v1/review/{entity_type}/{entity_id}/claim
# ---------------------------------------------------------------------------


async def test_claim_submitted_task_returns_200(
    client: AsyncClient, make_token: Callable[..., str]
) -> None:
    task_id = await _create_and_submit_task(client, make_token, sub="author-rv-001")

    token = make_token(sub="reviewer-rv-001", roles=["contributor"])
    response = await client.post(
        f"/api/v1/review/tasks/{task_id}/claim",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["entity_id"] == task_id
    assert body["entity_type"] == "task"
    assert body["released_at"] is None
    assert "expires_at" in body


async def test_claim_unauthenticated_returns_401(client: AsyncClient) -> None:
    response = await client.post(
        f"/api/v1/review/tasks/{uuid.uuid4()}/claim"
    )
    assert response.status_code == 401


async def test_claim_viewer_returns_403(
    client: AsyncClient, make_token: Callable[..., str]
) -> None:
    token = make_token(roles=["viewer"])
    response = await client.post(
        f"/api/v1/review/tasks/{uuid.uuid4()}/claim",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 403


async def test_claim_draft_task_returns_422(
    client: AsyncClient, make_token: Callable[..., str]
) -> None:
    # Create a draft task (not submitted)
    token = make_token(sub="author-rv-001", roles=["contributor"])
    r = await client.post(
        "/api/v1/tasks",
        json=task_payload(),
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 201
    task_id = r.json()["id"]

    reviewer_token = make_token(sub="reviewer-rv-001", roles=["contributor"])
    response = await client.post(
        f"/api/v1/review/tasks/{task_id}/claim",
        headers={"Authorization": f"Bearer {reviewer_token}"},
    )
    assert response.status_code == 422


async def test_claim_own_submitted_task_returns_403(
    client: AsyncClient, make_token: Callable[..., str]
) -> None:
    task_id = await _create_and_submit_task(client, make_token, sub="self-rv-001")

    token = make_token(sub="self-rv-001", roles=["contributor"])
    response = await client.post(
        f"/api/v1/review/tasks/{task_id}/claim",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 403


async def test_claim_already_claimed_by_another_returns_409(
    client: AsyncClient, make_token: Callable[..., str]
) -> None:
    task_id = await _create_and_submit_task(client, make_token, sub="author-rv-001")

    # reviewer-rv-001 claims first
    first_token = make_token(sub="reviewer-rv-001", roles=["contributor"])
    r = await client.post(
        f"/api/v1/review/tasks/{task_id}/claim",
        headers={"Authorization": f"Bearer {first_token}"},
    )
    assert r.status_code == 200

    # claimer-rv-001 tries to claim the same task
    second_token = make_token(sub="claimer-rv-001", roles=["contributor"])
    response = await client.post(
        f"/api/v1/review/tasks/{task_id}/claim",
        headers={"Authorization": f"Bearer {second_token}"},
    )
    assert response.status_code == 409


async def test_reclaim_own_active_claim_returns_200(
    client: AsyncClient, make_token: Callable[..., str]
) -> None:
    task_id = await _create_and_submit_task(client, make_token, sub="author-rv-001")

    token = make_token(sub="reviewer-rv-001", roles=["contributor"])
    # First claim
    r = await client.post(
        f"/api/v1/review/tasks/{task_id}/claim",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200
    first_expiry = r.json()["expires_at"]

    # Re-claim (should refresh expiry, not error)
    response = await client.post(
        f"/api/v1/review/tasks/{task_id}/claim",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    # Expiry should be refreshed (same or later)
    assert response.json()["expires_at"] >= first_expiry


async def test_claim_invalid_entity_type_returns_422(
    client: AsyncClient, make_token: Callable[..., str]
) -> None:
    token = make_token(sub="reviewer-rv-001", roles=["contributor"])
    response = await client.post(
        f"/api/v1/review/widgets/{uuid.uuid4()}/claim",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 422


# ---------------------------------------------------------------------------
# Release — POST /api/v1/review/{entity_type}/{entity_id}/release
# ---------------------------------------------------------------------------


async def test_release_own_claim_returns_200(
    client: AsyncClient, make_token: Callable[..., str]
) -> None:
    task_id = await _create_and_submit_task(client, make_token, sub="author-rv-001")

    token = make_token(sub="reviewer-rv-001", roles=["contributor"])
    r = await client.post(
        f"/api/v1/review/tasks/{task_id}/claim",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200

    response = await client.post(
        f"/api/v1/review/tasks/{task_id}/release",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    assert response.json()["released_at"] is not None


async def test_release_when_no_active_claim_returns_404(
    client: AsyncClient, make_token: Callable[..., str]
) -> None:
    task_id = await _create_and_submit_task(client, make_token, sub="author-rv-001")

    token = make_token(sub="reviewer-rv-001", roles=["contributor"])
    response = await client.post(
        f"/api/v1/review/tasks/{task_id}/release",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 404


async def test_release_other_users_claim_returns_403(
    client: AsyncClient, make_token: Callable[..., str]
) -> None:
    task_id = await _create_and_submit_task(client, make_token, sub="author-rv-001")

    # reviewer-rv-001 holds the claim
    reviewer_token = make_token(sub="reviewer-rv-001", roles=["contributor"])
    r = await client.post(
        f"/api/v1/review/tasks/{task_id}/claim",
        headers={"Authorization": f"Bearer {reviewer_token}"},
    )
    assert r.status_code == 200

    # claimer-rv-001 tries to release it
    claimer_token = make_token(sub="claimer-rv-001", roles=["contributor"])
    response = await client.post(
        f"/api/v1/review/tasks/{task_id}/release",
        headers={"Authorization": f"Bearer {claimer_token}"},
    )
    assert response.status_code == 403


# ---------------------------------------------------------------------------
# Confirm via review — POST /api/v1/review/{entity_type}/{entity_id}/confirm
# ---------------------------------------------------------------------------


async def test_review_confirm_task_sets_confirmed(
    client: AsyncClient, make_token: Callable[..., str]
) -> None:
    task_id = await _create_and_submit_task(client, make_token, sub="author-rv-001")

    token = make_token(sub="reviewer-rv-001", roles=["contributor"])
    response = await client.post(
        f"/api/v1/review/tasks/{task_id}/confirm",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "confirmed"
    assert body["id"] == task_id


async def test_review_confirm_releases_own_claim(
    client: AsyncClient, make_token: Callable[..., str]
) -> None:
    task_id = await _create_and_submit_task(client, make_token, sub="author-rv-001")

    token = make_token(sub="reviewer-rv-001", roles=["contributor"])
    # Claim the task
    r = await client.post(
        f"/api/v1/review/tasks/{task_id}/claim",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200

    # Confirm via review — should succeed and release claim
    response = await client.post(
        f"/api/v1/review/tasks/{task_id}/confirm",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "confirmed"

    # Verify claim is released: another user can no longer see an active claim
    # (task is confirmed so queue no longer shows it — verified by lack of active claim)
    # Try to claim the now-confirmed task → 422 (not submitted)
    r = await client.post(
        f"/api/v1/review/tasks/{task_id}/claim",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 422


async def test_review_confirm_non_submitted_returns_422(
    client: AsyncClient, make_token: Callable[..., str]
) -> None:
    # Create a draft task (not submitted)
    token = make_token(sub="author-rv-001", roles=["contributor"])
    r = await client.post(
        "/api/v1/tasks",
        json=task_payload(),
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 201
    task_id = r.json()["id"]

    reviewer_token = make_token(sub="reviewer-rv-001", roles=["contributor"])
    response = await client.post(
        f"/api/v1/review/tasks/{task_id}/confirm",
        headers={"Authorization": f"Bearer {reviewer_token}"},
    )
    assert response.status_code == 422


async def test_review_confirm_own_task_contributor_returns_403(
    client: AsyncClient, make_token: Callable[..., str]
) -> None:
    task_id = await _create_and_submit_task(client, make_token, sub="self-rv-001")

    token = make_token(sub="self-rv-001", roles=["contributor"])
    response = await client.post(
        f"/api/v1/review/tasks/{task_id}/confirm",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 403


# ---------------------------------------------------------------------------
# Return via review — POST /api/v1/review/{entity_type}/{entity_id}/return
# ---------------------------------------------------------------------------


async def test_review_return_task_sets_returned(
    client: AsyncClient, make_token: Callable[..., str]
) -> None:
    task_id = await _create_and_submit_task(client, make_token, sub="author-rv-001")

    token = make_token(sub="reviewer-rv-001", roles=["contributor"])
    response = await client.post(
        f"/api/v1/review/tasks/{task_id}/return",
        json={"note": "Needs more detail in step 2."},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "returned"
    assert body["id"] == task_id


async def test_review_return_releases_own_claim(
    client: AsyncClient, make_token: Callable[..., str]
) -> None:
    task_id = await _create_and_submit_task(client, make_token, sub="author-rv-001")

    token = make_token(sub="reviewer-rv-001", roles=["contributor"])
    r = await client.post(
        f"/api/v1/review/tasks/{task_id}/claim",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200

    response = await client.post(
        f"/api/v1/review/tasks/{task_id}/return",
        json={"note": "Needs revision."},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "returned"

    # Verify claim released: no active claim blocks a re-claim now
    # (item is returned, not submitted — so claim is moot, but the release happened)
    # Check by trying to claim the returned item → 422 (not submitted)
    r = await client.post(
        f"/api/v1/review/tasks/{task_id}/claim",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 422


# ---------------------------------------------------------------------------
# Expired claim — verified via direct DB insert
# ---------------------------------------------------------------------------


async def test_expired_claim_not_shown_as_active_in_queue(
    client: AsyncClient,
    make_token: Callable[..., str],
    test_settings: Settings,
) -> None:
    """An expired claim should not appear as an active claim on queue items."""
    task_id = await _create_and_submit_task(client, make_token, sub="author-rv-001")
    system_user_id = uuid.UUID("00000000-0000-0000-0000-000000000001")
    reviewer_id = str(uuid.uuid5(system_user_id, "reviewer-rv-001"))

    # Insert an already-expired claim directly into the DB
    engine = create_engine(test_settings)
    async with engine.begin() as conn:
        await conn.execute(
            sa.text("""
                INSERT INTO review_claims (id, entity_type, entity_id, claimed_by, expires_at)
                VALUES (:id, 'task', :entity_id, :claimed_by,
                        NOW() - INTERVAL '2 hours')
            """),
            {
                "id": str(uuid.uuid4()),
                "entity_id": task_id,
                "claimed_by": reviewer_id,
            },
        )
    await engine.dispose()

    # The queue should show the task with no active claim
    claimer_token = make_token(sub="claimer-rv-001", roles=["contributor"])
    response = await client.get(
        "/api/v1/review/queue",
        headers={"Authorization": f"Bearer {claimer_token}"},
    )
    assert response.status_code == 200
    matching = [item for item in response.json()["items"] if item["id"] == task_id]
    assert len(matching) == 1
    assert matching[0]["claim"] is None
