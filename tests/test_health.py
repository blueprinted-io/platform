"""Tests for GET /healthz."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_healthz_returns_200(client: AsyncClient) -> None:
    response = await client.get("/healthz")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_healthz_response_shape(client: AsyncClient) -> None:
    response = await client.get("/healthz")
    body = response.json()
    assert "status" in body
    assert body["status"] in ("ok", "unhealthy")
