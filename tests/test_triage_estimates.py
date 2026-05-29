"""Tests for triage estimate review endpoints (§11.5a).

Spec refs:
  §11.5a Triage Estimate Review
  §11.8a ingestion_triage_estimates table

Behaviour covered:
  - Auth: unauthenticated → 401
  - GET estimates: returns list ordered by sort_order
  - GET estimates: 404 when ingestion or chunk not found, or wrong owner
  - PATCH estimate: updates type, title, or rejects
  - PATCH estimate: 422 when estimate not in pending state
  - PATCH estimate: 422 when approved_type invalid
  - PATCH estimate: 422 when estimate_status not 'rejected'
  - POST merge: combines two estimates, survivor gets merged_title
  - POST merge: 422 when fewer than two IDs supplied
  - POST merge: 404 when estimate IDs not found on chunk
  - POST merge: 422 when any estimate not in pending state
  - POST approve: marks pending estimates approved, sets chunk to extraction_queued
  - POST approve: enqueues extract_chunk ARQ job
  - POST approve: all rejected/merged → chunk moves to done, no job enqueued
  - POST approve: 422 when chunk not in triage_complete state

Test users:
  author-ing-001 — contributor, used for all ingestion tests
"""

import uuid
from collections.abc import Callable

import pytest
import sqlalchemy as sa
from httpx import AsyncClient

from api.config import Settings
from api.database import create_engine
from tests.conftest import StubArqPool

pytestmark = pytest.mark.asyncio

_ING_SUB = "author-ing-001"


async def _make_ingestion_with_triage_complete_chunk(
    settings: Settings,
) -> tuple[uuid.UUID, uuid.UUID]:
    """Seed an ingestion + chunk in triage_complete state; return (ingestion_id, chunk_id)."""
    engine = create_engine(settings)
    ing_id = uuid.uuid4()
    chunk_id = uuid.uuid4()
    user_id = uuid.uuid5(uuid.UUID("00000000-0000-0000-0000-000000000001"), _ING_SUB)
    async with engine.begin() as conn:
        await conn.execute(
            sa.text("""
                INSERT INTO ingestions (id, source_type, status, created_by)
                VALUES (:id, 'pdf', 'ready', :user_id)
            """),
            {"id": ing_id, "user_id": user_id},
        )
        await conn.execute(
            sa.text("""
                INSERT INTO ingestion_chunks
                  (id, ingestion_id, chunk_index, section_title, section_level,
                   text, text_preview, word_count, chunk_status, candidate_count)
                VALUES (:id, :ing_id, 0, 'Test Section', 1,
                        'chunk text', 'chunk text', 2, 'triage_complete', 0)
            """),
            {"id": chunk_id, "ing_id": ing_id},
        )
    await engine.dispose()
    return ing_id, chunk_id


async def _seed_estimates(
    settings: Settings,
    ing_id: uuid.UUID,
    chunk_id: uuid.UUID,
    estimates: list[dict],
) -> list[uuid.UUID]:
    """Insert estimate rows and return their IDs in order."""
    engine = create_engine(settings)
    ids = [uuid.uuid4() for _ in estimates]
    async with engine.begin() as conn:
        for i, (eid, est) in enumerate(zip(ids, estimates, strict=True)):
            await conn.execute(
                sa.text("""
                    INSERT INTO ingestion_triage_estimates
                      (id, ingestion_id, chunk_id, record_type, approved_type,
                       estimated_title, estimate_status, sort_order)
                    VALUES (:id, :ing_id, :chunk_id, :record_type, :approved_type,
                            :title, :status, :sort_order)
                """),
                {
                    "id": eid,
                    "ing_id": ing_id,
                    "chunk_id": chunk_id,
                    "record_type": est.get("record_type", "task"),
                    "approved_type": est.get("approved_type", "task"),
                    "title": est.get("title", f"Estimate {i}"),
                    "status": est.get("status", "pending"),
                    "sort_order": i,
                },
            )
    await engine.dispose()
    return ids


def _auth(make_token: Callable[..., str], sub: str = _ING_SUB) -> dict:
    return {"Authorization": f"Bearer {make_token(sub=sub, roles=['contributor'])}"}


# ---------------------------------------------------------------------------
# Auth guards
# ---------------------------------------------------------------------------


async def test_list_estimates_unauthenticated(
    client: AsyncClient, test_settings: Settings
) -> None:
    ing_id, chunk_id = await _make_ingestion_with_triage_complete_chunk(test_settings)
    r = await client.get(f"/api/v1/ingestions/{ing_id}/chunks/{chunk_id}/estimates")
    assert r.status_code == 401


