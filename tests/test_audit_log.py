"""Tests for the audit log endpoint and audit event writes (§9.6, §5.1)."""

import uuid
from collections.abc import Callable

import pytest
from httpx import AsyncClient

from tests.factories import task_payload

pytestmark = pytest.mark.asyncio

_SYSTEM_USER_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")

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


# ---------------------------------------------------------------------------
# Lifecycle audit events — record_confirmed
# ---------------------------------------------------------------------------

async def test_record_confirmed_writes_audit_event(
    client: AsyncClient, make_token: Callable[..., str]
) -> None:
    author_token = make_token(sub="audit-author-conf-001", roles=["admin"])
    reviewer_token = make_token(sub="audit-reviewer-conf-001", roles=["admin"])
    admin_headers = {"Authorization": f"Bearer {author_token}"}
    reviewer_headers = {"Authorization": f"Bearer {reviewer_token}"}

    task_id = (
        await client.post("/api/v1/tasks", json=task_payload(), headers=admin_headers)
    ).json()["id"]
    await client.post(f"/api/v1/tasks/{task_id}/submit", headers=admin_headers)

    before = len((await client.get(_BASE, headers=admin_headers)).json())
    await client.post(f"/api/v1/tasks/{task_id}/confirm", headers=reviewer_headers)

    events = (await client.get(_BASE, headers=admin_headers)).json()
    assert len(events) > before
    assert "record_confirmed" in [e["event_type"] for e in events]


async def test_break_glass_confirm_writes_audit_event(
    client: AsyncClient, make_token: Callable[..., str]
) -> None:
    """Admin self-confirming their own record must produce a break_glass_confirm event."""
    admin_token = make_token(sub="audit-bg-admin-001", roles=["admin"])
    headers = {"Authorization": f"Bearer {admin_token}"}

    task_id = (
        await client.post("/api/v1/tasks", json=task_payload(), headers=headers)
    ).json()["id"]
    await client.post(f"/api/v1/tasks/{task_id}/submit", headers=headers)

    before = len((await client.get(_BASE, headers=headers)).json())
    await client.post(
        f"/api/v1/tasks/{task_id}/confirm",
        json={"justification": "Break-glass: sole domain expert unavailable."},
        headers=headers,
    )

    events = (await client.get(_BASE, headers=headers)).json()
    assert len(events) > before
    assert "break_glass_confirm" in [e["event_type"] for e in events]


# ---------------------------------------------------------------------------
# Lifecycle audit events — record_returned
# ---------------------------------------------------------------------------

async def test_record_returned_writes_audit_event(
    client: AsyncClient, make_token: Callable[..., str]
) -> None:
    author_token = make_token(sub="audit-author-ret-001", roles=["admin"])
    reviewer_token = make_token(sub="audit-reviewer-ret-001", roles=["admin"])
    headers = {"Authorization": f"Bearer {author_token}"}
    reviewer_headers = {"Authorization": f"Bearer {reviewer_token}"}

    task_id = (
        await client.post("/api/v1/tasks", json=task_payload(), headers=headers)
    ).json()["id"]
    await client.post(f"/api/v1/tasks/{task_id}/submit", headers=headers)

    before = len((await client.get(_BASE, headers=headers)).json())
    resp = await client.post(
        f"/api/v1/tasks/{task_id}/return",
        json={"note": "Missing completion criteria.", "severity": "warning"},
        headers=reviewer_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["return_severity"] == "warning"

    events = (await client.get(_BASE, headers=headers)).json()
    assert len(events) > before
    assert "record_returned" in [e["event_type"] for e in events]


# ---------------------------------------------------------------------------
# Lifecycle audit events — record_deprecated / record_retired
# ---------------------------------------------------------------------------

async def _confirmed_task_id(client: AsyncClient, author_headers: dict, reviewer_headers: dict) -> str:
    """Helper: create, submit, and confirm a task; return its id."""
    task_id = (
        await client.post("/api/v1/tasks", json=task_payload(), headers=author_headers)
    ).json()["id"]
    await client.post(f"/api/v1/tasks/{task_id}/submit", headers=author_headers)
    await client.post(
        f"/api/v1/tasks/{task_id}/confirm",
        json={"justification": "Audit test confirm."},
        headers=reviewer_headers,
    )
    return task_id


async def test_record_deprecated_writes_audit_event(
    client: AsyncClient, make_token: Callable[..., str]
) -> None:
    admin_token = make_token(sub="audit-dep-admin-001", roles=["admin"])
    headers = {"Authorization": f"Bearer {admin_token}"}

    task_id = await _confirmed_task_id(client, headers, headers)

    before = len((await client.get(_BASE, headers=headers)).json())
    resp = await client.post(f"/api/v1/tasks/{task_id}/deprecate", headers=headers)
    assert resp.status_code == 200

    events = (await client.get(_BASE, headers=headers)).json()
    assert len(events) > before
    assert "record_deprecated" in [e["event_type"] for e in events]


async def test_record_retired_writes_audit_event(
    client: AsyncClient, make_token: Callable[..., str]
) -> None:
    admin_token = make_token(sub="audit-ret-admin-001", roles=["admin"])
    headers = {"Authorization": f"Bearer {admin_token}"}

    task_id = await _confirmed_task_id(client, headers, headers)

    before = len((await client.get(_BASE, headers=headers)).json())
    resp = await client.post(f"/api/v1/tasks/{task_id}/retire", headers=headers)
    assert resp.status_code == 200

    events = (await client.get(_BASE, headers=headers)).json()
    assert len(events) > before
    assert "record_retired" in [e["event_type"] for e in events]


# ---------------------------------------------------------------------------
# Admin audit events — domain_created / user_domains_updated
# ---------------------------------------------------------------------------

async def test_domain_created_writes_audit_event(
    client: AsyncClient, make_token: Callable[..., str]
) -> None:
    admin_token = make_token(roles=["admin"])
    headers = {"Authorization": f"Bearer {admin_token}"}
    domain_name = f"audit-test-domain-{uuid.uuid4().hex[:8]}"

    before = len((await client.get(_BASE, headers=headers)).json())
    resp = await client.post("/api/v1/admin/domains", json={"name": domain_name}, headers=headers)
    assert resp.status_code == 201

    events = (await client.get(_BASE, headers=headers)).json()
    assert len(events) > before
    domain_events = [e for e in events if e["event_type"] == "domain_created"]
    assert any(e["detail"]["domain"] == domain_name for e in domain_events)


async def test_user_domains_updated_writes_audit_event(
    client: AsyncClient, make_token: Callable[..., str]
) -> None:
    admin_token = make_token(roles=["admin"])
    headers = {"Authorization": f"Bearer {admin_token}"}
    target_uid = uuid.uuid5(_SYSTEM_USER_ID, "test-sub-001")

    before = len((await client.get(_BASE, headers=headers)).json())
    resp = await client.put(
        f"/api/v1/admin/users/{target_uid}/domains",
        json={"domains": ["test-domain"]},
        headers=headers,
    )
    assert resp.status_code == 200

    events = (await client.get(_BASE, headers=headers)).json()
    assert len(events) > before
    assert "user_domains_updated" in [e["event_type"] for e in events]
