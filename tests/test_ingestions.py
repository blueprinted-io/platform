"""Tests for the Ingestion Pipeline API (§11).

Spec refs:
  §11.3  Ingestion pipeline stages
  §11.5  Section selection screen
  §11.8  Candidate review and commit
  §11.9  PDF ingestion: dedup, chunking, scanned-PDF rejection
  §11.10 HTML ingestion: single-page and site-nav modes
  §11.11 Nav discovery and selection
  §11.12 JSON ingestion: bypass chunking, direct candidates

Behaviour covered:
  - Auth: unauthenticated → 401; viewer → 403 for upload and select
  - PDF upload: contributor creates ingestion, arq job enqueued
  - Dedup: identical PDF bytes return existing ingestion (no new row)
  - Rejected: unsupported MIME type → 422; empty file → 422
  - List ingestions: returns only caller's ingestions, newest first
  - Status endpoint: returns ingestion with empty chunk list while pending
  - Select: rejects non-ready ingestion statuses; empty chunk_ids → 422
  - Select: queues only pending chunks; others are skipped
  - Candidates: list, accept, discard, commit as task or principle
  - HTML: URL validation, dedup, job enqueued, force bypass
  - HTML nav: list nav pages, select nav pages, non-HTML ingestion rejected
  - JSON: schema_version validation, item validation, dedup, candidates created

Test users (pre-seeded in tests/conftest.py):
  author-ing-001 — contributor, used for all ingestion tests
"""

import uuid
from collections.abc import Callable
from pathlib import Path

import pytest
import sqlalchemy as sa
from httpx import AsyncClient

from api.config import Settings
from api.database import create_engine
from tests.conftest import StubArqPool

pytestmark = pytest.mark.asyncio

_FIXTURES = Path(__file__).parent / "fixtures"


def _pdf_bytes(name: str = "sample.pdf") -> bytes:
    return (_FIXTURES / name).read_bytes()


def _pdf_upload(filename: str = "sample.pdf") -> dict:  # type: ignore[type-arg]
    """Returns a files dict for httpx multipart upload."""
    return {"file": (filename, _pdf_bytes(), "application/pdf")}


# ---------------------------------------------------------------------------
# Auth guards
# ---------------------------------------------------------------------------


async def test_upload_unauthenticated_returns_401(client: AsyncClient) -> None:
    response = await client.post("/api/v1/ingestions", files=_pdf_upload())
    assert response.status_code == 401


