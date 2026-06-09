"""Tests for the audit log endpoint and audit event writes (§9.6, §5.1)."""

from collections.abc import Callable

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio

_BASE = "/api/v1/audit"
_KEYS_BASE = "/api/v1/admin/api-keys"


# ---------------------------------------------------------------------------
# Access control
# ---------------------------------------------------------------------------

async def test_audit_log_unauthenticated_returns_401(client: AsyncClient) -> None:
    response = await client.get(_BASE)
    assert response.status_code == 401


async def test_audit_log_viewer_returns_403(
    client: AsyncClient, make_token: Callable[..., str]
) -> None:
    token = make_token(roles=["viewer"])
    response = await client.get(_BASE, headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 403


async def test_audit_log_contributor_returns_403(
    client: AsyncClient, make_token: Callable[..., str]
) -> None:
    token = make_token(roles=["contributor"])
    response = await client.get(_BASE, headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 403


async def test_audit_log_admin_can_read(
    client: AsyncClient, make_token: Callable[..., str]
) -> None:
    token = make_token(roles=["admin"])
    response = await client.get(_BASE, headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    assert isinstance(response.json(), list)


async def test_audit_log_audit_role_can_read(
    client: AsyncClient, make_token: Callable[..., str]
) -> None:
    token = make_token(roles=["audit"])
    response = await client.get(_BASE, headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200


# ---------------------------------------------------------------------------
# Audit events written on API key create/revoke
# ---------------------------------------------------------------------------

async def test_api_key_create_writes_audit_event(
    client: AsyncClient, make_token: Callable[..., str]
) -> None:
    admin_token = make_token(roles=["admin"])
    headers = {"Authorization": f"Bearer {admin_token}"}

    audit_before = await client.get(_BASE, headers=headers)
    count_before = len(audit_before.json())

    await client.post(
        _KEYS_BASE,
        json={"name": "Audit Event Key", "role": "agent:orphan_detector"},
        headers=headers,
    )

    audit_after = await client.get(_BASE, headers=headers)
    events = audit_after.json()
    assert len(events) > count_before
    event_types = [e["event_type"] for e in events]
    assert "api_key_created" in event_types


async def test_api_key_revoke_writes_audit_event(
    client: AsyncClient, make_token: Callable[..., str]
) -> None:
    admin_token = make_token(roles=["admin"])
    headers = {"Authorization": f"Bearer {admin_token}"}

    create_resp = await client.post(
        _KEYS_BASE,
        json={"name": "Revoke Audit Key", "role": "agent:staleness_monitor"},
        headers=headers,
    )
    key_id = create_resp.json()["id"]

    audit_before = await client.get(_BASE, headers=headers)
    count_before = len(audit_before.json())

    await client.delete(f"{_KEYS_BASE}/{key_id}", headers=headers)

    audit_after = await client.get(_BASE, headers=headers)
    events = audit_after.json()
    assert len(events) > count_before
    event_types = [e["event_type"] for e in events]
    assert "api_key_revoked" in event_types


# ---------------------------------------------------------------------------
# Pagination
# ---------------------------------------------------------------------------

async def test_audit_log_respects_limit(
    client: AsyncClient, make_token: Callable[..., str]
) -> None:
    token = make_token(roles=["admin"])
    headers = {"Authorization": f"Bearer {token}"}
    response = await client.get(_BASE, params={"limit": 1}, headers=headers)
    assert response.status_code == 200
    assert len(response.json()) <= 1