# ---------------------------------------------------------------------------
# GET /estimates
# ---------------------------------------------------------------------------


async def test_list_estimates_returns_ordered_list(
    client: AsyncClient,
    make_token: Callable[..., str],
    test_settings: Settings,
) -> None:
    ing_id, chunk_id = await _make_ingestion_with_triage_complete_chunk(test_settings)
    await _seed_estimates(
        test_settings,
        ing_id,
        chunk_id,
        [
            {"title": "First task", "record_type": "task"},
            {"title": "Second task", "record_type": "task"},
        ],
    )
    r = await client.get(
        f"/api/v1/ingestions/{ing_id}/chunks/{chunk_id}/estimates",
        headers=_auth(make_token),
    )
    assert r.status_code == 200
    data = r.json()
    assert len(data) == 2
    assert data[0]["estimated_title"] == "First task"
    assert data[1]["estimated_title"] == "Second task"
    assert data[0]["sort_order"] < data[1]["sort_order"]


async def test_list_estimates_wrong_owner_returns_404(
    client: AsyncClient,
    make_token: Callable[..., str],
    test_settings: Settings,
) -> None:
    ing_id, chunk_id = await _make_ingestion_with_triage_complete_chunk(test_settings)
    other_token = make_token(sub="other-user-not-owner", roles=["contributor"])
    r = await client.get(
        f"/api/v1/ingestions/{ing_id}/chunks/{chunk_id}/estimates",
        headers={"Authorization": f"Bearer {other_token}"},
    )
    assert r.status_code == 404


async def test_list_estimates_unknown_chunk_returns_404(
    client: AsyncClient,
    make_token: Callable[..., str],
    test_settings: Settings,
) -> None:
    ing_id, _ = await _make_ingestion_with_triage_complete_chunk(test_settings)
    r = await client.get(
        f"/api/v1/ingestions/{ing_id}/chunks/{uuid.uuid4()}/estimates",
        headers=_auth(make_token),
    )
    assert r.status_code == 404


# ---------------------------------------------------------------------------
# PATCH /estimates/{estimate_id}
# ---------------------------------------------------------------------------


async def test_patch_estimate_updates_approved_type(
    client: AsyncClient,
    make_token: Callable[..., str],
    test_settings: Settings,
) -> None:
    ing_id, chunk_id = await _make_ingestion_with_triage_complete_chunk(test_settings)
    (est_id,) = await _seed_estimates(
        test_settings, ing_id, chunk_id, [{"record_type": "task", "title": "A task"}]
    )
    r = await client.patch(
        f"/api/v1/ingestions/{ing_id}/chunks/{chunk_id}/estimates/{est_id}",
        json={"approved_type": "principle"},
        headers=_auth(make_token),
    )
    assert r.status_code == 200
    assert r.json()["approved_type"] == "principle"


async def test_patch_estimate_updates_title(
    client: AsyncClient,
    make_token: Callable[..., str],
    test_settings: Settings,
) -> None:
    ing_id, chunk_id = await _make_ingestion_with_triage_complete_chunk(test_settings)
    (est_id,) = await _seed_estimates(
        test_settings, ing_id, chunk_id, [{"title": "Old title"}]
    )
    r = await client.patch(
        f"/api/v1/ingestions/{ing_id}/chunks/{chunk_id}/estimates/{est_id}",
        json={"estimated_title": "New title"},
        headers=_auth(make_token),
    )
    assert r.status_code == 200
    assert r.json()["estimated_title"] == "New title"


async def test_patch_estimate_reject(
    client: AsyncClient,
    make_token: Callable[..., str],
    test_settings: Settings,
) -> None:
    ing_id, chunk_id = await _make_ingestion_with_triage_complete_chunk(test_settings)
    (est_id,) = await _seed_estimates(test_settings, ing_id, chunk_id, [{}])
    r = await client.patch(
        f"/api/v1/ingestions/{ing_id}/chunks/{chunk_id}/estimates/{est_id}",
        json={"estimate_status": "rejected"},
        headers=_auth(make_token),
    )
    assert r.status_code == 200
    assert r.json()["estimate_status"] == "rejected"


async def test_patch_estimate_invalid_approved_type_returns_422(
    client: AsyncClient,
    make_token: Callable[..., str],
    test_settings: Settings,
) -> None:
    ing_id, chunk_id = await _make_ingestion_with_triage_complete_chunk(test_settings)
    (est_id,) = await _seed_estimates(test_settings, ing_id, chunk_id, [{}])
    r = await client.patch(
        f"/api/v1/ingestions/{ing_id}/chunks/{chunk_id}/estimates/{est_id}",
        json={"approved_type": "workflow"},
        headers=_auth(make_token),
    )
    assert r.status_code == 422