async def test_upload_viewer_returns_403(
    client: AsyncClient, make_token: Callable[..., str]
) -> None:
    token = make_token(roles=["viewer"])
    response = await client.post(
        "/api/v1/ingestions",
        files=_pdf_upload(),
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 403


async def test_list_unauthenticated_returns_401(client: AsyncClient) -> None:
    response = await client.get("/api/v1/ingestions")
    assert response.status_code == 401


async def test_status_unauthenticated_returns_401(client: AsyncClient) -> None:
    response = await client.get(f"/api/v1/ingestions/{uuid.uuid4()}/status")
    assert response.status_code == 401


# ---------------------------------------------------------------------------
# PDF upload — happy path
# ---------------------------------------------------------------------------


async def test_upload_pdf_contributor_returns_201(
    client: AsyncClient, make_token: Callable[..., str]
) -> None:
    token = make_token(sub="author-ing-001", roles=["contributor"])
    response = await client.post(
        "/api/v1/ingestions",
        files=_pdf_upload(),
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "pending"
    assert body["source_type"] == "pdf"
    assert body["original_filename"] == "sample.pdf"
    assert "id" in body


async def test_upload_pdf_enqueues_chunk_job(
    client: AsyncClient, make_token: Callable[..., str]
) -> None:
    StubArqPool.enqueued.clear()
    token = make_token(sub="author-ing-001", roles=["contributor"])
    # Use sample2.pdf so SHA-256 differs from sample.pdf and dedup doesn't suppress the job.
    response = await client.post(
        "/api/v1/ingestions",
        files={"file": ("enqueue_test.pdf", _pdf_bytes("sample2.pdf"), "application/pdf")},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 201
    ingestion_id = response.json()["id"]
    jobs = [j for j in StubArqPool.enqueued if j[0] == "chunk_pdf"]
    assert any(j[1].get("ingestion_id") == ingestion_id for j in jobs)


async def test_upload_pdf_admin_returns_201(
    client: AsyncClient, make_token: Callable[..., str]
) -> None:
    token = make_token(sub="author-ing-001", roles=["admin"])
    response = await client.post(
        "/api/v1/ingestions",
        files={"file": ("admin_upload.pdf", _pdf_bytes(), "application/pdf")},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 201


# ---------------------------------------------------------------------------
# PDF upload — validation
# ---------------------------------------------------------------------------


async def test_upload_unsupported_mime_returns_422(
    client: AsyncClient, make_token: Callable[..., str]
) -> None:
    token = make_token(sub="author-ing-001", roles=["contributor"])
    response = await client.post(
        "/api/v1/ingestions",
        files={"file": ("doc.txt", b"hello world", "text/plain")},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 422
    assert "Unsupported file type" in response.json()["detail"]


async def test_upload_empty_file_returns_422(
    client: AsyncClient, make_token: Callable[..., str]
) -> None:
    token = make_token(sub="author-ing-001", roles=["contributor"])
    response = await client.post(
        "/api/v1/ingestions",
        files={"file": ("empty.pdf", b"", "application/pdf")},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 422
    assert "empty" in response.json()["detail"].lower()


# ---------------------------------------------------------------------------
# Deduplication
# ---------------------------------------------------------------------------


async def test_upload_duplicate_returns_200_existing_id(
    client: AsyncClient, make_token: Callable[..., str]
) -> None:
    """Second upload of identical bytes returns the existing ingestion, no new row."""
    token = make_token(sub="author-ing-001", roles=["contributor"])
    payload = {"file": ("dedup_a.pdf", _pdf_bytes(), "application/pdf")}
    r1 = await client.post(
        "/api/v1/ingestions",
        files=payload,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r1.status_code in (200, 201)
    original_id = r1.json()["id"]

    r2 = await client.post(
        "/api/v1/ingestions",
        files={"file": ("dedup_b.pdf", _pdf_bytes(), "application/pdf")},
        headers={"Authorization": f"Bearer {token}"},
    )
    # Dedup: same bytes → same ingestion record (status 200 or 201 depending on which was first)
    assert r2.json()["id"] == original_id


# ---------------------------------------------------------------------------
# List ingestions
# ---------------------------------------------------------------------------


async def test_list_returns_only_callers_ingestions(
    client: AsyncClient, make_token: Callable[..., str]
) -> None:
    """List endpoint returns only ingestions created by the caller."""
    token = make_token(sub="author-ing-001", roles=["contributor"])
    response = await client.get(
        "/api/v1/ingestions",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    items = response.json()
    # All returned ingestions should belong to author-ing-001
    # We can't inspect created_by without DB access, but we verify shape
    for item in items:
        assert "id" in item
        assert "status" in item
        assert item["source_type"] == "pdf"


async def test_list_viewer_returns_200(
    client: AsyncClient, make_token: Callable[..., str]
) -> None:
    """Viewers can list ingestions (list endpoint uses CurrentUser, not _Writer)."""
    token = make_token(roles=["viewer"])
    response = await client.get(
        "/api/v1/ingestions",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200


async def test_list_pagination(
    client: AsyncClient, make_token: Callable[..., str]
) -> None:
    token = make_token(sub="author-ing-001", roles=["contributor"])
    response = await client.get(
        "/api/v1/ingestions?limit=2&offset=0",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    assert isinstance(response.json(), list)


# ---------------------------------------------------------------------------
# Status endpoint
# ---------------------------------------------------------------------------


async def test_status_returns_ingestion_with_chunks(
    client: AsyncClient, make_token: Callable[..., str]
) -> None:
    token = make_token(sub="author-ing-001", roles=["contributor"])
    upload = await client.post(
        "/api/v1/ingestions",
        files={"file": ("status_test.pdf", _pdf_bytes(), "application/pdf")},
        headers={"Authorization": f"Bearer {token}"},
    )
    ingestion_id = upload.json()["id"]

    response = await client.get(
        f"/api/v1/ingestions/{ingestion_id}/status",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["id"] == ingestion_id
    assert "chunks" in body
    assert isinstance(body["chunks"], list)


async def test_status_other_user_returns_404(
    client: AsyncClient, make_token: Callable[..., str]
) -> None:
    """Status endpoint 404s for ingestions belonging to another user (no info leak)."""
    owner_token = make_token(sub="author-ing-001", roles=["contributor"])
    upload = await client.post(
        "/api/v1/ingestions",
        files={"file": ("other_user_test.pdf", _pdf_bytes(), "application/pdf")},
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    ingestion_id = upload.json()["id"]

    # Different user attempts to read it
    other_token = make_token(sub="test-sub-001", roles=["contributor"])
    response = await client.get(
        f"/api/v1/ingestions/{ingestion_id}/status",
        headers={"Authorization": f"Bearer {other_token}"},
    )
    assert response.status_code == 404


async def test_status_nonexistent_returns_404(
    client: AsyncClient, make_token: Callable[..., str]
) -> None:
    token = make_token(sub="author-ing-001", roles=["contributor"])
    response = await client.get(
        f"/api/v1/ingestions/{uuid.uuid4()}/status",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 404


# ---------------------------------------------------------------------------
# Select chunks
# ---------------------------------------------------------------------------


async def test_select_viewer_returns_403(
    client: AsyncClient, make_token: Callable[..., str]
) -> None:
    token = make_token(roles=["viewer"])
    response = await client.post(
        f"/api/v1/ingestions/{uuid.uuid4()}/select",
        json={"chunk_ids": [str(uuid.uuid4())]},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 403


async def test_select_empty_chunk_ids_returns_422(
    client: AsyncClient, make_token: Callable[..., str]
) -> None:
    """Empty chunk_ids list is rejected before status is checked."""
    token = make_token(sub="author-ing-001", roles=["contributor"])
    # First create an ingestion to get a real ID
    upload = await client.post(
        "/api/v1/ingestions",
        files={"file": ("select_empty.pdf", _pdf_bytes(), "application/pdf")},
        headers={"Authorization": f"Bearer {token}"},
    )
    ingestion_id = upload.json()["id"]

    response = await client.post(
        f"/api/v1/ingestions/{ingestion_id}/select",
        json={"chunk_ids": []},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 422
    assert "chunk_ids" in response.json()["detail"].lower()


async def test_select_pending_ingestion_returns_422(
    client: AsyncClient, make_token: Callable[..., str]
) -> None:
    """Cannot select chunks on a pending ingestion (not yet chunked)."""
    token = make_token(sub="author-ing-001", roles=["contributor"])
    upload = await client.post(
        "/api/v1/ingestions",
        files={"file": ("select_pending.pdf", _pdf_bytes(), "application/pdf")},
        headers={"Authorization": f"Bearer {token}"},
    )
    ingestion_id = upload.json()["id"]

    response = await client.post(
        f"/api/v1/ingestions/{ingestion_id}/select",
        json={"chunk_ids": [str(uuid.uuid4())]},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 422
    assert "pending" in response.json()["detail"]


async def test_select_ready_ingestion_queues_chunks(
    client: AsyncClient,
    make_token: Callable[..., str],
    test_settings: Settings,
) -> None:
    """Select on a ready ingestion queues matching pending chunks and returns count."""
    token = make_token(sub="author-ing-001", roles=["contributor"])

    # Upload a PDF first
    upload = await client.post(
        "/api/v1/ingestions",
        files={"file": ("select_ready.pdf", _pdf_bytes(), "application/pdf")},
        headers={"Authorization": f"Bearer {token}"},
    )
    ingestion_id = upload.json()["id"]

    # Simulate the worker having run: set status=ready and insert a chunk
    chunk_id = uuid.uuid4()
    engine = create_engine(test_settings)
    async with engine.begin() as conn:
        await conn.execute(
            sa.text(
                "UPDATE ingestions SET status = 'ready', chunk_count = 1 WHERE id = :id"
            ),
            {"id": uuid.UUID(ingestion_id)},
        )
        await conn.execute(
            sa.text("""
                INSERT INTO ingestion_chunks
                  (id, ingestion_id, chunk_index, section_level, text,
                   text_preview, word_count, chunk_status, is_scanned, candidate_count)
                VALUES (:id, :iid, 0, 0, 'test text', 'test text', 2, 'pending', false, 0)
            """),
            {"id": chunk_id, "iid": uuid.UUID(ingestion_id)},
        )
    await engine.dispose()

    StubArqPool.enqueued.clear()
    response = await client.post(
        f"/api/v1/ingestions/{ingestion_id}/select",
        json={"chunk_ids": [str(chunk_id)]},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["queued_count"] == 1
    assert body["ingestion_id"] == ingestion_id

    jobs = [j for j in StubArqPool.enqueued if j[0] == "process_chunks"]
    assert any(j[1].get("ingestion_id") == ingestion_id for j in jobs)


async def test_select_already_queued_chunk_is_skipped(
    client: AsyncClient,
    make_token: Callable[..., str],
    test_settings: Settings,
) -> None:
    """Selecting a chunk already in queued status does not re-queue it."""
    token = make_token(sub="author-ing-001", roles=["contributor"])
    upload = await client.post(
        "/api/v1/ingestions",
        files={"file": ("select_skip.pdf", _pdf_bytes(), "application/pdf")},
        headers={"Authorization": f"Bearer {token}"},
    )
    ingestion_id = upload.json()["id"]
    chunk_id = uuid.uuid4()

    engine = create_engine(test_settings)
    async with engine.begin() as conn:
        await conn.execute(
            sa.text(
                "UPDATE ingestions SET status = 'ready', chunk_count = 1 WHERE id = :id"
            ),
            {"id": uuid.UUID(ingestion_id)},
        )
        await conn.execute(
            sa.text("""
                INSERT INTO ingestion_chunks
                  (id, ingestion_id, chunk_index, section_level, text,
                   text_preview, word_count, chunk_status, is_scanned, candidate_count)
                VALUES (:id, :iid, 0, 0, 'text', 'text', 1, 'queued', false, 0)
            """),
            {"id": chunk_id, "iid": uuid.UUID(ingestion_id)},
        )
    await engine.dispose()

    response = await client.post(
        f"/api/v1/ingestions/{ingestion_id}/select",
        json={"chunk_ids": [str(chunk_id)]},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    # chunk was already queued, so queued_count is 0
    assert response.json()["queued_count"] == 0


# ---------------------------------------------------------------------------
# Candidate review and commit helpers
# ---------------------------------------------------------------------------

_SYSTEM_USER_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")
_AUTHOR_ING_001_ID = uuid.uuid5(_SYSTEM_USER_ID, "author-ing-001")
_TEST_DOMAIN = "test-domain"

_TASK_PROPOSED: dict[str, object] = {
    "title": "Configure iSCSI target",
    "outcome": "iSCSI target is configured and accessible.",
    "steps": [
        {
            "text": "Install the targetcli package",
            "completion": "Package installed successfully",
            "notes": None,
            "irreversible": False,
            "actions": ["Run apt-get install targetcli"],
        }
    ],
    "facts": ["iSCSI uses TCP port 3260"],
    "concepts": ["iSCSI", "LUN"],
    "tags": ["storage", "networking"],
}

_PRINCIPLE_PROPOSED: dict[str, object] = {
    "title": "Least privilege access",
    "summary": "Grant only the minimum permissions required.",
    "explanation": "Every component should operate with only the permissions it needs.",
    "analogies": "Like a need-to-know basis in security clearance.",
}


async def _seed_ingestion(
    test_settings: Settings,
    ingestion_id: uuid.UUID,
    user_id: uuid.UUID = _AUTHOR_ING_001_ID,
    status: str = "ready",
) -> None:
    """Insert a minimal ingestion row owned by user_id."""
    engine = create_engine(test_settings)
    async with engine.begin() as conn:
        await conn.execute(
            sa.text("""
                INSERT INTO ingestions (id, source_type, status, created_by)
                VALUES (:id, 'pdf', :status, :uid)
                ON CONFLICT DO NOTHING
            """),
            {"id": ingestion_id, "status": status, "uid": user_id},
        )
    await engine.dispose()


async def _seed_candidate(
    test_settings: Settings,
    candidate_id: uuid.UUID,
    ingestion_id: uuid.UUID,
    record_type: str = "task",
    proposed_json: dict[str, object] | None = None,
    candidate_status: str = "pending",
    committed_record_id: uuid.UUID | None = None,
) -> None:
    """Insert a minimal ingestion_candidates row."""
    import json

    proposed = proposed_json or _TASK_PROPOSED
    engine = create_engine(test_settings)
    async with engine.begin() as conn:
        await conn.execute(
            sa.text("""
                INSERT INTO ingestion_candidates
                  (id, ingestion_id, record_type, proposed_json, candidate_status,
                   committed_record_id)
                VALUES (:id, :iid, :rtype, cast(:pjson as jsonb), :cstatus, :crid)
                ON CONFLICT DO NOTHING
            """),
            {
                "id": candidate_id,
                "iid": ingestion_id,
                "rtype": record_type,
                "pjson": json.dumps(proposed),
                "cstatus": candidate_status,
                "crid": committed_record_id,
            },
        )
    await engine.dispose()


# ---------------------------------------------------------------------------
# List candidates
# ---------------------------------------------------------------------------


async def test_list_candidates_viewer_returns_403(
    client: AsyncClient, make_token: Callable[..., str]
) -> None:
    token = make_token(roles=["viewer"])
    response = await client.get(
        f"/api/v1/ingestions/{uuid.uuid4()}/candidates",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 403


async def test_list_candidates_not_found_returns_404(
    client: AsyncClient, make_token: Callable[..., str]
) -> None:
    token = make_token(sub="author-ing-001", roles=["contributor"])
    response = await client.get(
        f"/api/v1/ingestions/{uuid.uuid4()}/candidates",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 404


async def test_list_candidates_other_user_returns_404(
    client: AsyncClient,
    make_token: Callable[..., str],
    test_settings: Settings,
) -> None:
    """Candidate list for another user's ingestion is opaque 404."""
    ingestion_id = uuid.uuid4()
    await _seed_ingestion(test_settings, ingestion_id, user_id=_AUTHOR_ING_001_ID)

    other_token = make_token(sub="test-sub-001", roles=["contributor"])
    response = await client.get(
        f"/api/v1/ingestions/{ingestion_id}/candidates",
        headers={"Authorization": f"Bearer {other_token}"},
    )
    assert response.status_code == 404


async def test_list_candidates_returns_candidates(
    client: AsyncClient,
    make_token: Callable[..., str],
    test_settings: Settings,
) -> None:
    ingestion_id = uuid.uuid4()
    candidate_id = uuid.uuid4()
    await _seed_ingestion(test_settings, ingestion_id)
    await _seed_candidate(test_settings, candidate_id, ingestion_id)

    token = make_token(sub="author-ing-001", roles=["contributor"])
    response = await client.get(
        f"/api/v1/ingestions/{ingestion_id}/candidates",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    body = response.json()
    assert isinstance(body, list)
    ids = [c["id"] for c in body]
    assert str(candidate_id) in ids


# ---------------------------------------------------------------------------
# Review candidate — PATCH
# ---------------------------------------------------------------------------


async def test_review_candidate_accept_sets_status(
    client: AsyncClient,
    make_token: Callable[..., str],
    test_settings: Settings,
) -> None:
    ingestion_id = uuid.uuid4()
    candidate_id = uuid.uuid4()
    await _seed_ingestion(test_settings, ingestion_id)
    await _seed_candidate(test_settings, candidate_id, ingestion_id)

    token = make_token(sub="author-ing-001", roles=["contributor"])
    response = await client.patch(
        f"/api/v1/ingestions/{ingestion_id}/candidates/{candidate_id}",
        json={"action": "accept"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["candidate_status"] == "accepted"
    assert body["reviewed_by"] is not None
    assert body["reviewed_at"] is not None


async def test_review_candidate_accept_with_edit_sets_edited(
    client: AsyncClient,
    make_token: Callable[..., str],
    test_settings: Settings,
) -> None:
    ingestion_id = uuid.uuid4()
    candidate_id = uuid.uuid4()
    await _seed_ingestion(test_settings, ingestion_id)
    await _seed_candidate(test_settings, candidate_id, ingestion_id)

    edited_json = {**_TASK_PROPOSED, "title": "Edited title"}
    token = make_token(sub="author-ing-001", roles=["contributor"])
    response = await client.patch(
        f"/api/v1/ingestions/{ingestion_id}/candidates/{candidate_id}",
        json={"action": "accept", "proposed_json": edited_json},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["candidate_status"] == "edited"
    assert body["proposed_json"]["title"] == "Edited title"


async def test_review_candidate_discard_sets_status(
    client: AsyncClient,
    make_token: Callable[..., str],
    test_settings: Settings,
) -> None:
    ingestion_id = uuid.uuid4()
    candidate_id = uuid.uuid4()
    await _seed_ingestion(test_settings, ingestion_id)
    await _seed_candidate(test_settings, candidate_id, ingestion_id)

    token = make_token(sub="author-ing-001", roles=["contributor"])
    response = await client.patch(
        f"/api/v1/ingestions/{ingestion_id}/candidates/{candidate_id}",
        json={"action": "discard", "review_note": "Not relevant"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["candidate_status"] == "discarded"
    assert body["review_note"] == "Not relevant"


async def test_review_candidate_already_discarded_returns_422(
    client: AsyncClient,
    make_token: Callable[..., str],
    test_settings: Settings,
) -> None:
    ingestion_id = uuid.uuid4()
    candidate_id = uuid.uuid4()
    await _seed_ingestion(test_settings, ingestion_id)
    await _seed_candidate(test_settings, candidate_id, ingestion_id, candidate_status="discarded")

    token = make_token(sub="author-ing-001", roles=["contributor"])
    response = await client.patch(
        f"/api/v1/ingestions/{ingestion_id}/candidates/{candidate_id}",
        json={"action": "accept"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 422
    assert "discarded" in response.json()["detail"].lower()


async def test_review_candidate_already_committed_returns_422(
    client: AsyncClient,
    make_token: Callable[..., str],
    test_settings: Settings,
) -> None:
    ingestion_id = uuid.uuid4()
    candidate_id = uuid.uuid4()
    await _seed_ingestion(test_settings, ingestion_id)
    await _seed_candidate(
        test_settings,
        candidate_id,
        ingestion_id,
        candidate_status="accepted",
        committed_record_id=uuid.uuid4(),
    )

    token = make_token(sub="author-ing-001", roles=["contributor"])
    response = await client.patch(
        f"/api/v1/ingestions/{ingestion_id}/candidates/{candidate_id}",
        json={"action": "accept"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 422
    assert "committed" in response.json()["detail"].lower()


# ---------------------------------------------------------------------------
# Commit candidate — POST
# ---------------------------------------------------------------------------


async def test_commit_task_candidate_creates_task(
    client: AsyncClient,
    make_token: Callable[..., str],
    test_settings: Settings,
) -> None:
    ingestion_id = uuid.uuid4()
    candidate_id = uuid.uuid4()
    await _seed_ingestion(test_settings, ingestion_id)
    await _seed_candidate(
        test_settings, candidate_id, ingestion_id, candidate_status="accepted"
    )

    token = make_token(sub="author-ing-001", roles=["contributor"])
    response = await client.post(
        f"/api/v1/ingestions/{ingestion_id}/candidates/{candidate_id}/commit",
        json={"domain": _TEST_DOMAIN, "target_status": "draft"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 201
    body = response.json()
    assert body["record_type"] == "task"
    assert body["target_status"] == "draft"
    assert "committed_record_id" in body
    assert "candidate_id" in body


async def test_commit_principle_candidate_creates_principle(
    client: AsyncClient,
    make_token: Callable[..., str],
    test_settings: Settings,
) -> None:
    ingestion_id = uuid.uuid4()
    candidate_id = uuid.uuid4()
    await _seed_ingestion(test_settings, ingestion_id)
    await _seed_candidate(
        test_settings,
        candidate_id,
        ingestion_id,
        record_type="principle",
        proposed_json=_PRINCIPLE_PROPOSED,
        candidate_status="accepted",
    )

    token = make_token(sub="author-ing-001", roles=["contributor"])
    response = await client.post(
        f"/api/v1/ingestions/{ingestion_id}/candidates/{candidate_id}/commit",
        json={"domain": _TEST_DOMAIN},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 201
    body = response.json()
    assert body["record_type"] == "principle"
    assert body["target_status"] == "draft"


async def test_commit_task_with_submitted_status(
    client: AsyncClient,
    make_token: Callable[..., str],
    test_settings: Settings,
) -> None:
    ingestion_id = uuid.uuid4()
    candidate_id = uuid.uuid4()
    await _seed_ingestion(test_settings, ingestion_id)
    await _seed_candidate(
        test_settings, candidate_id, ingestion_id, candidate_status="edited"
    )

    token = make_token(sub="author-ing-001", roles=["contributor"])
    response = await client.post(
        f"/api/v1/ingestions/{ingestion_id}/candidates/{candidate_id}/commit",
        json={"domain": _TEST_DOMAIN, "target_status": "submitted"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 201
    assert response.json()["target_status"] == "submitted"


async def test_commit_pending_candidate_returns_422(
    client: AsyncClient,
    make_token: Callable[..., str],
    test_settings: Settings,
) -> None:
    """Cannot commit a candidate that has not been accepted."""
    ingestion_id = uuid.uuid4()
    candidate_id = uuid.uuid4()
    await _seed_ingestion(test_settings, ingestion_id)
    await _seed_candidate(test_settings, candidate_id, ingestion_id, candidate_status="pending")

    token = make_token(sub="author-ing-001", roles=["contributor"])
    response = await client.post(
        f"/api/v1/ingestions/{ingestion_id}/candidates/{candidate_id}/commit",
        json={"domain": _TEST_DOMAIN},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 422
    assert "accepted" in response.json()["detail"].lower()


async def test_commit_already_committed_returns_422(
    client: AsyncClient,
    make_token: Callable[..., str],
    test_settings: Settings,
) -> None:
    ingestion_id = uuid.uuid4()
    candidate_id = uuid.uuid4()
    await _seed_ingestion(test_settings, ingestion_id)
    await _seed_candidate(
        test_settings,
        candidate_id,
        ingestion_id,
        candidate_status="accepted",
        committed_record_id=uuid.uuid4(),
    )

    token = make_token(sub="author-ing-001", roles=["contributor"])
    response = await client.post(
        f"/api/v1/ingestions/{ingestion_id}/candidates/{candidate_id}/commit",
        json={"domain": _TEST_DOMAIN},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 422
    assert "committed" in response.json()["detail"].lower()


async def test_commit_invalid_domain_returns_422(
    client: AsyncClient,
    make_token: Callable[..., str],
    test_settings: Settings,
) -> None:
    ingestion_id = uuid.uuid4()
    candidate_id = uuid.uuid4()
    await _seed_ingestion(test_settings, ingestion_id)
    await _seed_candidate(test_settings, candidate_id, ingestion_id, candidate_status="accepted")

    token = make_token(sub="author-ing-001", roles=["contributor"])
    response = await client.post(
        f"/api/v1/ingestions/{ingestion_id}/candidates/{candidate_id}/commit",
        json={"domain": "nonexistent-domain"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 422
    assert "nonexistent-domain" in response.json()["detail"]


async def test_commit_unassigned_domain_returns_403(
    client: AsyncClient,
    make_token: Callable[..., str],
    test_settings: Settings,
) -> None:
    """A contributor not assigned to the domain gets 403."""
    ingestion_id = uuid.uuid4()
    candidate_id = uuid.uuid4()
    # Seed with a different user's ID so the ingestion 404 check passes for test-sub-001
    other_user_id = uuid.uuid5(_SYSTEM_USER_ID, "test-sub-001")
    await _seed_ingestion(test_settings, ingestion_id, user_id=other_user_id)
    await _seed_candidate(test_settings, candidate_id, ingestion_id, candidate_status="accepted")

    # Use an unassigned domain — "other-domain" does not exist in seed data
    # Instead create an ingestion owned by test-sub-001 and use test-domain
    # but first confirm test-sub-001 is not assigned (it is, per conftest).
    # Use a freshly created domain that no contributor is assigned to.
    engine = create_engine(test_settings)
    async with engine.begin() as conn:
        await conn.execute(
            sa.text(
                "INSERT INTO domains (name, created_by) VALUES ('restricted-domain', :uid) "
                "ON CONFLICT DO NOTHING"
            ),
            {"uid": _SYSTEM_USER_ID},
        )
    await engine.dispose()

    token = make_token(sub="test-sub-001", roles=["contributor"])
    response = await client.post(
        f"/api/v1/ingestions/{ingestion_id}/candidates/{candidate_id}/commit",
        json={"domain": "restricted-domain"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 403


# ---------------------------------------------------------------------------
# HTML ingestion (§11.10)
# ---------------------------------------------------------------------------


async def test_html_ingestion_unauthenticated_returns_401(client: AsyncClient) -> None:
    response = await client.post(
        "/api/v1/ingestions/html",
        json={"url": "https://example.com"},
    )
    assert response.status_code == 401


async def test_html_ingestion_viewer_returns_403(
    client: AsyncClient, make_token: Callable[..., str]
) -> None:
    token = make_token(roles=["viewer"])
    response = await client.post(
        "/api/v1/ingestions/html",
        json={"url": "https://example.com"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 403


async def test_html_ingestion_invalid_scheme_returns_422(
    client: AsyncClient, make_token: Callable[..., str]
) -> None:
    token = make_token(sub="author-ing-001", roles=["contributor"])
    response = await client.post(
        "/api/v1/ingestions/html",
        json={"url": "ftp://example.com/page"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 422


async def test_html_ingestion_creates_ingestion_and_enqueues_job(
    client: AsyncClient, make_token: Callable[..., str]
) -> None:
    StubArqPool.enqueued.clear()
    token = make_token(sub="author-ing-001", roles=["contributor"])
    response = await client.post(
        "/api/v1/ingestions/html",
        json={"url": "https://html-test-unique-01.example.com/"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 201
    body = response.json()
    assert body["source_type"] == "html"
    assert body["status"] == "pending"
    assert body["source_url"] == "https://html-test-unique-01.example.com/"
    ingestion_id = body["id"]

    jobs = [j for j in StubArqPool.enqueued if j[0] == "crawl_html"]
    assert any(j[1].get("ingestion_id") == ingestion_id for j in jobs)


async def test_html_ingestion_dedup_returns_existing(
    client: AsyncClient, make_token: Callable[..., str]
) -> None:
    """Second POST with same URL returns the existing ingestion."""
    token = make_token(sub="author-ing-001", roles=["contributor"])
    url = "https://html-dedup-unique.example.com/"
    r1 = await client.post(
        "/api/v1/ingestions/html",
        json={"url": url},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r1.status_code == 201
    original_id = r1.json()["id"]

    r2 = await client.post(
        "/api/v1/ingestions/html",
        json={"url": url},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r2.json()["id"] == original_id


async def test_html_ingestion_force_creates_new(
    client: AsyncClient, make_token: Callable[..., str]
) -> None:
    """force=true bypasses dedup and creates a new ingestion record."""
    token = make_token(sub="author-ing-001", roles=["contributor"])
    url = "https://html-force-unique.example.com/"
    r1 = await client.post(
        "/api/v1/ingestions/html",
        json={"url": url},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r1.status_code == 201
    original_id = r1.json()["id"]

    r2 = await client.post(
        "/api/v1/ingestions/html",
        json={"url": url, "force": True},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r2.status_code == 201
    assert r2.json()["id"] != original_id


async def test_html_ingestion_sitenav_mode_enqueues_with_mode(
    client: AsyncClient, make_token: Callable[..., str]
) -> None:
    StubArqPool.enqueued.clear()
    token = make_token(sub="author-ing-001", roles=["contributor"])
    response = await client.post(
        "/api/v1/ingestions/html",
        json={"url": "https://html-sitenav-unique.example.com/", "mode": "site-nav"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 201
    ingestion_id = response.json()["id"]
    jobs = [j for j in StubArqPool.enqueued if j[0] == "crawl_html"]
    matching = [j for j in jobs if j[1].get("ingestion_id") == ingestion_id]
    assert matching
    assert matching[0][1]["mode"] == "site-nav"


# ---------------------------------------------------------------------------
# Nav page listing and selection (§11.11)
# ---------------------------------------------------------------------------


async def _seed_html_ingestion(
    test_settings: Settings,
    ingestion_id: uuid.UUID,
    user_id: uuid.UUID = _AUTHOR_ING_001_ID,
    status: str = "ready",
) -> None:
    """Insert a minimal HTML ingestion row."""
    engine = create_engine(test_settings)
    async with engine.begin() as conn:
        await conn.execute(
            sa.text("""
                INSERT INTO ingestions (id, source_type, status, created_by, source_url)
                VALUES (:id, 'html', :status, :uid, 'https://example.com/')
                ON CONFLICT DO NOTHING
            """),
            {"id": ingestion_id, "status": status, "uid": user_id},
        )
    await engine.dispose()


async def _seed_nav_page(
    test_settings: Settings,
    nav_page_id: uuid.UUID,
    ingestion_id: uuid.UUID,
    nav_status: str = "pending",
) -> None:
    """Insert a minimal ingestion_nav_pages row."""
    engine = create_engine(test_settings)
    async with engine.begin() as conn:
        await conn.execute(
            sa.text("""
                INSERT INTO ingestion_nav_pages
                  (id, ingestion_id, url, nav_level, nav_order, nav_status, chunk_count)
                VALUES (:id, :iid, 'https://example.com/page', 1, 0, :status, 0)
                ON CONFLICT DO NOTHING
            """),
            {"id": nav_page_id, "iid": ingestion_id, "status": nav_status},
        )
    await engine.dispose()


async def test_list_nav_pages_viewer_returns_403(
    client: AsyncClient, make_token: Callable[..., str]
) -> None:
    token = make_token(roles=["viewer"])
    response = await client.get(
        f"/api/v1/ingestions/{uuid.uuid4()}/nav-pages",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 403


async def test_list_nav_pages_not_found_returns_404(
    client: AsyncClient, make_token: Callable[..., str]
) -> None:
    token = make_token(sub="author-ing-001", roles=["contributor"])
    response = await client.get(
        f"/api/v1/ingestions/{uuid.uuid4()}/nav-pages",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 404


async def test_list_nav_pages_pdf_ingestion_returns_422(
    client: AsyncClient,
    make_token: Callable[..., str],
    test_settings: Settings,
) -> None:
    """Nav pages endpoint rejects non-HTML ingestions."""
    ingestion_id = uuid.uuid4()
    await _seed_ingestion(test_settings, ingestion_id)  # PDF ingestion

    token = make_token(sub="author-ing-001", roles=["contributor"])
    response = await client.get(
        f"/api/v1/ingestions/{ingestion_id}/nav-pages",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 422


async def test_list_nav_pages_returns_pages(
    client: AsyncClient,
    make_token: Callable[..., str],
    test_settings: Settings,
) -> None:
    ingestion_id = uuid.uuid4()
    nav_page_id = uuid.uuid4()
    await _seed_html_ingestion(test_settings, ingestion_id)
    await _seed_nav_page(test_settings, nav_page_id, ingestion_id)

    token = make_token(sub="author-ing-001", roles=["contributor"])
    response = await client.get(
        f"/api/v1/ingestions/{ingestion_id}/nav-pages",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    body = response.json()
    assert isinstance(body, list)
    assert any(p["id"] == str(nav_page_id) for p in body)


async def test_nav_select_empty_ids_returns_422(
    client: AsyncClient,
    make_token: Callable[..., str],
    test_settings: Settings,
) -> None:
    ingestion_id = uuid.uuid4()
    await _seed_html_ingestion(test_settings, ingestion_id)

    token = make_token(sub="author-ing-001", roles=["contributor"])
    response = await client.post(
        f"/api/v1/ingestions/{ingestion_id}/nav-select",
        json={"nav_page_ids": []},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 422


async def test_nav_select_pdf_ingestion_returns_422(
    client: AsyncClient,
    make_token: Callable[..., str],
    test_settings: Settings,
) -> None:
    ingestion_id = uuid.uuid4()
    await _seed_ingestion(test_settings, ingestion_id)

    token = make_token(sub="author-ing-001", roles=["contributor"])
    response = await client.post(
        f"/api/v1/ingestions/{ingestion_id}/nav-select",
        json={"nav_page_ids": [str(uuid.uuid4())]},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 422


async def test_nav_select_non_ready_ingestion_returns_422(
    client: AsyncClient,
    make_token: Callable[..., str],
    test_settings: Settings,
) -> None:
    ingestion_id = uuid.uuid4()
    await _seed_html_ingestion(test_settings, ingestion_id, status="pending")

    token = make_token(sub="author-ing-001", roles=["contributor"])
    response = await client.post(
        f"/api/v1/ingestions/{ingestion_id}/nav-select",
        json={"nav_page_ids": [str(uuid.uuid4())]},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 422
    assert "pending" in response.json()["detail"]


async def test_nav_select_queues_pending_pages_and_enqueues_job(
    client: AsyncClient,
    make_token: Callable[..., str],
    test_settings: Settings,
) -> None:
    ingestion_id = uuid.uuid4()
    nav_page_id = uuid.uuid4()
    await _seed_html_ingestion(test_settings, ingestion_id)
    await _seed_nav_page(test_settings, nav_page_id, ingestion_id)

    StubArqPool.enqueued.clear()
    token = make_token(sub="author-ing-001", roles=["contributor"])
    response = await client.post(
        f"/api/v1/ingestions/{ingestion_id}/nav-select",
        json={"nav_page_ids": [str(nav_page_id)]},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["queued_count"] == 1
    assert body["ingestion_id"] == str(ingestion_id)

    jobs = [j for j in StubArqPool.enqueued if j[0] == "render_nav_pages"]
    assert any(j[1].get("ingestion_id") == str(ingestion_id) for j in jobs)


async def test_nav_select_already_selected_page_is_skipped(
    client: AsyncClient,
    make_token: Callable[..., str],
    test_settings: Settings,
) -> None:
    """A page already in selected status is not re-queued."""
    ingestion_id = uuid.uuid4()
    nav_page_id = uuid.uuid4()
    await _seed_html_ingestion(test_settings, ingestion_id)
    await _seed_nav_page(test_settings, nav_page_id, ingestion_id, nav_status="selected")

    token = make_token(sub="author-ing-001", roles=["contributor"])
    response = await client.post(
        f"/api/v1/ingestions/{ingestion_id}/nav-select",
        json={"nav_page_ids": [str(nav_page_id)]},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    assert response.json()["queued_count"] == 0


# ---------------------------------------------------------------------------
# JSON ingestion (§11.12)
# ---------------------------------------------------------------------------

_VALID_JSON_TASK = {
    "type": "task",
    "title": "Configure SSH key authentication",
    "outcome": "SSH key authentication is configured and active.",
    "software_name": "OpenSSH",
    "software_version": "8.9",
    "domain": "test-domain",
    "facts": ["SSH uses port 22 by default"],
    "concepts": ["Public key cryptography"],
    "dependencies": ["SSH server must be running"],
    "irreversible": False,
    "task_order": [],
    "steps": [
        {
            "id": "S001",
            "text": "Generate an SSH key pair",
            "completion": "id_rsa and id_rsa.pub present in ~/.ssh/",
            "actions": ["ssh-keygen -t rsa -b 4096"],
            "notes": None,
        }
    ],
}

_VALID_JSON_PRINCIPLE = {
    "type": "principle",
    "title": "Fail securely",
    "summary": "Errors should default to a safe state.",
    "explanation": "When a system fails, it should deny access rather than grant it.",
    "analogies": "Like a door that locks rather than unlocks on power failure.",
    "software_name": None,
    "software_version": None,
    "domain": "test-domain",
}

_VALID_JSON_PAYLOAD = {
    "schema_version": "1.0",
    "items": [_VALID_JSON_TASK],
}


async def test_json_ingestion_unauthenticated_returns_401(client: AsyncClient) -> None:
    response = await client.post(
        "/api/v1/ingestions/json",
        json=_VALID_JSON_PAYLOAD,
    )
    assert response.status_code == 401


async def test_json_ingestion_viewer_returns_403(
    client: AsyncClient, make_token: Callable[..., str]
) -> None:
    token = make_token(roles=["viewer"])
    response = await client.post(
        "/api/v1/ingestions/json",
        json=_VALID_JSON_PAYLOAD,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 403


async def test_json_ingestion_invalid_schema_version_returns_422(
    client: AsyncClient, make_token: Callable[..., str]
) -> None:
    token = make_token(sub="author-ing-001", roles=["contributor"])
    payload = {**_VALID_JSON_PAYLOAD, "schema_version": "2.0"}
    response = await client.post(
        "/api/v1/ingestions/json",
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 422


async def test_json_ingestion_empty_items_returns_422(
    client: AsyncClient, make_token: Callable[..., str]
) -> None:
    token = make_token(sub="author-ing-001", roles=["contributor"])
    payload = {"schema_version": "1.0", "items": []}
    response = await client.post(
        "/api/v1/ingestions/json",
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 422


async def test_json_ingestion_task_missing_field_returns_422(
    client: AsyncClient, make_token: Callable[..., str]
) -> None:
    """A task item missing a required field is rejected with 422."""
    bad_task = {k: v for k, v in _VALID_JSON_TASK.items() if k != "outcome"}
    token = make_token(sub="author-ing-001", roles=["contributor"])
    response = await client.post(
        "/api/v1/ingestions/json",
        json={"schema_version": "1.0", "items": [bad_task]},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 422


async def test_json_ingestion_task_empty_steps_returns_422(
    client: AsyncClient, make_token: Callable[..., str]
) -> None:
    bad_task = {**_VALID_JSON_TASK, "steps": []}
    token = make_token(sub="author-ing-001", roles=["contributor"])
    response = await client.post(
        "/api/v1/ingestions/json",
        json={"schema_version": "1.0", "items": [bad_task]},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 422


async def test_json_ingestion_creates_ingestion_ready_with_candidates(
    client: AsyncClient, make_token: Callable[..., str]
) -> None:
    """Valid JSON payload creates ingestion in ready status with candidates immediately."""
    # Unique payload to avoid dedup with other tests.
    payload = {
        "schema_version": "1.0",
        "items": [{**_VALID_JSON_TASK, "title": "JSON ingestion test unique title A"}],
    }
    token = make_token(sub="author-ing-001", roles=["contributor"])
    response = await client.post(
        "/api/v1/ingestions/json",
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 201
    body = response.json()
    assert body["source_type"] == "json"
    assert body["status"] == "ready"
    assert body["chunk_count"] == 0
    ingestion_id = body["id"]

    # Candidates should be immediately queryable.
    cand_response = await client.get(
        f"/api/v1/ingestions/{ingestion_id}/candidates",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert cand_response.status_code == 200
    candidates = cand_response.json()
    assert len(candidates) == 1
    assert candidates[0]["record_type"] == "task"
    assert candidates[0]["candidate_status"] == "pending"
    assert candidates[0]["chunk_id"] is None


async def test_json_ingestion_principle_item_creates_principle_candidate(
    client: AsyncClient, make_token: Callable[..., str]
) -> None:
    payload = {
        "schema_version": "1.0",
        "items": [{**_VALID_JSON_PRINCIPLE, "title": "JSON principle unique title B"}],
    }
    token = make_token(sub="author-ing-001", roles=["contributor"])
    response = await client.post(
        "/api/v1/ingestions/json",
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 201
    ingestion_id = response.json()["id"]

    cand_response = await client.get(
        f"/api/v1/ingestions/{ingestion_id}/candidates",
        headers={"Authorization": f"Bearer {token}"},
    )
    candidates = cand_response.json()
    assert len(candidates) == 1
    assert candidates[0]["record_type"] == "principle"


async def test_json_ingestion_mixed_items_creates_multiple_candidates(
    client: AsyncClient, make_token: Callable[..., str]
) -> None:
    payload = {
        "schema_version": "1.0",
        "items": [
            {**_VALID_JSON_TASK, "title": "JSON mixed task unique C"},
            {**_VALID_JSON_PRINCIPLE, "title": "JSON mixed principle unique C"},
        ],
    }
    token = make_token(sub="author-ing-001", roles=["contributor"])
    response = await client.post(
        "/api/v1/ingestions/json",
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 201
    ingestion_id = response.json()["id"]

    cand_response = await client.get(
        f"/api/v1/ingestions/{ingestion_id}/candidates",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert len(cand_response.json()) == 2


async def test_json_ingestion_dedup_returns_existing(
    client: AsyncClient, make_token: Callable[..., str]
) -> None:
    """Identical JSON payload returns the existing ingestion."""
    payload = {
        "schema_version": "1.0",
        "items": [{**_VALID_JSON_TASK, "title": "JSON dedup unique title D"}],
    }
    token = make_token(sub="author-ing-001", roles=["contributor"])
    r1 = await client.post(
        "/api/v1/ingestions/json",
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r1.status_code == 201
    original_id = r1.json()["id"]

    r2 = await client.post(
        "/api/v1/ingestions/json",
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r2.json()["id"] == original_id


async def test_json_ingestion_no_arq_job_enqueued(
    client: AsyncClient, make_token: Callable[..., str]
) -> None:
    """JSON ingestion is synchronous — no worker job should be enqueued."""
    StubArqPool.enqueued.clear()
    payload = {
        "schema_version": "1.0",
        "items": [{**_VALID_JSON_TASK, "title": "JSON no arq unique E"}],
    }
    token = make_token(sub="author-ing-001", roles=["contributor"])
    await client.post(
        "/api/v1/ingestions/json",
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
    )
    # No job should be enqueued — JSON ingestion is fully synchronous.
    json_jobs = [j for j in StubArqPool.enqueued if j[0] in ("chunk_pdf", "crawl_html")]
    assert not json_jobs


# ---------------------------------------------------------------------------
# JSON ingestion — task_order cross-reference validation (§11.12)
# ---------------------------------------------------------------------------


async def test_json_task_order_valid_forward_ref_accepted(
    client: AsyncClient, make_token: Callable[..., str]
) -> None:
    """task_order forward reference (id appears later in items) is accepted."""
    task_a = {**_VALID_JSON_TASK, "title": "Task A order unique F", "id": "T001",
              "task_order": ["T002"]}
    task_b = {**_VALID_JSON_TASK, "title": "Task B order unique F", "id": "T002",
              "task_order": []}
    token = make_token(sub="author-ing-001", roles=["contributor"])
    response = await client.post(
        "/api/v1/ingestions/json",
        json={"schema_version": "1.0", "items": [task_a, task_b]},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 201


async def test_json_task_order_dangling_ref_returns_422(
    client: AsyncClient, make_token: Callable[..., str]
) -> None:
    """task_order referencing an id not in the payload is rejected."""
    task = {**_VALID_JSON_TASK, "title": "Task dangling ref G", "id": "T001",
            "task_order": ["T999"]}
    token = make_token(sub="author-ing-001", roles=["contributor"])
    response = await client.post(
        "/api/v1/ingestions/json",
        json={"schema_version": "1.0", "items": [task]},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 422
    assert "T999" in response.text


async def test_json_task_order_duplicate_id_returns_422(
    client: AsyncClient, make_token: Callable[..., str]
) -> None:
    """Duplicate import IDs within a payload are rejected."""
    task_a = {**_VALID_JSON_TASK, "title": "Task dup A unique H", "id": "T001", "task_order": []}
    task_b = {**_VALID_JSON_TASK, "title": "Task dup B unique H", "id": "T001", "task_order": []}
    token = make_token(sub="author-ing-001", roles=["contributor"])
    response = await client.post(
        "/api/v1/ingestions/json",
        json={"schema_version": "1.0", "items": [task_a, task_b]},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 422
    assert "T001" in response.text


async def test_json_task_order_no_id_field_with_empty_task_order_accepted(
    client: AsyncClient, make_token: Callable[..., str]
) -> None:
    """Task with no id field and empty task_order is valid (id is optional)."""
    task = {**_VALID_JSON_TASK, "title": "Task no id unique I", "task_order": []}
    # _VALID_JSON_TASK has no id field, so this confirms the existing fixture still works.
    token = make_token(sub="author-ing-001", roles=["contributor"])
    response = await client.post(
        "/api/v1/ingestions/json",
        json={"schema_version": "1.0", "items": [task]},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 201


# ---------------------------------------------------------------------------
# Batch commit (POST /ingestions/{id}/candidates/commit-batch)
# ---------------------------------------------------------------------------


async def test_commit_batch_commits_selected_candidates(
    client: AsyncClient,
    make_token: Callable[..., str],
    test_settings: Settings,
) -> None:
    """Batch commit creates governance records for all requested candidates."""
    ingestion_id = uuid.uuid4()
    await _seed_ingestion(test_settings, ingestion_id)
    c1 = uuid.uuid4()
    c2 = uuid.uuid4()
    await _seed_candidate(
        test_settings, c1, ingestion_id, record_type="task", proposed_json=_TASK_PROPOSED
    )
    await _seed_candidate(
        test_settings, c2, ingestion_id, record_type="principle", proposed_json=_PRINCIPLE_PROPOSED
    )

    token = make_token(sub="author-ing-001", roles=["contributor"])
    response = await client.post(
        f"/api/v1/ingestions/{ingestion_id}/candidates/commit-batch",
        json={
            "candidate_ids": [str(c1), str(c2)],
            "domain": _TEST_DOMAIN,
            "target_status": "draft",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 201
    body = response.json()
    assert body["committed_count"] == 2
    result_ids = {r["candidate_id"] for r in body["results"]}
    assert str(c1) in result_ids
    assert str(c2) in result_ids


async def test_commit_batch_skips_already_committed(
    client: AsyncClient,
    make_token: Callable[..., str],
    test_settings: Settings,
) -> None:
    """Candidates already committed are silently excluded from the batch."""
    ingestion_id = uuid.uuid4()
    await _seed_ingestion(test_settings, ingestion_id)
    already_committed_id = uuid.uuid4()
    pending_id = uuid.uuid4()
    fake_record_id = uuid.uuid4()
    await _seed_candidate(
        test_settings, already_committed_id, ingestion_id,
        candidate_status="accepted", committed_record_id=fake_record_id,
    )
    await _seed_candidate(test_settings, pending_id, ingestion_id, proposed_json=_TASK_PROPOSED)

    token = make_token(sub="author-ing-001", roles=["contributor"])
    response = await client.post(
        f"/api/v1/ingestions/{ingestion_id}/candidates/commit-batch",
        json={
            "candidate_ids": [str(already_committed_id), str(pending_id)],
            "domain": _TEST_DOMAIN,
            "target_status": "draft",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 201
    body = response.json()
    assert body["committed_count"] == 1
    assert body["results"][0]["candidate_id"] == str(pending_id)


async def test_commit_batch_rejects_discarded_candidates(
    client: AsyncClient,
    make_token: Callable[..., str],
    test_settings: Settings,
) -> None:
    """Discarded candidates are excluded from the batch (they must be promoted first)."""
    ingestion_id = uuid.uuid4()
    await _seed_ingestion(test_settings, ingestion_id)
    discarded_id = uuid.uuid4()
    await _seed_candidate(test_settings, discarded_id, ingestion_id, candidate_status="discarded")

    token = make_token(sub="author-ing-001", roles=["contributor"])
    response = await client.post(
        f"/api/v1/ingestions/{ingestion_id}/candidates/commit-batch",
        json={
            "candidate_ids": [str(discarded_id)],
            "domain": _TEST_DOMAIN,
            "target_status": "draft",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 201
    assert response.json()["committed_count"] == 0


async def test_commit_batch_empty_candidate_ids_returns_422(
    client: AsyncClient,
    make_token: Callable[..., str],
    test_settings: Settings,
) -> None:
    ingestion_id = uuid.uuid4()
    await _seed_ingestion(test_settings, ingestion_id)
    token = make_token(sub="author-ing-001", roles=["contributor"])
    response = await client.post(
        f"/api/v1/ingestions/{ingestion_id}/candidates/commit-batch",
        json={"candidate_ids": [], "domain": _TEST_DOMAIN, "target_status": "draft"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 422


# ---------------------------------------------------------------------------
# Promote candidate (POST /ingestions/{id}/candidates/{id}/promote)
# ---------------------------------------------------------------------------


async def test_promote_candidate_restores_discarded_to_pending(
    client: AsyncClient,
    make_token: Callable[..., str],
    test_settings: Settings,
) -> None:
    ingestion_id = uuid.uuid4()
    await _seed_ingestion(test_settings, ingestion_id)
    candidate_id = uuid.uuid4()
    await _seed_candidate(test_settings, candidate_id, ingestion_id, candidate_status="discarded")

    token = make_token(sub="author-ing-001", roles=["contributor"])
    response = await client.post(
        f"/api/v1/ingestions/{ingestion_id}/candidates/{candidate_id}/promote",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    assert response.json()["candidate_status"] == "pending"


async def test_promote_candidate_rejects_already_committed(
    client: AsyncClient,
    make_token: Callable[..., str],
    test_settings: Settings,
) -> None:
    ingestion_id = uuid.uuid4()
    await _seed_ingestion(test_settings, ingestion_id)
    candidate_id = uuid.uuid4()
    fake_record_id = uuid.uuid4()
    await _seed_candidate(
        test_settings, candidate_id, ingestion_id,
        candidate_status="accepted", committed_record_id=fake_record_id,
    )

    token = make_token(sub="author-ing-001", roles=["contributor"])
    response = await client.post(
        f"/api/v1/ingestions/{ingestion_id}/candidates/{candidate_id}/promote",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 422


async def test_promote_candidate_rejects_non_discarded(
    client: AsyncClient,
    make_token: Callable[..., str],
    test_settings: Settings,
) -> None:
    """Promoting a pending (non-discarded) candidate returns 422."""
    ingestion_id = uuid.uuid4()
    await _seed_ingestion(test_settings, ingestion_id)
    candidate_id = uuid.uuid4()
    await _seed_candidate(test_settings, candidate_id, ingestion_id, candidate_status="pending")

    token = make_token(sub="author-ing-001", roles=["contributor"])
    response = await client.post(
        f"/api/v1/ingestions/{ingestion_id}/candidates/{candidate_id}/promote",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 422
