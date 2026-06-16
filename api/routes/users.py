"""User profile endpoints."""

from fastapi import APIRouter

from api.dependencies import CurrentUser, DBSession
from api.schemas.user import UserPreferencesUpdate, UserResponse

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=UserResponse)
async def get_me(user: CurrentUser) -> UserResponse:
    """Return the authenticated user's profile."""
    return UserResponse.model_validate(user)


@router.patch("/me/preferences", response_model=UserResponse)
async def patch_preferences(
    body: UserPreferencesUpdate,
    user: CurrentUser,
    session: DBSession,
) -> UserResponse:
    """Merge preference updates into the current user's stored preferences."""
    patch = body.model_dump(exclude_none=True)
    user.preferences = {**user.preferences, **patch}
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return UserResponse.model_validate(user)
