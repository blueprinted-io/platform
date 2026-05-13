"""pytest fixtures for the Blueprinted test suite.

Test DB setup runs via asyncio.run() (outside pytest-asyncio's managed loops)
so there are no event-loop-scope conflicts.

asgi-lifespan triggers the FastAPI lifespan (startup hook) so app.state is
populated before the first request.

JWT test utilities use a session-scoped RSA key pair. The client fixture
installs a StubTokenVerifier on app.state so no live Authentik is needed.
"""

import asyncio
import time
import uuid
from collections.abc import AsyncGenerator, Callable, Generator
from typing import Any

import jwt
import pytest
import pytest_asyncio
import sqlalchemy as sa
from asgi_lifespan import LifespanManager
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives.asymmetric.rsa import RSAPrivateKey, RSAPublicKey
from httpx import ASGITransport, AsyncClient
from sqlalchemy.dialects.postgresql import insert as pg_insert

from api.auth import StubTokenVerifier
from api.config import Settings
from api.database import Base, create_engine
from api.main import create_app
from api.models.domain import Domain, UserDomain
from api.models.user import User

# ---------------------------------------------------------------------------
# Settings
# ---------------------------------------------------------------------------

TEST_ISSUER = "https://auth.test.example.com/"
TEST_AUDIENCE = "blueprinted-test"


@pytest.fixture(scope="session")
def test_settings() -> Settings:
    # _env_file=None prevents pydantic-settings from reading the project .env,
    # which contains Docker Compose keys (AUTHENTIK_*, API_PORT, etc.) that are
    # not in the Settings model. Settings uses extra="forbid", so those keys
    # would cause a ValidationError. Tests supply all required values explicitly.
    return Settings(
        _env_file=None,  # type: ignore[call-arg]
        app_env="test",
        database_url="postgresql+asyncpg://blueprinted:blueprinted@localhost:5432/blueprinted_test",
        database_url_sync="postgresql+psycopg2://blueprinted:blueprinted@localhost:5432/blueprinted_test",
        redis_url="redis://localhost:6379/1",
        log_level="WARNING",
        app_secret_key="ci-test-secret-not-for-production",  # type: ignore[arg-type]
        oidc_issuer=TEST_ISSUER,
        oidc_audience=TEST_AUDIENCE,
        oidc_roles_claim="roles",
    )


# ---------------------------------------------------------------------------
# Database setup
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session", autouse=True)
def setup_test_db(test_settings: Settings) -> Generator[None, None, None]:
    """Create all ORM tables once per session, outside the async event loop."""

    async def _create() -> None:
        engine = create_engine(test_settings)
        async with engine.begin() as conn:
            # pgvector extension must exist before vector(1536) columns are created
            await conn.execute(sa.text("CREATE EXTENSION IF NOT EXISTS vector"))
            await conn.run_sync(Base.metadata.drop_all)
            await conn.run_sync(Base.metadata.create_all)
        await engine.dispose()

    asyncio.run(_create())
    yield


# ---------------------------------------------------------------------------
# Domain and user pre-seeding
# ---------------------------------------------------------------------------

# Stable system user UUID for domain created_by FK
_SYSTEM_USER_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")

_TEST_DOMAIN = "test-domain"

# All contributor subs that interact with domain-enforced resources (tasks, workflows, principles).
# Pre-creating these ensures their UUIDs are stable before domain assignments are inserted.
_CONTRIBUTOR_SUBS: list[str] = [
    "test-sub-001",
    "author-cpt-001", "reviewer-cpt-001",
    "author-cpt-immut-001", "reviewer-cpt-immut-001",
    "author-cpt-ret-001", "reviewer-cpt-ret-001",
    "self-cpt-001", "contrib-cpt-dep-001",
    "author-prn-001", "reviewer-prn-001",
    "author-prn-immut-001", "reviewer-prn-immut-001",
    "author-prn-ret-001", "reviewer-prn-ret-001",
    "self-prn-001", "contrib-prn-dep-001",
    "author-step-immut-001", "reviewer-step-immut-001",
    "author-ref-001", "reviewer-ref-001",
    "author-ref-002", "reviewer-ref-002",
    "author-cref-001", "reviewer-cref-001",
    "author-task-001", "reviewer-task-001",
    "self-task-001",
    "author-task-immut-001", "reviewer-task-immut-001",
    "author-task-ret-001", "reviewer-task-ret-001",
    "author-wf-tref-001", "reviewer-wf-tref-001",
    "author-wf-immut-001", "reviewer-wf-immut-001",
    "author-wf-pref-001", "reviewer-wf-pref-001",
    "author-wf-001", "reviewer-wf-001",
    "self-wf-001",
    "author-wf-immut-002", "reviewer-wf-immut-002",
    "author-wf-ret-001", "reviewer-wf-ret-001",
    # Sprint 5 — review queue and claiming tests
    "author-rv-001",
    "reviewer-rv-001",
    "claimer-rv-001",
    "self-rv-001",
]


