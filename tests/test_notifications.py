"""Tests for the Notifications API (§13).

Spec refs:
  §13  Notifications — list, mark read, mark all read
"""

import uuid
from collections.abc import Callable
from datetime import UTC, datetime

import pytest
import sqlalchemy as sa
from httpx import AsyncClient
from sqlalchemy.dialects.postgresql import insert as pg_insert

from api.config import Settings
from api.database import create_engine
from api.models.notification import Notification
from api.models.user import User

pytestmark = pytest.mark.asyncio

_NOTIF_USER_SUB = "notif-user-001"
_NOTIF_USER_ID = uuid.uuid5(uuid.UUID("00000000-0000-0000-0000-000000000001"), _NOTIF_USER_SUB)
_OTHER_USER_SUB = "notif-other-001"
_OTHER_USER_ID = uuid.uuid5(uuid.UUID("00000000-0000-0000-0000-000000000001"), _OTHER_USER_SUB)


async def _seed_users(test_settings: Settings) -> None:
    engine = create_engine(test_settings)
    async with engine.begin() as conn:
        for uid, sub in [(_NOTIF_USER_ID, _NOTIF_USER_SUB), (_OTHER_USER_ID, _OTHER_USER_SUB)]:
            await conn.execute(
                pg_insert(User)
                .values(
                    id=uid,
                    sub=sub,
                    email=f"{sub}@test.example.com",
                    display_name=sub,
                    roles=["viewer"],
                    is_active=True,
                )
                .on_conflict_do_nothing()
            )
    await engine.dispose()


async def _insert_notification(
    test_settings: Settings,
    user_id: uuid.UUID,
    *,
    read: bool = False,
) -> uuid.UUID:
    notif_id = uuid.uuid4()
    engine = create_engine(test_settings)
    async with engine.begin() as conn:
        await conn.execute(
            sa.insert(Notification).values(
                id=notif_id,
                user_id=user_id,
                kind="task_confirmed",
                entity_type="task",
                entity_id=uuid.uuid4(),
                message="Test notification",
                created_at=datetime.now(tz=UTC),
                read_at=datetime.now(tz=UTC) if read else None,
            )
        )
    await engine.dispose()
    return notif_id


async def _delete_notifications_for(test_settings: Settings, user_id: uuid.UUID) -> None:
    engine = create_engine(test_settings)
    async with engine.begin() as conn:
        await conn.execute(sa.delete(Notification).where(Notification.user_id == user_id))
    await engine.dispose()


