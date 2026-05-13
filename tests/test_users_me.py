"""Tests for GET /api/v1/users/me."""

from collections.abc import Callable

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_me_unauthenticated_returns_401(client: AsyncClient) -> None:
    response = await client.get("/api/v1/users/me")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_me_invalid_token_returns_401(client: AsyncClient) -> None:
    response = await client.get(
        "/api/v1/users/me",
        headers={"Authorization": "Bearer not.a.valid.token"},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_me_returns_user_profile(
    client: AsyncClient,
    make_token: Callable[..., str],
) -> None:
    token = make_token(
        sub="integration-user-001",
        email="integration@example.com",
        name="Integration User",
        roles=["contributor"],
    )
    response = await client.get(
        "/api/v1/users/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["sub"] == "integration-user-001"
    assert body["email"] == "integration@example.com"
    assert body["display_name"] == "Integration User"
    assert "contributor" in body["roles"]
    assert body["is_active"] is True


@pytest.mark.asyncio
async def test_me_creates_user_on_first_call(
    client: AsyncClient,
    make_token: Callable[..., str],
) -> None:
    token = make_token(sub="new-user-999", email="new@example.com")
    response = await client.get(
        "/api/v1/users/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    assert response.json()["sub"] == "new-user-999"


@pytest.mark.asyncio
async def test_me_syncs_updated_email(
    client: AsyncClient,
    make_token: Callable[..., str],
) -> None:
    sub = "sync-email-user-001"
    # First call — establish the user
    token_v1 = make_token(sub=sub, email="original@example.com")
    r1 = await client.get(
        "/api/v1/users/me", headers={"Authorization": f"Bearer {token_v1}"}
    )
    assert r1.status_code == 200
    assert r1.json()["email"] == "original@example.com"

    # Second call with updated email in token — should sync
    token_v2 = make_token(sub=sub, email="updated@example.com")
    r2 = await client.get(
        "/api/v1/users/me", headers={"Authorization": f"Bearer {token_v2}"}
    )
    assert r2.status_code == 200
    assert r2.json()["email"] == "updated@example.com"


@pytest.mark.asyncio
async def test_me_response_has_required_fields(
    client: AsyncClient,
    make_token: Callable[..., str],
) -> None:
    token = make_token()
    response = await client.get(
        "/api/v1/users/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    body = response.json()
    expected_fields = (
        "id", "sub", "email", "display_name", "roles", "is_active", "created_at", "updated_at"
    )
    for field in expected_fields:
        assert field in body, f"Missing field: {field}"
