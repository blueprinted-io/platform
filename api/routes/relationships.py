"""Relationships API endpoints. §9.4, §23.9

All writes rejected with HTTP 422 in v1 — no relationship kinds are defined.
GET /relationships is unrestricted (all authenticated roles).
"""

from fastapi import APIRouter, status
from sqlalchemy import select

from api.dependencies import CurrentUser, DBSession
from api.models.relationship import Relationship
from api.schemas.relationship import RelationshipResponse

router = APIRouter(prefix="/relationships", tags=["relationships"])


@router.get("", response_model=list[RelationshipResponse])
async def list_relationships(session: DBSession, _user: CurrentUser) -> list[Relationship]:
    result = await session.execute(select(Relationship).order_by(Relationship.created_at.desc()))
    return list(result.scalars().all())


@router.post("", status_code=status.HTTP_422_UNPROCESSABLE_CONTENT)
async def create_relationship(_user: CurrentUser) -> dict[str, str]:
    return {"detail": "No relationship kinds are defined in v1. Writes are not permitted."}