@pytest.fixture(scope="session", autouse=True)
def setup_test_domain_and_users(test_settings: Settings, setup_test_db: None) -> None:
    """Pre-seed the test domain and all contributor users with domain assignments.

    Contributors are lazily upserted by the auth dependency on first request, but
    domain assignment requires the user row to exist before domain-checking endpoints
    are called. We pre-create users here with stable UUIDs so user_domains resolves.
    """

    async def _seed() -> None:
        engine = create_engine(test_settings)
        async with engine.begin() as conn:
            await conn.execute(
                pg_insert(User)
                .values(
                    id=_SYSTEM_USER_ID,
                    sub="__system__",
                    email="system@blueprinted.internal",
                    display_name="System",
                    roles=["admin"],
                    is_active=True,
                )
                .on_conflict_do_nothing()
            )
            await conn.execute(
                pg_insert(Domain)
                .values(name=_TEST_DOMAIN, created_by=_SYSTEM_USER_ID)
                .on_conflict_do_nothing()
            )
            for sub in _CONTRIBUTOR_SUBS:
                uid = uuid.uuid5(_SYSTEM_USER_ID, sub)
                await conn.execute(
                    pg_insert(User)
                    .values(
                        id=uid,
                        sub=sub,
                        email=f"{sub}@test.example.com",
                        display_name=sub,
                        roles=["contributor"],
                        is_active=True,
                    )
                    .on_conflict_do_nothing()
                )
                await conn.execute(
                    pg_insert(UserDomain)
                    .values(user_id=uid, domain=_TEST_DOMAIN, created_by=_SYSTEM_USER_ID)
                    .on_conflict_do_nothing()
                )
        await engine.dispose()

    asyncio.run(_seed())


# ---------------------------------------------------------------------------
# RSA key pair for JWT signing in tests
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def rsa_private_key() -> RSAPrivateKey:
    return rsa.generate_private_key(public_exponent=65537, key_size=2048)


@pytest.fixture(scope="session")
def rsa_public_key(rsa_private_key: RSAPrivateKey) -> RSAPublicKey:
    return rsa_private_key.public_key()


@pytest.fixture(scope="session")
def make_token(rsa_private_key: RSAPrivateKey) -> Callable[..., str]:
    """Factory that produces signed RS256 JWTs for testing."""

    def _make(
        sub: str = "test-sub-001",
        email: str = "test@example.com",
        name: str = "Test User",
        roles: list[str] | None = None,
        issuer: str = TEST_ISSUER,
        audience: str = TEST_AUDIENCE,
        exp_offset: int = 3600,
        extra: dict[str, Any] | None = None,
    ) -> str:
        now = int(time.time())
        payload: dict[str, Any] = {
            "sub": sub,
            "email": email,
            "name": name,
            "roles": roles if roles is not None else ["viewer"],
            "iss": issuer,
            "aud": audience,
            "iat": now,
            "exp": now + exp_offset,
        }
        if extra:
            payload.update(extra)
        return jwt.encode(payload, rsa_private_key, algorithm="RS256")

    return _make


# ---------------------------------------------------------------------------
# HTTP client
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture
async def client(
    test_settings: Settings,
    rsa_public_key: RSAPublicKey,
) -> AsyncGenerator[AsyncClient, None]:
    """Async HTTP client with lifespan started and StubTokenVerifier installed."""
    app = create_app(settings=test_settings)
    async with LifespanManager(app):
        app.state.token_verifier = StubTokenVerifier(
            public_key=rsa_public_key,
            issuer=TEST_ISSUER,
            audience=TEST_AUDIENCE,
        )
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as ac:
            yield ac
