"""Tests for the Relationships API. §9.4, §23.9

The relationships table exists as infrastructure in v1.
All writes are rejected with HTTP 422. Reads are open to all authenticated roles.
"""

from collections.abc import Callable

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


# ---------------------------------------------------------------------------
# GET /api/v1/relationships
# ---------------------------------------------------------------------------

async def test_list_relationships_unauthenticated_returns_401(client: AsyncClient) -> None:
    response = await client.get("/api/v1/relationships")
    assert response.status_code == 401


async def test_list_relationships_viewer_returns_empty_list(
    client: AsyncClient, make_token: Callable[..., str]
) -> None:
    token = make_token(roles=["viewer"])
    headers = {"Authorization": f"Bearer {token}"}
    response = await client.get("/api/v1/relationships", headers=headers)
    assert response.status_code == 200
    assert response.json() == []


async def test_list_relationships_contributor_returns_empty_list(
    client: AsyncClient, make_token: Callable[..., str]
) -> None:
    token = make_token(roles=["contributor"])
    headers = {"Authorization": f"Bearer {token}"}
    response = await client.get("/api/v1/relationships", headers=headers)
    assert response.status_code == 200
    assert response.json() == []


# ---------------------------------------------------------------------------
# POST /api/v1/relationships — all writes rejected in v1
# ---------------------------------------------------------------------------

async def test_create_relationship_returns_422(
    client: AsyncClient, make_token: Callable[..., str]
) -> None:
    token = make_token(roles=["contributor"])
    response = await client.post(
        "/api/v1/relationships",
        json={},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 422
