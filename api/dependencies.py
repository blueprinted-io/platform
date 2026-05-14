"""FastAPI dependency providers."""

from collections.abc import AsyncGenerator
from typing import Annotated

import structlog
from arq.connections import ArqRedis
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.auth import Role, TokenVerificationError, TokenVerifier
from api.config import Settings
from api.models.user import User

log = structlog.get_logger(__name__)

_bearer = HTTPBearer(auto_error=False)


# ---------------------------------------------------------------------------
# Settings (from app.state — uses the instance injected at startup, not a fresh
# Settings() call which would re-read .env and may fail with extra keys in test)
# ---------------------------------------------------------------------------

def get_app_settings(request: Request) -> Settings:
    return request.app.state.settings  # type: ignore[no-any-return]


AppSettings = Annotated[Settings, Depends(get_app_settings)]


# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------

async def get_db_session(request: Request) -> AsyncGenerator[AsyncSession, None]:
    """Yield a database session from the factory stored on app.state."""
    async with request.app.state.session_factory() as session:
        yield session


DBSession = Annotated[AsyncSession, Depends(get_db_session)]


# ---------------------------------------------------------------------------
# ARQ job queue
# ---------------------------------------------------------------------------

def get_arq_pool(request: Request) -> ArqRedis | None:
    """Return the ARQ pool stored on app.state, or None if unavailable."""
    return request.app.state.arq_pool  # type: ignore[no-any-return]


ArqPool = Annotated[ArqRedis | None, Depends(get_arq_pool)]


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------

def get_token_verifier(request: Request) -> TokenVerifier:
    """Return the TokenVerifier stored on app.state."""
    return request.app.state.token_verifier  # type: ignore[no-any-return]


async def get_current_user(
    session: DBSession,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
    verifier: Annotated[TokenVerifier, Depends(get_token_verifier)],
) -> User:
    """Validate Bearer token and return (or upsert) the authenticated user.

    Raises HTTP 401 for missing or invalid tokens.
    Raises HTTP 403 for inactive users.
    """
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        claims = verifier.decode(credentials.credentials)
    except TokenVerificationError as exc:
        log.warning("token_verification_failed", reason=str(exc))
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    sub: str = claims["sub"]
    email: str = claims.get("email", "")
    display_name: str | None = claims.get("name")
    roles = verifier.extract_roles(claims)

    # Upsert: sync user record from JWT claims on every authenticated request
    result = await session.execute(select(User).where(User.sub == sub))
    user = result.scalar_one_or_none()

    if user is None:
        user = User(sub=sub, email=email, display_name=display_name, roles=roles)
        session.add(user)
        log.info("user_created", sub=sub, email=email)
    else:
        user.email = email
        user.display_name = display_name
        user.roles = roles

    await session.commit()
    await session.refresh(user)

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive",
        )

    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def require_role(*roles: Role) -> Annotated[User, Depends]:
    """Dependency factory that enforces role membership.

    Usage:
        @router.get("/admin-only")
        async def admin_route(user: Annotated[User, Depends(require_role(Role.ADMIN))]):
            ...
    """
    allowed = {r.value for r in roles}

    async def _check(user: CurrentUser) -> User:
        if not any(r in allowed for r in user.roles):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions",
            )
        return user

    return Depends(_check)  # type: ignore[no-any-return]  # Depends() stubs return Any
