"""Versioned API router — all /api/v1/ routes registered here."""

from fastapi import APIRouter

from api.routes import users

router = APIRouter(prefix="/api/v1")
router.include_router(users.router)
