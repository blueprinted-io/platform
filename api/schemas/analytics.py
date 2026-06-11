"""Analytics response schemas — §15 Dashboards."""

import uuid
from datetime import datetime

from pydantic import BaseModel


class RecentRecord(BaseModel):
    id: uuid.UUID
    record_type: str
    title: str
    domain: str | None
    updated_at: datetime


class ContributorStats(BaseModel):
    my_drafts: int
    my_submitted: int
    my_returned: int
    recently_returned: list[RecentRecord]


class ReviewerStats(BaseModel):
    queue_depth: int


class DomainStaleness(BaseModel):
    domain: str
    stale_count: int


class AdminStats(BaseModel):
    confirmed_30d: int
    return_rate_30d: float
    stale_confirmed_count: int
    stale_by_domain: list[DomainStaleness]
    staleness_threshold_days: int


class DashboardResponse(BaseModel):
    contributor: ContributorStats
    reviewer: ReviewerStats
    admin: AdminStats | None
