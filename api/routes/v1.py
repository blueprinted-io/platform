"""Versioned API router — all /api/v1/ routes registered here."""

from fastapi import APIRouter

from api.routes import (
    admin,
    ingestions,
    notifications,
    principles,
    review,
    search,
    tasks,
    triage_estimates,
    users,
    workflows,
)

router = APIRouter(prefix="/api/v1")
router.include_router(users.router)
router.include_router(principles.router)
router.include_router(tasks.router)
router.include_router(workflows.router)
router.include_router(review.router)
router.include_router(search.router)
router.include_router(ingestions.router)
router.include_router(triage_estimates.router)
router.include_router(notifications.router)
router.include_router(admin.router)
