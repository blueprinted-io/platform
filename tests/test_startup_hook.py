"""Tests for the ARQ worker startup hook (§14, issue 5).

Covers:
  - processing → queued reset on crash recovery
  - extracting → extraction_queued reset on crash recovery
  - extraction_queued chunks re-enqueued when ctx['redis'] is set
  - re-enqueue skipped gracefully when ctx['redis'] is absent
  - ctx populated with engine and settings after startup
"""

import uuid
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest
import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession

from api.config import Settings
from api.database import create_engine
from workers.ingestion import startup

pytestmark = pytest.mark.asyncio

_SYSTEM_USER_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")


async def _insert_ingestion_and_chunk(
    test_settings: Settings, chunk_status: str
) -> tuple[uuid.UUID, uuid.UUID]:
    ingestion_id = uuid.uuid4()
    chunk_id = uuid.uuid4()
    engine = create_engine(test_settings)
    async with engine.begin() as conn:
        await conn.execute(
            sa.text("""
                INSERT INTO ingestions
                  (id, source_type, status, created_by, source_sha256)
                VALUES (:id, 'pdf', 'ready', :user, :sha)
                ON CONFLICT DO NOTHING
            """),
            {"id": ingestion_id, "user": _SYSTEM_USER_ID, "sha": uuid.uuid4().hex},
        )
        await conn.execute(
            sa.text("""
                INSERT INTO ingestion_chunks
                  (id, ingestion_id, chunk_index, section_title, section_level,
                   text, text_preview, word_count, chunk_status, is_scanned, candidate_count)
                VALUES (:id, :iid, 0, 'S', 1, 'text', 'text', 1, :status, false, 0)
            """),
            {"id": chunk_id, "iid": ingestion_id, "status": chunk_status},
        )
    await engine.dispose()
    return ingestion_id, chunk_id


async def _get_chunk_status(test_settings: Settings, chunk_id: uuid.UUID) -> str:
    engine = create_engine(test_settings)
    async with AsyncSession(engine) as session:
        row = (
            await session.execute(
                sa.text("SELECT chunk_status FROM ingestion_chunks WHERE id = :id"),
                {"id": chunk_id},
            )
        ).fetchone()
    await engine.dispose()
    assert row is not None
    return str(row[0])


# ---------------------------------------------------------------------------
# processing → queued reset
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_startup_resets_processing_to_queued(test_settings: Settings) -> None:
    _, chunk_id = await _insert_ingestion_and_chunk(test_settings, "processing")

    with patch("workers.common.get_settings", return_value=test_settings):
        ctx: dict[str, Any] = {}
        await startup(ctx)
        await ctx["db_engine"].dispose()

    assert await _get_chunk_status(test_settings, chunk_id) == "queued"


# ---------------------------------------------------------------------------
# extracting → extraction_queued reset
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_startup_resets_extracting_to_extraction_queued(test_settings: Settings) -> None:
    _, chunk_id = await _insert_ingestion_and_chunk(test_settings, "extracting")

    with patch("workers.common.get_settings", return_value=test_settings):
        ctx: dict[str, Any] = {}
        await startup(ctx)
        await ctx["db_engine"].dispose()

    assert await _get_chunk_status(test_settings, chunk_id) == "extraction_queued"


# ---------------------------------------------------------------------------
# Re-enqueue with redis present (issue 5 core path)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_startup_reenqueues_extraction_queued_chunks(test_settings: Settings) -> None:
    _, chunk_id = await _insert_ingestion_and_chunk(test_settings, "extraction_queued")

    mock_arq = AsyncMock()
    mock_arq.enqueue_job = AsyncMock()

    with patch("workers.common.get_settings", return_value=test_settings):
        ctx: dict[str, Any] = {"redis": mock_arq}
        await startup(ctx)
        await ctx["db_engine"].dispose()

    called_chunk_ids = [
        call.kwargs["chunk_id"]
        for call in mock_arq.enqueue_job.call_args_list
        if call.args[0] == "extract_chunk"
    ]
    assert str(chunk_id) in called_chunk_ids


# ---------------------------------------------------------------------------
# No redis → re-enqueue skipped cleanly
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_startup_skips_reenqueue_without_redis(test_settings: Settings) -> None:
    _, chunk_id = await _insert_ingestion_and_chunk(test_settings, "extraction_queued")

    with patch("workers.common.get_settings", return_value=test_settings):
        ctx: dict[str, Any] = {}
        await startup(ctx)  # must not raise
        await ctx["db_engine"].dispose()

    # chunk remains extraction_queued — no re-enqueue happened
    assert await _get_chunk_status(test_settings, chunk_id) == "extraction_queued"


# ---------------------------------------------------------------------------
# ctx is populated after startup
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_startup_populates_ctx(test_settings: Settings) -> None:
    with patch("workers.common.get_settings", return_value=test_settings):
        ctx: dict[str, Any] = {}
        await startup(ctx)
        await ctx["db_engine"].dispose()

    assert "db_engine" in ctx
    assert "settings" in ctx
    assert ctx["settings"].app_env == "test"