async def test_patch_estimate_invalid_status_value_returns_422(
    client: AsyncClient,
    make_token: Callable[..., str],
    test_settings: Settings,
) -> None:
    ing_id, chunk_id = await _make_ingestion_with_triage_complete_chunk(test_settings)
    (est_id,) = await _seed_estimates(test_settings, ing_id, chunk_id, [{}])
    r = await client.patch(
        f"/api/v1/ingestions/{ing_id}/chunks/{chunk_id}/estimates/{est_id}",
        json={"estimate_status": "approved"},  # only 'rejected' is valid via PATCH
        headers=_auth(make_token),
    )
    assert r.status_code == 422


async def test_patch_estimate_non_pending_returns_422(
    client: AsyncClient,
    make_token: Callable[..., str],
    test_settings: Settings,
) -> None:
    ing_id, chunk_id = await _make_ingestion_with_triage_complete_chunk(test_settings)
    (est_id,) = await _seed_estimates(
        test_settings, ing_id, chunk_id, [{"status": "rejected"}]
    )
    r = await client.patch(
        f"/api/v1/ingestions/{ing_id}/chunks/{chunk_id}/estimates/{est_id}",
        json={"estimated_title": "New title"},
        headers=_auth(make_token),
    )
    assert r.status_code == 422


# ---------------------------------------------------------------------------
# POST /estimates/merge
# ---------------------------------------------------------------------------


async def test_merge_estimates_survivor_gets_merged_title(
    client: AsyncClient,
    make_token: Callable[..., str],
    test_settings: Settings,
) -> None:
    ing_id, chunk_id = await _make_ingestion_with_triage_complete_chunk(test_settings)
    ids = await _seed_estimates(
        test_settings,
        ing_id,
        chunk_id,
        [{"title": "Part A"}, {"title": "Part B"}],
    )
    r = await client.post(
        f"/api/v1/ingestions/{ing_id}/chunks/{chunk_id}/estimates/merge",
        json={"estimate_ids": [str(ids[0]), str(ids[1])], "merged_title": "Combined A+B"},
        headers=_auth(make_token),
    )
    assert r.status_code == 200
    assert r.json()["surviving_id"] == str(ids[0])

    # Check state via GET
    r2 = await client.get(
        f"/api/v1/ingestions/{ing_id}/chunks/{chunk_id}/estimates",
        headers=_auth(make_token),
    )
    estimates = {e["id"]: e for e in r2.json()}
    assert estimates[str(ids[0])]["estimated_title"] == "Combined A+B"
    assert estimates[str(ids[0])]["estimate_status"] == "pending"
    assert estimates[str(ids[1])]["estimate_status"] == "merged"
    assert estimates[str(ids[1])]["merged_into_id"] == str(ids[0])


async def test_merge_estimates_requires_two_ids(
    client: AsyncClient,
    make_token: Callable[..., str],
    test_settings: Settings,
) -> None:
    ing_id, chunk_id = await _make_ingestion_with_triage_complete_chunk(test_settings)
    (est_id,) = await _seed_estimates(test_settings, ing_id, chunk_id, [{}])
    r = await client.post(
        f"/api/v1/ingestions/{ing_id}/chunks/{chunk_id}/estimates/merge",
        json={"estimate_ids": [str(est_id)], "merged_title": "Only one"},
        headers=_auth(make_token),
    )
    assert r.status_code == 422


async def test_merge_estimates_unknown_ids_return_404(
    client: AsyncClient,
    make_token: Callable[..., str],
    test_settings: Settings,
) -> None:
    ing_id, chunk_id = await _make_ingestion_with_triage_complete_chunk(test_settings)
    r = await client.post(
        f"/api/v1/ingestions/{ing_id}/chunks/{chunk_id}/estimates/merge",
        json={
            "estimate_ids": [str(uuid.uuid4()), str(uuid.uuid4())],
            "merged_title": "Ghost merge",
        },
        headers=_auth(make_token),
    )
    assert r.status_code == 404


async def test_merge_estimates_non_pending_returns_422(
    client: AsyncClient,
    make_token: Callable[..., str],
    test_settings: Settings,
) -> None:
    ing_id, chunk_id = await _make_ingestion_with_triage_complete_chunk(test_settings)
    ids = await _seed_estimates(
        test_settings,
        ing_id,
        chunk_id,
        [{"title": "A", "status": "rejected"}, {"title": "B"}],
    )
    r = await client.post(
        f"/api/v1/ingestions/{ing_id}/chunks/{chunk_id}/estimates/merge",
        json={"estimate_ids": [str(ids[0]), str(ids[1])], "merged_title": "Nope"},
        headers=_auth(make_token),
    )
    assert r.status_code == 422


