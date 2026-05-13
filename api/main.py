"""FastAPI application factory."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import secure
import structlog
from fastapi import FastAPI, Request, Response

from api.auth import TokenVerifier
from api.config import Settings, get_settings
from api.database import create_engine, create_session_factory
from api.logging import configure_logging
from api.middleware import RequestIDMiddleware
from api.routes import health, v1

log = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    settings: Settings = app.state.settings
    engine = create_engine(settings)
    app.state.engine = engine
    app.state.session_factory = create_session_factory(engine)

    # TokenVerifier is only initialised when OIDC is configured.
    # Tests replace app.state.token_verifier with a StubTokenVerifier.
    if settings.oidc_jwks_uri:
        app.state.token_verifier = TokenVerifier(
            jwks_uri=settings.oidc_jwks_uri,
            issuer=settings.oidc_issuer,
            audience=settings.oidc_audience,
            roles_claim=settings.oidc_roles_claim,
        )
    else:
        app.state.token_verifier = None

    log.info("startup_complete", env=settings.app_env)
    yield
    await engine.dispose()
    log.info("shutdown_complete")


def create_app(settings: Settings | None = None) -> FastAPI:
    if settings is None:
        settings = get_settings()

    configure_logging(settings.log_level)

    app = FastAPI(
        title="Blueprinted",
        version="0.1.0",
        docs_url="/api/docs",
        redoc_url="/api/redoc",
        openapi_url="/api/openapi.json",
        lifespan=lifespan,
    )
    app.state.settings = settings

    # Middleware — order matters: outermost wraps innermost
    app.add_middleware(RequestIDMiddleware)

    # Security headers on every response
    secure_headers = secure.Secure.with_default_headers()

    @app.middleware("http")
    async def add_security_headers(request: Request, call_next: object) -> Response:
        response: Response = await call_next(request)  # type: ignore[operator]
        secure_headers.set_headers(response)  # type: ignore[arg-type]  # MutableHeaders vs MutableMapping
        return response

    # Routes
    app.include_router(health.router)
    app.include_router(v1.router)

    return app