# ---------------------------------------------------------------------------
# GET /notifications — list
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_list_notifications_unauthenticated_returns_401(client: AsyncClient) -> None:
    response = await client.get("/api/v1/notifications")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_list_notifications_returns_own_notifications(
    client: AsyncClient, make_token: Callable[..., str], test_settings: Settings
) -> None:
    await _seed_users(test_settings)
    await _delete_notifications_for(test_settings, _NOTIF_USER_ID)
    notif_id = await _insert_notification(test_settings, _NOTIF_USER_ID)
    await _insert_notification(test_settings, _OTHER_USER_ID)

    token = make_token(sub=_NOTIF_USER_SUB, roles=["viewer"])
    response = await client.get(
        "/api/v1/notifications", headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 200
    data = response.json()
    ids = [n["id"] for n in data]
    assert str(notif_id) in ids
    assert all(n["id"] != str(_OTHER_USER_ID) for n in data)

    await _delete_notifications_for(test_settings, _NOTIF_USER_ID)
    await _delete_notifications_for(test_settings, _OTHER_USER_ID)


@pytest.mark.asyncio
async def test_list_notifications_unread_only_filter(
    client: AsyncClient, make_token: Callable[..., str], test_settings: Settings
) -> None:
    await _seed_users(test_settings)
    await _delete_notifications_for(test_settings, _NOTIF_USER_ID)
    unread_id = await _insert_notification(test_settings, _NOTIF_USER_ID, read=False)
    await _insert_notification(test_settings, _NOTIF_USER_ID, read=True)

    token = make_token(sub=_NOTIF_USER_SUB, roles=["viewer"])
    response = await client.get(
        "/api/v1/notifications?unread_only=true",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["id"] == str(unread_id)

    await _delete_notifications_for(test_settings, _NOTIF_USER_ID)


@pytest.mark.asyncio
async def test_list_notifications_empty_for_new_user(
    client: AsyncClient, make_token: Callable[..., str], test_settings: Settings
) -> None:
    await _seed_users(test_settings)
    await _delete_notifications_for(test_settings, _NOTIF_USER_ID)

    token = make_token(sub=_NOTIF_USER_SUB, roles=["viewer"])
    response = await client.get(
        "/api/v1/notifications", headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 200
    assert response.json() == []


# ---------------------------------------------------------------------------
# POST /notifications/{id}/read — mark single read
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_mark_read_unauthenticated_returns_401(client: AsyncClient) -> None:
    response = await client.post(f"/api/v1/notifications/{uuid.uuid4()}/read")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_mark_read_sets_read_at(
    client: AsyncClient, make_token: Callable[..., str], test_settings: Settings
) -> None:
    await _seed_users(test_settings)
    notif_id = await _insert_notification(test_settings, _NOTIF_USER_ID, read=False)

    token = make_token(sub=_NOTIF_USER_SUB, roles=["viewer"])
    response = await client.post(
        f"/api/v1/notifications/{notif_id}/read",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == str(notif_id)
    assert data["read_at"] is not None

    await _delete_notifications_for(test_settings, _NOTIF_USER_ID)


@pytest.mark.asyncio
async def test_mark_read_already_read_is_idempotent(
    client: AsyncClient, make_token: Callable[..., str], test_settings: Settings
) -> None:
    await _seed_users(test_settings)
    notif_id = await _insert_notification(test_settings, _NOTIF_USER_ID, read=True)

    token = make_token(sub=_NOTIF_USER_SUB, roles=["viewer"])
    response = await client.post(
        f"/api/v1/notifications/{notif_id}/read",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    assert response.json()["read_at"] is not None

    await _delete_notifications_for(test_settings, _NOTIF_USER_ID)


@pytest.mark.asyncio
async def test_mark_read_other_users_notification_returns_404(
    client: AsyncClient, make_token: Callable[..., str], test_settings: Settings
) -> None:
    await _seed_users(test_settings)
    notif_id = await _insert_notification(test_settings, _OTHER_USER_ID)

    token = make_token(sub=_NOTIF_USER_SUB, roles=["viewer"])
    response = await client.post(
        f"/api/v1/notifications/{notif_id}/read",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 404

    await _delete_notifications_for(test_settings, _OTHER_USER_ID)


@pytest.mark.asyncio
async def test_mark_read_nonexistent_returns_404(
    client: AsyncClient, make_token: Callable[..., str], test_settings: Settings
) -> None:
    await _seed_users(test_settings)
    token = make_token(sub=_NOTIF_USER_SUB, roles=["viewer"])
    response = await client.post(
        f"/api/v1/notifications/{uuid.uuid4()}/read",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 404


# ---------------------------------------------------------------------------
# POST /notifications/read-all — mark all read
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_mark_all_read_unauthenticated_returns_401(client: AsyncClient) -> None:
    response = await client.post("/api/v1/notifications/read-all")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_mark_all_read_returns_204(
    client: AsyncClient, make_token: Callable[..., str], test_settings: Settings
) -> None:
    await _seed_users(test_settings)
    await _delete_notifications_for(test_settings, _NOTIF_USER_ID)
    await _insert_notification(test_settings, _NOTIF_USER_ID, read=False)
    await _insert_notification(test_settings, _NOTIF_USER_ID, read=False)

    token = make_token(sub=_NOTIF_USER_SUB, roles=["viewer"])
    response = await client.post(
        "/api/v1/notifications/read-all",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 204

    check = await client.get(
        "/api/v1/notifications?unread_only=true",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert check.json() == []

    await _delete_notifications_for(test_settings, _NOTIF_USER_ID)


@pytest.mark.asyncio
async def test_mark_all_read_only_affects_own_notifications(
    client: AsyncClient, make_token: Callable[..., str], test_settings: Settings
) -> None:
    await _seed_users(test_settings)
    await _delete_notifications_for(test_settings, _NOTIF_USER_ID)
    await _delete_notifications_for(test_settings, _OTHER_USER_ID)
    await _insert_notification(test_settings, _NOTIF_USER_ID, read=False)
    other_notif_id = await _insert_notification(test_settings, _OTHER_USER_ID, read=False)

    token = make_token(sub=_NOTIF_USER_SUB, roles=["viewer"])
    await client.post(
        "/api/v1/notifications/read-all",
        headers={"Authorization": f"Bearer {token}"},
    )

    other_token = make_token(sub=_OTHER_USER_SUB, roles=["viewer"])
    check = await client.get(
        "/api/v1/notifications?unread_only=true",
        headers={"Authorization": f"Bearer {other_token}"},
    )
    ids = [n["id"] for n in check.json()]
    assert str(other_notif_id) in ids

    await _delete_notifications_for(test_settings, _NOTIF_USER_ID)
    await _delete_notifications_for(test_settings, _OTHER_USER_ID)
