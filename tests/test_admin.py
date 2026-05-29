"""Tests for the Admin API (§23.11).

Spec refs:
  §23.11  Admin endpoints — settings, domains, user-domain assignments, health

All endpoints require the admin role; non-admin callers get 403.
"""

import uuid
from collections.abc import Callable

import pytest
import respx
from httpx import AsyncClient, Response

pytestmark = pytest.mark.asyncio

_ADMIN_SUB = "admin-001"
_VIEWER_SUB = "viewer-admin-test-001"



def _admin_headers(make_token: Callable[..., str]) -> dict[str, str]:
    return {"Authorization": f"Bearer {make_token(sub=_ADMIN_SUB, roles=['admin'])}"}


def _viewer_headers(make_token: Callable[..., str]) -> dict[str, str]:
    return {"Authorization": f"Bearer {make_token(sub=_VIEWER_SUB, roles=['viewer'])}"}


# ---------------------------------------------------------------------------
# GET /admin/health
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_health_unauthenticated_returns_401(client: AsyncClient) -> None:
    response = await client.get("/api/v1/admin/health")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_health_viewer_returns_403(
    client: AsyncClient, make_token: Callable[..., str]
) -> None:
    response = await client.get("/api/v1/admin/health", headers=_viewer_headers(make_token))
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_health_admin_returns_ok(
    client: AsyncClient, make_token: Callable[..., str]
) -> None:
    response = await client.get("/api/v1/admin/health", headers=_admin_headers(make_token))
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["db_ok"] is True
    assert "migration_head" in data
    assert "undelivered_notification_errors" in data


# ---------------------------------------------------------------------------
# GET /admin/settings
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_list_settings_unauthenticated_returns_401(client: AsyncClient) -> None:
    response = await client.get("/api/v1/admin/settings")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_list_settings_viewer_returns_403(
    client: AsyncClient, make_token: Callable[..., str]
) -> None:
    response = await client.get("/api/v1/admin/settings", headers=_viewer_headers(make_token))
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_list_settings_admin_returns_list(
    client: AsyncClient, make_token: Callable[..., str]
) -> None:
    response = await client.get("/api/v1/admin/settings", headers=_admin_headers(make_token))
    assert response.status_code == 200
    assert isinstance(response.json(), list)


