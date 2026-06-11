"""Scheduled maintenance jobs (§8.2, §14). Runs on the default worker."""

import sqlalchemy as sa
import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

from api.models.review_claim import ReviewClaim
from api.services.notifications import create_notification

log = structlog.get_logger(__name__)


async def expire_review_claims(ctx: dict) -> None:  # type: ignore[type-arg]
    """Release review claims whose expiry has passed (§8.2, §14).

    Runs every 15 minutes via cron. Sets released_at on any claim where
    released_at IS NULL AND expires_at < NOW(). Notifies each claimer.
    """
    engine: AsyncEngine = ctx["db_engine"]
    async with AsyncSession(engine) as session:
        # Fetch expiring claims before releasing so we can notify claimers.
        expiring = (
            await session.execute(
                select(ReviewClaim).where(
                    ReviewClaim.released_at.is_(None),
                    ReviewClaim.expires_at < sa.func.now(),
                )
            )
        ).scalars().all()

        for claim in expiring:
            claim.released_at = sa.func.now()
            await create_notification(
                session, claim.claimed_by, "claim_expired", claim.entity_type,
                claim.entity_id,
                f"Your review claim on a {claim.entity_type} has expired"
                " and returned to the queue.",
            )

        expired_count = len(expiring)
        await session.commit()

    if expired_count:
        log.info("review_claims_expired", count=expired_count)
