"""Notifications API endpoints (§13)."""

import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Query
from sqlalchemy import select

from api.dependencies import CurrentUser, DBSession
from api.models.notification import Notification
from api.schemas.notification import NotificationResponse

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get("", response_model=list[NotificationResponse])
async def list_notifications(
    session: DBSession,
    user: CurrentUser,
    unread_only: bool = Query(default=False),
    limit: int = Query(default=20, le=100),
    offset: int = Query(default=0, ge=0),
) -> list[NotificationResponse]:
    """Return the current user's notifications, newest first."""
    q = (
        select(Notification)
        .where(Notification.user_id == user.id)
        .order_by(Notification.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    if unread_only:
        q = q.where(Notification.read_at.is_(None))

    result = await session.execute(q)
    return [NotificationResponse.model_validate(n) for n in result.scalars().all()]


@router.post("/{notification_id}/read", response_model=NotificationResponse)
async def mark_read(
    notification_id: uuid.UUID,
    session: DBSession,
    user: CurrentUser,
) -> NotificationResponse:
    """Mark a single notification as read."""
    notification = (
        await session.execute(
            select(Notification).where(
                Notification.id == notification_id,
                Notification.user_id == user.id,
            )
        )
    ).scalar_one_or_none()

    if notification is None:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Notification not found.")

    if notification.read_at is None:
        notification.read_at = datetime.now(tz=UTC)
        await session.commit()
        await session.refresh(notification)

    return NotificationResponse.model_validate(notification)


@router.post("/read-all", status_code=204)
async def mark_all_read(
    session: DBSession,
    user: CurrentUser,
) -> None:
    """Mark all unread notifications for the current user as read."""
    result = await session.execute(
        select(Notification).where(
            Notification.user_id == user.id,
            Notification.read_at.is_(None),
        )
    )
    now = datetime.now(tz=UTC)
    for notification in result.scalars().all():
        notification.read_at = now
    await session.commit()
