"""Analytics and dashboard endpoint — §15.

Single endpoint: GET /analytics/dashboard
Returns a role-shaped payload with contributor stats (all users), reviewer
queue depth (all users, reflects domain assignments), and admin stats (admin only).

§15 specifies a fixed role-aware layout for v1. Customisable layouts are v2.
"""

import uuid
from datetime import UTC, datetime, timedelta

from typing import Annotated

import sqlalchemy as sa
import structlog
from fastapi import APIRouter
from sqlalchemy.ext.asyncio import AsyncSession

from api.auth import Role
from api.dependencies import DBSession, require_role
from api.models.user import User
from api.schemas.analytics import (
    AdminStats,
    ContributorStats,
    DashboardResponse,
    DomainStaleness,
    RecentRecord,
    ReviewerStats,
)

log = structlog.get_logger(__name__)

router = APIRouter(prefix="/analytics", tags=["analytics"])

_AnyUser = Annotated[User, require_role(Role.VIEWER, Role.CONTRIBUTOR, Role.ADMIN)]

# Default staleness window. TODO: make configurable via system_settings.
_STALENESS_DAYS = 90

_CONTRIBUTOR_COUNTS_SQL = sa.text("""
WITH latest_tasks AS (
  SELECT id, status FROM tasks t
  WHERE t.version = (SELECT MAX(v.version) FROM tasks v WHERE v.record_id = t.record_id)
    AND t.created_by = :user_id
),
latest_workflows AS (
  SELECT id, status FROM workflows w
  WHERE w.version = (SELECT MAX(v.version) FROM workflows v WHERE v.record_id = w.record_id)
    AND w.created_by = :user_id
),
latest_principles AS (
  SELECT id, status FROM principles p
  WHERE p.version = (SELECT MAX(v.version) FROM principles v WHERE v.record_id = p.record_id)
    AND p.created_by = :user_id
),
all_mine AS (
  SELECT status FROM latest_tasks
  UNION ALL
  SELECT status FROM latest_workflows
  UNION ALL
  SELECT status FROM latest_principles
)
SELECT
  SUM(CASE WHEN status = 'draft'     THEN 1 ELSE 0 END) AS my_drafts,
  SUM(CASE WHEN status = 'submitted' THEN 1 ELSE 0 END) AS my_submitted,
  SUM(CASE WHEN status = 'returned'  THEN 1 ELSE 0 END) AS my_returned
FROM all_mine
""")

_RECENTLY_RETURNED_SQL = sa.text("""
SELECT id, 'task' AS record_type, title, domain, updated_at FROM tasks t
WHERE t.version = (SELECT MAX(v.version) FROM tasks v WHERE v.record_id = t.record_id)
  AND t.created_by = :user_id AND t.status = 'returned'
UNION ALL
SELECT id, 'workflow' AS record_type, title, domain, updated_at FROM workflows w
WHERE w.version = (SELECT MAX(v.version) FROM workflows v WHERE v.record_id = w.record_id)
  AND w.created_by = :user_id AND w.status = 'returned'
UNION ALL
SELECT id, 'principle' AS record_type, title, domain, updated_at FROM principles p
WHERE p.version = (SELECT MAX(v.version) FROM principles v WHERE v.record_id = p.record_id)
  AND p.created_by = :user_id AND p.status = 'returned'
ORDER BY updated_at DESC
LIMIT 5
""")

_QUEUE_DEPTH_SQL = sa.text("""
SELECT COUNT(*) AS depth FROM (
  SELECT record_id FROM tasks
  WHERE status = 'submitted' AND created_by != :user_id
    AND (:is_admin OR domain = ANY(:domains))
  UNION ALL
  SELECT record_id FROM workflows
  WHERE status = 'submitted' AND created_by != :user_id
    AND (:is_admin OR domain = ANY(:domains))
  UNION ALL
  SELECT record_id FROM principles
  WHERE status = 'submitted' AND created_by != :user_id
    AND (:is_admin OR domain = ANY(:domains))
) q
""")

_ADMIN_THROUGHPUT_SQL = sa.text("""
SELECT
  SUM(CASE WHEN status = 'confirmed' THEN 1 ELSE 0 END) AS confirmed_30d,
  SUM(CASE WHEN status = 'returned'  THEN 1 ELSE 0 END) AS returned_30d
FROM (
  SELECT status FROM tasks   WHERE status IN ('confirmed','returned') AND updated_at > :cutoff
  UNION ALL
  SELECT status FROM workflows WHERE status IN ('confirmed','returned') AND updated_at > :cutoff
  UNION ALL
  SELECT status FROM principles WHERE status IN ('confirmed','returned') AND updated_at > :cutoff
) recent
""")

