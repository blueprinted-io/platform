"""pytest fixtures for the Blueprinted test suite.

Test DB setup runs via asyncio.run() (outside pytest-asyncio's managed loops)
so there are no event-loop-scope conflicts.

asgi-lifespan is used to trigger the FastAPI lifespan (startup hook) so
app.state is populated before the first request in each test.

Sprint 4: add transactional isolation fixtures once data model tables exist.
"""

import asyncio
from collections.abc import AsyncGenerator, Generator

import pytest
import pytest_asyncio
from asgi_lifespan import LifespanManager
from httpx import ASGITransport, AsyncClient

from api.config import Settings
from api.database import Base, create_engine
from api.main import create_app


@pytest.fixture(scope="session")
def test_settings() -> Settings:
    return Settings(
        app_env="test",
        database_url="postgresql+asyncpg://blueprinted:blueprinted@localhost:5432/blueprinted_test",
        database_url_sync="postgresql+psycopg2://blueprinted:blueprinted@localhost:5432/blueprinted_test",
        redis_url="redis://localhost:6379/1",
        log_level="WARNING",
        app_secret_key="ci-test-secret-not-for-production",  # type: ignore[arg-type]
    )


@pytest.fixture(scope="session", autouse=True)
def setup_test_db(test_settings: Settings) -> Generator[None, None, None]:
    """Create all ORM tables once per session, outside the async event loop."""

    async def _create() -> None:
        engine = create_engine(test_settings)
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
            await conn.run_sync(Base.metadata.create_all)
        await engine.dispose()

    asyncio.run(_create())
    yield


@pytest_asyncio.fixture
async def client(test_settings: Settings) -> AsyncGenerator[AsyncClient, None]:
    """Async HTTP client with lifespan properly started via asgi-lifespan."""
    app = create_app(settings=test_settings)
    async with LifespanManager(app):
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as ac:
            yield ac
