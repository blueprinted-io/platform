"""Tests for the §6 pagination convention (v4.11) on governed record lists.

Covers:
  - Page envelope shape {items, total, limit, offset} on /tasks, /workflows, /principles
  - limit/offset query param bounds (limit 1..100, offset >= 0)
  - total counts distinct records, latest version only
  - offset past the end returns an empty page with total intact
"""

import uuid
from collections.abc import Callable
from typing import Any

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from api.config import Settings
from api.database import create_engine
from api.models.task import Task
from tests.factories import task_payload

pytestmark = pytest.mark.asyncio

_SYSTEM_USER_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")


async def _walk_all_pages(
    client: AsyncClient, path: str, headers: dict[str, str]
) -> tuple[list[dict[str, Any]], int]:
    """Fetch every page of a list endpoint, returning (all items, reported total)."""
    items: list[dict[str, Any]] = []
    offset = 0
    while True:
        resp = await client.get(
            path, params={"limit": 100, "offset": offset}, headers=headers
        )
        assert resp.status_code == 200
        body = resp.json()
        items.extend(body["items"])
        offset += 100
        if offset >= body["total"]:
            return items, body["total"]


# ---------------------------------------------------------------------------
# Envelope shape and defaults
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("path", ["/api/v1/tasks", "/api/v1/workflows", "/api/v1/principles"])
async def test_list_returns_page_envelope_with_defaults(
    client: AsyncClient, make_token: Callable[..., str], path: str
) -> None:
    token = make_token(roles=["viewer"])
    resp = await client.get(path, headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    body = resp.json()
    assert set(body.keys()) == {"items", "total", "limit", "offset"}
    assert body["limit"] == 20
    assert body["offset"] == 0
    assert isinstance(body["items"], list)
    assert len(body["items"]) <= 20
    assert body["total"] >= len(body["items"]) or body["offset"] > 0


async def test_list_tasks_respects_limit(
    client: AsyncClient, make_token: Callable[..., str]
) -> None:
    token = make_token(roles=["contributor"])
    headers = {"Authorization": f"Bearer {token}"}
    for _ in range(3):
        created = await client.post("/api/v1/tasks", json=task_payload(), headers=headers)
        assert created.status_code == 201

    resp = await client.get("/api/v1/tasks", params={"limit": 2}, headers=headers)
    assert resp.status_code == 200
    body = resp.json()
    assert len(body["items"]) == 2
    assert body["limit"] == 2
    assert body["total"] >= 3


# ---------------------------------------------------------------------------
# Query param bounds
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("path", ["/api/v1/tasks", "/api/v1/workflows", "/api/v1/principles"])
@pytest.mark.parametrize(
    "params", [{"limit": 0}, {"limit": 101}, {"limit": -5}, {"offset": -1}]
)
async def test_list_rejects_out_of_bounds_params(
    client: AsyncClient,
    make_token: Callable[..., str],
    path: str,
    params: dict[str, int],
) -> None:
    token = make_token(roles=["viewer"])
    resp = await client.get(path, params=params, headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# Latest-version-only and total correctness
# ---------------------------------------------------------------------------

async def test_list_tasks_returns_latest_version_only_and_total_counts_records(
    client: AsyncClient, make_token: Callable[..., str], test_settings: Settings
) -> None:
    token = make_token(roles=["contributor"])
    headers = {"Authorization": f"Bearer {token}"}

    created = await client.post("/api/v1/tasks", json=task_payload(), headers=headers)
    assert created.status_code == 201
    record_id = created.json()["record_id"]

    # Insert a second version of the same record directly — the API only
    # produces new versions via the full review lifecycle.
    engine = create_engine(test_settings)
    try:
        async with AsyncSession(engine) as session:
            session.add(
                Task(
                    record_id=uuid.UUID(record_id),
                    version=2,
                    title="Rotate a PostgreSQL superuser password (v2)",
                    outcome="Updated outcome.",
                    domain="test-domain",
                    created_by=_SYSTEM_USER_ID,
                    updated_by=_SYSTEM_USER_ID,
                )
            )
            await session.commit()
    finally:
        await engine.dispose()

    items, total = await _walk_all_pages(client, "/api/v1/tasks", headers)

    matching = [t for t in items if t["record_id"] == record_id]
    assert len(matching) == 1, "each record must appear exactly once across all pages"
    assert matching[0]["version"] == 2, "only the latest version must be listed"

    record_ids = [t["record_id"] for t in items]
    assert len(record_ids) == len(set(record_ids)), "no record may appear on two pages"
    assert total == len(items), "total must equal the number of distinct records"


async def test_list_tasks_offset_past_end_returns_empty_page(
    client: AsyncClient, make_token: Callable[..., str]
) -> None:
    token = make_token(roles=["viewer"])
    headers = {"Authorization": f"Bearer {token}"}
    first = await client.get("/api/v1/tasks", headers=headers)
    total = first.json()["total"]

    resp = await client.get(
        "/api/v1/tasks", params={"offset": total + 50}, headers=headers
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["items"] == []
    assert body["total"] == total
    assert body["offset"] == total + 50
