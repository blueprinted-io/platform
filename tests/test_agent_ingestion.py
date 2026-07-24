"""Tests for the ingestion producer agent (§5.2, §11) — Sprint 15.

An agent:ingestion_agent credential may drive the ingestion pipeline end to end
(create ingestion, commit candidates to submitted) so machine-drafted content
lands in the human review queue — while the no-machine-can-confirm invariant
(§5.3, §10.2) stays intact.
"""

from collections.abc import Callable
from typing import Any

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio

_KEYS = "/api/v1/admin/api-keys"
_ING = "/api/v1/ingestions"
_TEST_DOMAIN = "test-domain"


async def _create_agent_key(
    client: AsyncClient, make_token: Callable[..., str], role: str
) -> str:
    """Admin creates an API key with the given agent role; return the raw bp_ key."""
    admin = make_token(roles=["admin"])
    resp = await client.post(
        _KEYS,
        json={"name": f"key-{role}", "role": role},
        headers={"Authorization": f"Bearer {admin}"},
    )
    assert resp.status_code == 201, resp.text
    return str(resp.json()["raw_key"])


def _json_payload(marker: str) -> dict[str, Any]:
    """Minimal valid §11.12 JSON import with one task.

    `marker` makes the payload unique so the SHA-256 dedup in create_json_ingestion
    does not collide across tests sharing the session-scoped test database.
    """
    return {
        "schema_version": "1.0",
        "items": [
            {
                "type": "task",
                "id": "t1",
                "title": f"Rotate the signing key ({marker})",
                "outcome": "The signing key is rotated and the old key revoked",
                "software_name": "vault",
                "software_version": "1.15",
                "domain": _TEST_DOMAIN,
                "facts": ["Keys expire after 90 days"],
                "concepts": ["key rotation"],
                "dependencies": [],
                "irreversible": False,
                "task_order": [],
                "steps": [
                    {
                        "id": "s1",
                        "text": "Generate a new key",
                        "completion": "The new key appears in the keyring",
                        "actions": ["Run vault operator generate-root"],
                        "notes": None,
                    }
                ],
            }
        ],
    }


async def _ingest_one_candidate(
    client: AsyncClient, headers: dict[str, str], marker: str
) -> tuple[str, str]:
    """Agent creates a JSON ingestion and returns (ingestion_id, candidate_id)."""
    resp = await client.post(f"{_ING}/json", json=_json_payload(marker), headers=headers)
    assert resp.status_code == 201, resp.text
    ingestion_id = resp.json()["id"]

    resp = await client.get(f"{_ING}/{ingestion_id}/candidates", headers=headers)
    assert resp.status_code == 200, resp.text
    candidates = resp.json()
    assert len(candidates) == 1
    return ingestion_id, candidates[0]["id"]


async def test_ingestion_agent_role_is_creatable(
    client: AsyncClient, make_token: Callable[..., str]
) -> None:
    raw = await _create_agent_key(client, make_token, "agent:ingestion_agent")
    assert raw.startswith("bp_")


async def test_ingestion_agent_can_ingest_and_submit_to_review_queue(
    client: AsyncClient, make_token: Callable[..., str]
) -> None:
    raw = await _create_agent_key(client, make_token, "agent:ingestion_agent")
    headers = {"Authorization": f"Bearer {raw}"}

    ingestion_id, candidate_id = await _ingest_one_candidate(client, headers, "review-queue")

    resp = await client.post(
        f"{_ING}/{ingestion_id}/candidates/commit-batch",
        json={
            "candidate_ids": [candidate_id],
            "domain": _TEST_DOMAIN,
            "target_status": "submitted",
        },
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["committed_count"] == 1
    record_id = body["results"][0]["committed_record_id"]

    # The committed record is submitted — i.e. it has reached the review queue.
    admin = make_token(roles=["admin"])
    resp = await client.get(
        f"/api/v1/tasks/{record_id}", headers={"Authorization": f"Bearer {admin}"}
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["status"] == "submitted"


async def test_ingestion_agent_commits_cross_domain_without_assignment(
    client: AsyncClient, make_token: Callable[..., str]
) -> None:
    """The agent holds no domain assignment yet commits into test-domain (§7.3 waiver)."""
    raw = await _create_agent_key(client, make_token, "agent:ingestion_agent")
    headers = {"Authorization": f"Bearer {raw}"}

    ingestion_id, candidate_id = await _ingest_one_candidate(client, headers, "cross-domain")

    resp = await client.post(
        f"{_ING}/{ingestion_id}/candidates/commit-batch",
        json={
            "candidate_ids": [candidate_id],
            "domain": _TEST_DOMAIN,
            "target_status": "draft",
        },
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    assert resp.json()["committed_count"] == 1


async def test_ingestion_agent_cannot_confirm(
    client: AsyncClient, make_token: Callable[..., str]
) -> None:
    """The machine may draft and submit, but never confirm (§5.3, §10.2)."""
    raw = await _create_agent_key(client, make_token, "agent:ingestion_agent")
    headers = {"Authorization": f"Bearer {raw}"}

    ingestion_id, candidate_id = await _ingest_one_candidate(client, headers, "no-confirm")
    commit = await client.post(
        f"{_ING}/{ingestion_id}/candidates/commit-batch",
        json={
            "candidate_ids": [candidate_id],
            "domain": _TEST_DOMAIN,
            "target_status": "submitted",
        },
        headers=headers,
    )
    record_id = commit.json()["results"][0]["committed_record_id"]

    resp = await client.post(f"/api/v1/review/tasks/{record_id}/confirm", headers=headers)
    assert resp.status_code == 403, resp.text


async def test_consumer_agent_cannot_ingest(
    client: AsyncClient, make_token: Callable[..., str]
) -> None:
    """Only the producer role may ingest — consumer agent roles are 403."""
    raw = await _create_agent_key(client, make_token, "agent:workflow_consumer")
    headers = {"Authorization": f"Bearer {raw}"}
    resp = await client.post(f"{_ING}/json", json=_json_payload("consumer"), headers=headers)
    assert resp.status_code == 403, resp.text
