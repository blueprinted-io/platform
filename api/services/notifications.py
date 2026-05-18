"""Notification creation helpers (§13)."""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.models.domain import UserDomain
from api.models.notification import Notification


async def create_notification(
    session: AsyncSession,
    user_id: uuid.UUID,
    kind: str,
    entity_type: str,
    entity_id: uuid.UUID,
    message: str,
) -> Notification:
    notification = Notification(
        user_id=user_id,
        kind=kind,
        entity_type=entity_type,
        entity_id=entity_id,
        message=message,
    )
    session.add(notification)
    return notification


async def notify_domain_users(
    session: AsyncSession,
    domain: str,
    kind: str,
    entity_type: str,
    entity_id: uuid.UUID,
    message: str,
    exclude_user_id: uuid.UUID | None = None,
) -> int:
    """Create a notification for every user in domain, optionally excluding one."""
    result = await session.execute(
        select(UserDomain.user_id).where(UserDomain.domain == domain)
    )
    user_ids = [row for row in result.scalars().all()]

    count = 0
    for uid in user_ids:
        if exclude_user_id is not None and uid == exclude_user_id:
            continue
        await create_notification(session, uid, kind, entity_type, entity_id, message)
        count += 1

    return count