_STALENESS_SQL = sa.text("""
SELECT domain, COUNT(*) AS stale_count FROM (
  SELECT domain FROM tasks t
  WHERE t.version = (SELECT MAX(v.version) FROM tasks v WHERE v.record_id = t.record_id)
    AND t.status = 'confirmed'
    AND (t.reviewed_at IS NULL OR t.reviewed_at < :threshold)
  UNION ALL
  SELECT domain FROM workflows w
  WHERE w.version = (SELECT MAX(v.version) FROM workflows v WHERE v.record_id = w.record_id)
    AND w.status = 'confirmed'
    AND (w.reviewed_at IS NULL OR w.reviewed_at < :threshold)
  UNION ALL
  SELECT domain FROM principles p
  WHERE p.version = (SELECT MAX(v.version) FROM principles v WHERE v.record_id = p.record_id)
    AND p.status = 'confirmed'
    AND (p.reviewed_at IS NULL OR p.reviewed_at < :threshold)
) stale
GROUP BY domain
ORDER BY stale_count DESC
""")


async def _contributor_stats(session: AsyncSession, user_id: uuid.UUID) -> ContributorStats:
    counts_row = (await session.execute(_CONTRIBUTOR_COUNTS_SQL, {"user_id": user_id})).one()
    my_drafts = counts_row.my_drafts or 0
    my_submitted = counts_row.my_submitted or 0
    my_returned = counts_row.my_returned or 0

    returned_rows = (await session.execute(_RECENTLY_RETURNED_SQL, {"user_id": user_id})).all()
    recently_returned = [
        RecentRecord(
            id=row.id,
            record_type=row.record_type,
            title=row.title,
            domain=row.domain,
            updated_at=row.updated_at,
        )
        for row in returned_rows
    ]
    return ContributorStats(
        my_drafts=my_drafts,
        my_submitted=my_submitted,
        my_returned=my_returned,
        recently_returned=recently_returned,
    )


async def _reviewer_stats(
    session: AsyncSession, user: User, is_admin: bool
) -> ReviewerStats:
    if not is_admin:
        domain_result = await session.execute(
            sa.text("SELECT domain FROM user_domains WHERE user_id = :uid"),
            {"uid": user.id},
        )
        domains = [row.domain for row in domain_result]
    else:
        domains = []

    depth_row = (
        await session.execute(
            _QUEUE_DEPTH_SQL,
            {"user_id": user.id, "is_admin": is_admin, "domains": domains},
        )
    ).one()
    return ReviewerStats(queue_depth=depth_row.depth or 0)


async def _admin_stats(session: AsyncSession) -> AdminStats:
    cutoff_30d = datetime.now(UTC) - timedelta(days=30)
    throughput_row = (
        await session.execute(_ADMIN_THROUGHPUT_SQL, {"cutoff": cutoff_30d})
    ).one()
    confirmed_30d = throughput_row.confirmed_30d or 0
    returned_30d = throughput_row.returned_30d or 0
    total_resolved = confirmed_30d + returned_30d
    return_rate = (returned_30d / total_resolved) if total_resolved > 0 else 0.0

    staleness_threshold = datetime.now(UTC) - timedelta(days=_STALENESS_DAYS)
    stale_rows = (
        await session.execute(_STALENESS_SQL, {"threshold": staleness_threshold})
    ).all()
    stale_by_domain = [
        DomainStaleness(domain=row.domain, stale_count=row.stale_count)
        for row in stale_rows
    ]
    stale_confirmed_count = sum(d.stale_count for d in stale_by_domain)

    return AdminStats(
        confirmed_30d=confirmed_30d,
        return_rate_30d=return_rate,
        stale_confirmed_count=stale_confirmed_count,
        stale_by_domain=stale_by_domain,
        staleness_threshold_days=_STALENESS_DAYS,
    )


@router.get("/dashboard", response_model=DashboardResponse)
async def get_dashboard(session: DBSession, user: _AnyUser) -> DashboardResponse:
    """Role-aware dashboard stats. §15."""
    is_admin = Role.ADMIN.value in user.roles

    contributor = await _contributor_stats(session, user.id)
    reviewer = await _reviewer_stats(session, user, is_admin)
    admin = await _admin_stats(session) if is_admin else None

    return DashboardResponse(contributor=contributor, reviewer=reviewer, admin=admin)
