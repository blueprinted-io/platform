"""Versioned API router — all /api/v1/ routes registered here."""

from fastapi import APIRouter

from api.routes import concepts, facts, principles, tasks, users, workflows

router = APIRouter(prefix="/api/v1")
router.include_router(users.router)
router.include_router(facts.router)
router.include_router(concepts.router)
router.include_router(principles.router)
router.include_router(tasks.router)
router.include_router(workflows.router)