# ---------------------------------------------------------------------------
# POST /estimates/approve
# ---------------------------------------------------------------------------


async def test_approve_estimates_queues_extraction(
    client: AsyncClient,
    make_token: Callable[..., str],
    test_settings: Settings,
) -> None:
    ing_id, chunk_id = await _make_ingestion_with_triage_complete_chunk(test_settings)
    await _seed_estimates(
        test_settings,
        ing_id,
        chunk_id,
        [{"title": "Task A"}, {"title": "Task B"}],
    )
    StubArqPool.enqueued.clear()
    r = await client.post(
        f"/api/v1/ingestions/{ing_id}/chunks/{chunk_id}/estimates/approve",
        headers=_auth(make_token),
    )
    assert r.status_code == 200
    assert r.json()["extraction_queued"] == 2

    # Chunk should now be extraction_queued
    engine = create_engine(test_settings)
    async with engine.begin() as conn:
        row = (
            await conn.execute(
                sa.text("SELECT chunk_status FROM ingestion_chunks WHERE id = :id"),
                {"id": chunk_id},
            )
        ).fetchone()
    await engine.dispose()
    assert row is not None and row[0] == "extraction_queued"

    # ARQ job enqueued
    assert any(fn == "extract_chunk" for fn, _ in StubArqPool.enqueued)


async def test_approve_estimates_marks_approved(
    client: AsyncClient,
    make_token: Callable[..., str],
    test_settings: Settings,
) -> None:
    ing_id, chunk_id = await _make_ingestion_with_triage_complete_chunk(test_settings)
    ids = await _seed_estimates(test_settings, ing_id, chunk_id, [{"title": "One"}])
    await client.post(
        f"/api/v1/ingestions/{ing_id}/chunks/{chunk_id}/estimates/approve",
        headers=_auth(make_token),
    )
    r = await client.get(
        f"/api/v1/ingestions/{ing_id}/chunks/{chunk_id}/estimates",
        headers=_auth(make_token),
    )
    est = next(e for e in r.json() if e["id"] == str(ids[0]))
    assert est["estimate_status"] == "approved"


async def test_approve_all_rejected_moves_chunk_to_done(
    client: AsyncClient,
    make_token: Callable[..., str],
    test_settings: Settings,
) -> None:
    ing_id, chunk_id = await _make_ingestion_with_triage_complete_chunk(test_settings)
    await _seed_estimates(
        test_settings,
        ing_id,
        chunk_id,
        [{"status": "rejected"}, {"status": "merged"}],
    )
    StubArqPool.enqueued.clear()
    r = await client.post(
        f"/api/v1/ingestions/{ing_id}/chunks/{chunk_id}/estimates/approve",
        headers=_auth(make_token),
    )
    assert r.status_code == 200
    assert r.json()["extraction_queued"] == 0

    engine = create_engine(test_settings)
    async with engine.begin() as conn:
        row = (
            await conn.execute(
                sa.text("SELECT chunk_status FROM ingestion_chunks WHERE id = :id"),
                {"id": chunk_id},
            )
        ).fetchone()
    await engine.dispose()
    assert row is not None and row[0] == "done"

    assert not any(fn == "extract_chunk" for fn, _ in StubArqPool.enqueued)


async def test_approve_estimates_wrong_chunk_status_returns_422(
    client: AsyncClient,
    make_token: Callable[..., str],
    test_settings: Settings,
) -> None:
    ing_id, _ = await _make_ingestion_with_triage_complete_chunk(test_settings)
    # Create a separate chunk in 'queued' state (wrong status for approve)
    engine = create_engine(test_settings)
    queued_chunk_id = uuid.uuid4()
    user_id = uuid.uuid5(uuid.UUID("00000000-0000-0000-0000-000000000001"), _ING_SUB)
    async with engine.begin() as conn:
        await conn.execute(
            sa.text("""
                INSERT INTO ingestion_chunks
                  (id, ingestion_id, chunk_index, section_title, section_level,
                   text, text_preview, word_count, chunk_status, candidate_count)
                VALUES (:id, :ing_id, 99, 'Queued Section', 1,
                        'text', 'text', 1, 'queued', 0)
            """),
            {"id": queued_chunk_id, "ing_id": ing_id, "user_id": user_id},
        )
    await engine.dispose()

    r = await client.post(
        f"/api/v1/ingestions/{ing_id}/chunks/{queued_chunk_id}/estimates/approve",
        headers=_auth(make_token),
    )
    assert r.status_code == 422
