"""Versioned API router — all /api/v1/ routes registered here."""

from fastapi import APIRouter

from api.routes import (
    ingestions,
    notifications,
    principles,
    review,
    search,
    tasks,
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
router.include_router(notifications.router)