# ---------------------------------------------------------------------------
# PATCH /admin/settings
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_patch_settings_unauthenticated_returns_401(client: AsyncClient) -> None:
    response = await client.patch(
        "/api/v1/admin/settings", json={"settings": {"llm_base_url": {"value": "http://x"}}}
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_patch_settings_viewer_returns_403(
    client: AsyncClient, make_token: Callable[..., str]
) -> None:
    response = await client.patch(
        "/api/v1/admin/settings",
        json={"settings": {"llm_base_url": {"value": "http://x"}}},
        headers=_viewer_headers(make_token),
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_patch_settings_upserts_setting(
    client: AsyncClient, make_token: Callable[..., str]
) -> None:
    response = await client.patch(
        "/api/v1/admin/settings",
        json={"settings": {"test_key_admin": {"value": "hello", "encrypted": False}}},
        headers=_admin_headers(make_token),
    )
    assert response.status_code == 200
    data = response.json()
    keys = [s["key"] for s in data]
    assert "test_key_admin" in keys
    match = next(s for s in data if s["key"] == "test_key_admin")
    assert match["value"] == "hello"
    assert match["encrypted"] is False


@pytest.mark.asyncio
async def test_patch_settings_encrypted_masks_value(
    client: AsyncClient, make_token: Callable[..., str]
) -> None:
    await client.patch(
        "/api/v1/admin/settings",
        json={"settings": {"secret_key_admin": {"value": "s3cret", "encrypted": True}}},
        headers=_admin_headers(make_token),
    )
    response = await client.get("/api/v1/admin/settings", headers=_admin_headers(make_token))
    data = response.json()
    match = next((s for s in data if s["key"] == "secret_key_admin"), None)
    assert match is not None
    assert match["value"] is None
    assert match["encrypted"] is True


# ---------------------------------------------------------------------------
# POST /admin/settings/test-connection
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_test_connection_unauthenticated_returns_401(client: AsyncClient) -> None:
    response = await client.post(
        "/api/v1/admin/settings/test-connection",
        json={"base_url": "http://llm.test"},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_test_connection_viewer_returns_403(
    client: AsyncClient, make_token: Callable[..., str]
) -> None:
    response = await client.post(
        "/api/v1/admin/settings/test-connection",
        json={"base_url": "http://llm.test"},
        headers=_viewer_headers(make_token),
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_test_connection_missing_base_url_returns_not_ok(
    client: AsyncClient, make_token: Callable[..., str]
) -> None:
    response = await client.post(
        "/api/v1/admin/settings/test-connection",
        json={"base_url": ""},
        headers=_admin_headers(make_token),
    )
    assert response.status_code == 200
    data = response.json()
    assert data["ok"] is False
    assert data["error"] is not None


@pytest.mark.asyncio
@respx.mock
async def test_test_connection_returns_model_ids(
    client: AsyncClient, make_token: Callable[..., str]
) -> None:
    respx.get("http://llm.test/models").mock(
        return_value=Response(
            200,
            json={"data": [{"id": "model-a"}, {"id": "model-b"}]},
        )
    )
    response = await client.post(
        "/api/v1/admin/settings/test-connection",
        json={"base_url": "http://llm.test"},
        headers=_admin_headers(make_token),
    )
    assert response.status_code == 200
    data = response.json()
    assert data["ok"] is True
    assert data["models"] == ["model-a", "model-b"]


@pytest.mark.asyncio
@respx.mock
async def test_test_connection_401_from_server_returns_not_ok(
    client: AsyncClient, make_token: Callable[..., str]
) -> None:
    respx.get("http://llm.test/models").mock(return_value=Response(401))
    response = await client.post(
        "/api/v1/admin/settings/test-connection",
        json={"base_url": "http://llm.test"},
        headers=_admin_headers(make_token),
    )
    assert response.status_code == 200
    data = response.json()
    assert data["ok"] is False
    assert "401" in data["error"]


@pytest.mark.asyncio
@respx.mock
async def test_test_connection_404_means_reachable(
    client: AsyncClient, make_token: Callable[..., str]
) -> None:
    respx.get("http://llm.test/models").mock(return_value=Response(404))
    response = await client.post(
        "/api/v1/admin/settings/test-connection",
        json={"base_url": "http://llm.test"},
        headers=_admin_headers(make_token),
    )
    assert response.status_code == 200
    data = response.json()
    assert data["ok"] is True
    assert data["models"] == []


# ---------------------------------------------------------------------------
# GET /admin/users
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_list_users_unauthenticated_returns_401(client: AsyncClient) -> None:
    response = await client.get("/api/v1/admin/users")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_list_users_viewer_returns_403(
    client: AsyncClient, make_token: Callable[..., str]
) -> None:
    response = await client.get("/api/v1/admin/users", headers=_viewer_headers(make_token))
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_list_users_admin_returns_list(
    client: AsyncClient, make_token: Callable[..., str]
) -> None:
    response = await client.get("/api/v1/admin/users", headers=_admin_headers(make_token))
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) > 0
    user = data[0]
    assert "id" in user
    assert "email" in user
    assert "roles" in user
    assert "is_active" in user


# ---------------------------------------------------------------------------
# GET /admin/domains
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_list_domains_unauthenticated_returns_401(client: AsyncClient) -> None:
    response = await client.get("/api/v1/admin/domains")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_list_domains_viewer_returns_403(
    client: AsyncClient, make_token: Callable[..., str]
) -> None:
    response = await client.get("/api/v1/admin/domains", headers=_viewer_headers(make_token))
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_list_domains_admin_returns_list(
    client: AsyncClient, make_token: Callable[..., str]
) -> None:
    response = await client.get("/api/v1/admin/domains", headers=_admin_headers(make_token))
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert any(d["name"] == "test-domain" for d in data)


# ---------------------------------------------------------------------------
# POST /admin/domains
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_create_domain_unauthenticated_returns_401(client: AsyncClient) -> None:
    response = await client.post("/api/v1/admin/domains", json={"name": "new-domain"})
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_create_domain_viewer_returns_403(
    client: AsyncClient, make_token: Callable[..., str]
) -> None:
    response = await client.post(
        "/api/v1/admin/domains",
        json={"name": "new-domain"},
        headers=_viewer_headers(make_token),
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_create_domain_admin_returns_201(
    client: AsyncClient, make_token: Callable[..., str]
) -> None:
    domain_name = f"admin-test-domain-{uuid.uuid4().hex[:8]}"
    response = await client.post(
        "/api/v1/admin/domains",
        json={"name": domain_name},
        headers=_admin_headers(make_token),
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == domain_name
    assert data["disabled_at"] is None


@pytest.mark.asyncio
async def test_create_domain_duplicate_returns_409(
    client: AsyncClient, make_token: Callable[..., str]
) -> None:
    response = await client.post(
        "/api/v1/admin/domains",
        json={"name": "test-domain"},
        headers=_admin_headers(make_token),
    )
    assert response.status_code == 409


# ---------------------------------------------------------------------------
# POST /admin/domains/{name}/disable and /enable
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_disable_domain_unauthenticated_returns_401(client: AsyncClient) -> None:
    response = await client.post("/api/v1/admin/domains/test-domain/disable")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_disable_then_enable_domain(
    client: AsyncClient, make_token: Callable[..., str]
) -> None:
    domain_name = f"toggle-domain-{uuid.uuid4().hex[:8]}"
    await client.post(
        "/api/v1/admin/domains",
        json={"name": domain_name},
        headers=_admin_headers(make_token),
    )

    disable = await client.post(
        f"/api/v1/admin/domains/{domain_name}/disable",
        headers=_admin_headers(make_token),
    )
    assert disable.status_code == 200
    assert disable.json()["disabled_at"] is not None

    enable = await client.post(
        f"/api/v1/admin/domains/{domain_name}/enable",
        headers=_admin_headers(make_token),
    )
    assert enable.status_code == 200
    assert enable.json()["disabled_at"] is None


@pytest.mark.asyncio
async def test_disable_domain_already_disabled_returns_409(
    client: AsyncClient, make_token: Callable[..., str]
) -> None:
    domain_name = f"already-disabled-{uuid.uuid4().hex[:8]}"
    await client.post(
        "/api/v1/admin/domains", json={"name": domain_name}, headers=_admin_headers(make_token)
    )
    await client.post(
        f"/api/v1/admin/domains/{domain_name}/disable", headers=_admin_headers(make_token)
    )
    response = await client.post(
        f"/api/v1/admin/domains/{domain_name}/disable", headers=_admin_headers(make_token)
    )
    assert response.status_code == 409


@pytest.mark.asyncio
async def test_enable_domain_already_active_returns_409(
    client: AsyncClient, make_token: Callable[..., str]
) -> None:
    domain_name = f"already-active-{uuid.uuid4().hex[:8]}"
    await client.post(
        "/api/v1/admin/domains", json={"name": domain_name}, headers=_admin_headers(make_token)
    )
    response = await client.post(
        f"/api/v1/admin/domains/{domain_name}/enable", headers=_admin_headers(make_token)
    )
    assert response.status_code == 409


@pytest.mark.asyncio
async def test_disable_nonexistent_domain_returns_404(
    client: AsyncClient, make_token: Callable[..., str]
) -> None:
    response = await client.post(
        "/api/v1/admin/domains/no-such-domain-xyz/disable",
        headers=_admin_headers(make_token),
    )
    assert response.status_code == 404


# ---------------------------------------------------------------------------
# GET /admin/users/{user_id}/domains
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_user_domains_unauthenticated_returns_401(client: AsyncClient) -> None:
    response = await client.get(f"/api/v1/admin/users/{uuid.uuid4()}/domains")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_get_user_domains_viewer_returns_403(
    client: AsyncClient, make_token: Callable[..., str]
) -> None:
    response = await client.get(
        f"/api/v1/admin/users/{uuid.uuid4()}/domains",
        headers=_viewer_headers(make_token),
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_get_user_domains_returns_assignments(
    client: AsyncClient, make_token: Callable[..., str]
) -> None:
    # test-sub-001 is pre-seeded in conftest with test-domain assignment
    system_user_id = uuid.UUID("00000000-0000-0000-0000-000000000001")
    target_uid = uuid.uuid5(system_user_id, "test-sub-001")

    response = await client.get(
        f"/api/v1/admin/users/{target_uid}/domains",
        headers=_admin_headers(make_token),
    )
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert any(d["domain"] == "test-domain" for d in data)


# ---------------------------------------------------------------------------
# PUT /admin/users/{user_id}/domains
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_replace_user_domains_unauthenticated_returns_401(client: AsyncClient) -> None:
    response = await client.put(
        f"/api/v1/admin/users/{uuid.uuid4()}/domains", json={"domains": []}
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_replace_user_domains_viewer_returns_403(
    client: AsyncClient, make_token: Callable[..., str]
) -> None:
    response = await client.put(
        f"/api/v1/admin/users/{uuid.uuid4()}/domains",
        json={"domains": []},
        headers=_viewer_headers(make_token),
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_replace_user_domains_nonexistent_user_returns_404(
    client: AsyncClient, make_token: Callable[..., str]
) -> None:
    response = await client.put(
        f"/api/v1/admin/users/{uuid.uuid4()}/domains",
        json={"domains": ["test-domain"]},
        headers=_admin_headers(make_token),
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_replace_user_domains_replaces_assignments(
    client: AsyncClient, make_token: Callable[..., str]
) -> None:
    system_user_id = uuid.UUID("00000000-0000-0000-0000-000000000001")
    target_uid = uuid.uuid5(system_user_id, "test-sub-001")

    domain_name = f"replace-domain-{uuid.uuid4().hex[:8]}"
    await client.post(
        "/api/v1/admin/domains",
        json={"name": domain_name},
        headers=_admin_headers(make_token),
    )

    response = await client.put(
        f"/api/v1/admin/users/{target_uid}/domains",
        json={"domains": [domain_name]},
        headers=_admin_headers(make_token),
    )
    assert response.status_code == 200
    data = response.json()
    domains = [d["domain"] for d in data]
    assert domain_name in domains
    assert "test-domain" not in domains

    # Restore original assignment so other tests aren't broken
    await client.put(
        f"/api/v1/admin/users/{target_uid}/domains",
        json={"domains": ["test-domain"]},
        headers=_admin_headers(make_token),
    )
