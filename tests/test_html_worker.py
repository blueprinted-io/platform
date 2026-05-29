"""Tests for HTML ingestion workers and helpers (§11.10, §11.11).

Covers:
  _make_chunks_from_sections (pure unit):
    - empty sections list → no chunks
    - sections with empty text are skipped
    - word_count, text_preview, source_url, section_title populated correctly

  _is_robots_allowed (unit, RobotFileParser mocked):
    - allowed → True
    - disallowed → False
    - robots.txt unreachable (exception) → True (allow by default)

  crawl_html (Playwright mocked, real DB):
    - single mode: chunks written, ingestion → ready
    - single mode: page returns HTTP error → ingestion → failed, error_detail set
    - single mode: robots.txt disallows → ingestion → failed
    - site-nav mode: nav pages written, ingestion → ready
    - site-nav mode: root page HTTP error → ingestion → failed

  render_nav_pages (Playwright mocked, real DB):
    - selected pages rendered, chunks written, nav_status → rendered
    - no selected pages → nothing written, exits cleanly
    - one page fails, others succeed → failed page nav_status=failed, chunk count updated

Playwright is mocked throughout — no real browser is launched.
"""

import uuid
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

from api.config import Settings
from api.database import create_engine
from api.models.ingestion import IngestionChunk, IngestionNavPage
from workers.main import (
    _is_robots_allowed,
    _make_chunks_from_sections,
    crawl_html,
    render_nav_pages,
)

pytestmark = pytest.mark.asyncio

_SYSTEM_USER_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")
_TEST_URL = "http://docs.test/guide"
_TEST_SECTIONS = [
    {"level": 1, "title": "Introduction", "text": "Welcome to the guide."},
    {"level": 2, "title": "Setup", "text": "Install dependencies first."},
]
_TEST_NAV_LINKS = [
    {"url": "http://docs.test/page-1", "text": "Page 1"},
    {"url": "http://docs.test/page-2", "text": "Page 2"},
]


# ---------------------------------------------------------------------------
# Playwright mock factory
# ---------------------------------------------------------------------------

def _make_pw_mock(
    sections: list[dict[str, Any]] | None = None,
    page_ok: bool = True,
    page_status: int = 200,
    evaluate_side_effect: list[Any] | None = None,
) -> Any:
    """Return an async context manager that yields a mock Playwright instance."""
    mock_response = MagicMock()
    mock_response.ok = page_ok
    mock_response.status = page_status

    mock_page = AsyncMock()
    mock_page.goto.return_value = mock_response
    mock_page.close = AsyncMock()

    if evaluate_side_effect is not None:
        mock_page.evaluate.side_effect = evaluate_side_effect
    else:
        mock_page.evaluate.return_value = sections if sections is not None else []

    mock_browser = AsyncMock()
    mock_browser.new_page.return_value = mock_page
    mock_browser.close = AsyncMock()

    mock_chromium = AsyncMock()
    mock_chromium.launch.return_value = mock_browser

    mock_pw = AsyncMock()
    mock_pw.chromium = mock_chromium

    mock_ctx = AsyncMock()
    mock_ctx.__aenter__.return_value = mock_pw
    mock_ctx.__aexit__.return_value = None

    return mock_ctx


# ---------------------------------------------------------------------------
# DB helpers
# ---------------------------------------------------------------------------

async def _insert_html_ingestion(test_settings: Settings, url: str = _TEST_URL) -> uuid.UUID:
    iid = uuid.uuid4()
    engine = create_engine(test_settings)
    async with engine.begin() as conn:
        await conn.execute(
            sa.text("""
                INSERT INTO ingestions (id, source_type, status, created_by, source_url)
                VALUES (:id, 'html', 'pending', :user, :url)
            """),
            {"id": iid, "user": _SYSTEM_USER_ID, "url": url},
        )
    await engine.dispose()
    return iid


async def _insert_nav_page(
    test_settings: Settings,
    ingestion_id: uuid.UUID,
    url: str,
    nav_status: str = "selected",
) -> uuid.UUID:
    pid = uuid.uuid4()
    engine = create_engine(test_settings)
    async with engine.begin() as conn:
        await conn.execute(
            sa.text("""
                INSERT INTO ingestion_nav_pages (id, ingestion_id, url, nav_status, nav_level)
                VALUES (:id, :iid, :url, :status, 1)
            """),
            {"id": pid, "iid": ingestion_id, "url": url, "status": nav_status},
        )
    await engine.dispose()
    return pid


async def _get_ingestion_status(test_settings: Settings, iid: uuid.UUID) -> dict[str, Any]:
    engine = create_engine(test_settings)
    async with AsyncSession(engine) as session:
        row = (
            await session.execute(
                sa.text("SELECT status, error_detail, chunk_count FROM ingestions WHERE id = :id"),
                {"id": iid},
            )
        ).fetchone()
    await engine.dispose()
    assert row is not None
    return {"status": row[0], "error_detail": row[1], "chunk_count": row[2]}


async def _count_chunks(engine: AsyncEngine, ingestion_id: uuid.UUID) -> int:
    async with AsyncSession(engine) as session:
        return (
            await session.execute(
                sa.select(sa.func.count()).where(IngestionChunk.ingestion_id == ingestion_id)
            )
        ).scalar_one()


async def _count_nav_pages(engine: AsyncEngine, ingestion_id: uuid.UUID) -> int:
    async with AsyncSession(engine) as session:
        return (
            await session.execute(
                sa.select(sa.func.count()).where(IngestionNavPage.ingestion_id == ingestion_id)
            )
        ).scalar_one()


async def _get_nav_page_status(test_settings: Settings, page_id: uuid.UUID) -> str:
    engine = create_engine(test_settings)
    async with AsyncSession(engine) as session:
        row = (
            await session.execute(
                sa.text("SELECT nav_status FROM ingestion_nav_pages WHERE id = :id"),
                {"id": page_id},
            )
        ).fetchone()
    await engine.dispose()
    assert row is not None
    return str(row[0])


def _make_ctx(test_settings: Settings) -> dict[str, Any]:
    engine = create_engine(test_settings)
    return {"db_engine": engine, "settings": test_settings}


# ---------------------------------------------------------------------------
# _make_chunks_from_sections — pure unit tests
# ---------------------------------------------------------------------------

def test_make_chunks_empty_sections() -> None:
    result = _make_chunks_from_sections([], uuid.uuid4())
    assert result == []


def test_make_chunks_skips_empty_text() -> None:
    sections = [
        {"level": 1, "title": "Non-empty", "text": "Some content here."},
        {"level": 2, "title": "Empty", "text": "   "},
        {"level": 2, "title": "Also empty", "text": ""},
    ]
    result = _make_chunks_from_sections(sections, uuid.uuid4())
    assert len(result) == 1
    assert result[0].section_title == "Non-empty"


def test_make_chunks_populates_fields() -> None:
    iid = uuid.uuid4()
    url = "http://docs.test/page"
    sections = [{"level": 2, "title": "Steps", "text": "Run the command now."}]
    chunks = _make_chunks_from_sections(sections, iid, source_url=url)
    assert len(chunks) == 1
    c = chunks[0]
    assert c.ingestion_id == iid
    assert c.section_title == "Steps"
    assert c.section_level == 2
    assert c.source_url == url
    assert c.word_count == 4
    assert c.chunk_status == "pending"
    assert c.text_preview == "Run the command now."


def test_make_chunks_preview_truncated() -> None:
    long_text = "word " * 100
    chunks = _make_chunks_from_sections(
        [{"level": 0, "title": None, "text": long_text}], uuid.uuid4()
    )
    assert len(chunks[0].text_preview) <= 200


# ---------------------------------------------------------------------------
# _is_robots_allowed — unit tests
# ---------------------------------------------------------------------------

def test_is_robots_allowed_permits() -> None:
    mock_rp = MagicMock()
    mock_rp.can_fetch.return_value = True
    with patch("workers.main.RobotFileParser", return_value=mock_rp):
        assert _is_robots_allowed("http://example.com/page") is True


def test_is_robots_allowed_blocks() -> None:
    mock_rp = MagicMock()
    mock_rp.can_fetch.return_value = False
    with patch("workers.main.RobotFileParser", return_value=mock_rp):
        assert _is_robots_allowed("http://example.com/page") is False


def test_is_robots_allowed_unreachable_defaults_to_true() -> None:
    mock_rp = MagicMock()
    mock_rp.read.side_effect = OSError("connection refused")
    with patch("workers.main.RobotFileParser", return_value=mock_rp):
        assert _is_robots_allowed("http://example.com/page") is True


# ---------------------------------------------------------------------------
# crawl_html — single mode
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_crawl_html_single_writes_chunks(test_settings: Settings) -> None:
    iid = await _insert_html_ingestion(test_settings)
    ctx = _make_ctx(test_settings)

    pw_mock = _make_pw_mock(sections=_TEST_SECTIONS)
    with patch("workers.main.async_playwright", return_value=pw_mock):
        with patch("workers.main._is_robots_allowed", return_value=True):
            await crawl_html(ctx, str(iid), mode="single")

    ing = await _get_ingestion_status(test_settings, iid)
    assert ing["status"] == "ready"
    chunk_count = await _count_chunks(ctx["db_engine"], iid)
    assert chunk_count == 2
    await ctx["db_engine"].dispose()


@pytest.mark.asyncio
async def test_crawl_html_single_http_error_fails_ingestion(test_settings: Settings) -> None:
    iid = await _insert_html_ingestion(test_settings)
    ctx = _make_ctx(test_settings)

    pw_mock = _make_pw_mock(page_ok=False, page_status=403)
    with patch("workers.main.async_playwright", return_value=pw_mock):
        with patch("workers.main._is_robots_allowed", return_value=True):
            with pytest.raises(ValueError):
                await crawl_html(ctx, str(iid), mode="single")

    ing = await _get_ingestion_status(test_settings, iid)
    assert ing["status"] == "failed"
    assert ing["error_detail"] is not None
    await ctx["db_engine"].dispose()


@pytest.mark.asyncio
async def test_crawl_html_single_robots_blocked_fails_ingestion(test_settings: Settings) -> None:
    iid = await _insert_html_ingestion(test_settings)
    ctx = _make_ctx(test_settings)

    pw_mock = _make_pw_mock(sections=_TEST_SECTIONS)
    with patch("workers.main.async_playwright", return_value=pw_mock):
        with patch("workers.main._is_robots_allowed", return_value=False):
            with pytest.raises(ValueError):
                await crawl_html(ctx, str(iid), mode="single")

    ing = await _get_ingestion_status(test_settings, iid)
    assert ing["status"] == "failed"
    await ctx["db_engine"].dispose()


# ---------------------------------------------------------------------------
# crawl_html — site-nav mode
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_crawl_html_sitenav_writes_nav_pages(test_settings: Settings) -> None:
    iid = await _insert_html_ingestion(test_settings, url="http://docs.test/")
    ctx = _make_ctx(test_settings)

    pw_mock = _make_pw_mock(evaluate_side_effect=[_TEST_NAV_LINKS])
    with patch("workers.main.async_playwright", return_value=pw_mock):
        with patch("workers.main._is_robots_allowed", return_value=True):
            await crawl_html(ctx, str(iid), mode="site-nav")

    ing = await _get_ingestion_status(test_settings, iid)
    assert ing["status"] == "ready"
    nav_count = await _count_nav_pages(ctx["db_engine"], iid)
    assert nav_count == 2
    await ctx["db_engine"].dispose()


@pytest.mark.asyncio
async def test_crawl_html_sitenav_root_http_error_fails(test_settings: Settings) -> None:
    iid = await _insert_html_ingestion(test_settings, url="http://docs.test/")
    ctx = _make_ctx(test_settings)

    pw_mock = _make_pw_mock(page_ok=False, page_status=503)
    with patch("workers.main.async_playwright", return_value=pw_mock):
        with patch("workers.main._is_robots_allowed", return_value=True):
            with pytest.raises(ValueError):
                await crawl_html(ctx, str(iid), mode="site-nav")

    ing = await _get_ingestion_status(test_settings, iid)
    assert ing["status"] == "failed"
    await ctx["db_engine"].dispose()


# ---------------------------------------------------------------------------
# render_nav_pages
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_render_nav_pages_writes_chunks(test_settings: Settings) -> None:
    iid = await _insert_html_ingestion(test_settings)
    pid = await _insert_nav_page(test_settings, iid, "http://docs.test/page-1")
    ctx = _make_ctx(test_settings)

    pw_mock = _make_pw_mock(sections=_TEST_SECTIONS)
    with patch("workers.main.async_playwright", return_value=pw_mock):
        with patch("workers.main._is_robots_allowed", return_value=True):
            await render_nav_pages(ctx, str(iid))

    chunk_count = await _count_chunks(ctx["db_engine"], iid)
    assert chunk_count == 2
    assert await _get_nav_page_status(test_settings, pid) == "rendered"
    await ctx["db_engine"].dispose()


@pytest.mark.asyncio
async def test_render_nav_pages_no_selected_pages_exits_cleanly(test_settings: Settings) -> None:
    iid = await _insert_html_ingestion(test_settings)
    # Insert a page in 'pending' state (not selected) — should be ignored
    await _insert_nav_page(test_settings, iid, "http://docs.test/page-x", nav_status="pending")
    ctx = _make_ctx(test_settings)

    pw_mock = _make_pw_mock(sections=_TEST_SECTIONS)
    with patch("workers.main.async_playwright", return_value=pw_mock):
        await render_nav_pages(ctx, str(iid))  # must not raise

    chunk_count = await _count_chunks(ctx["db_engine"], iid)
    assert chunk_count == 0
    await ctx["db_engine"].dispose()


@pytest.mark.asyncio
async def test_render_nav_pages_partial_failure(test_settings: Settings) -> None:
    iid = await _insert_html_ingestion(test_settings)
    good_pid = await _insert_nav_page(test_settings, iid, "http://docs.test/good")
    bad_pid = await _insert_nav_page(test_settings, iid, "http://docs.test/bad")
    ctx = _make_ctx(test_settings)

    call_count = 0

    async def _side_effect_goto(*_args: Any, **_kwargs: Any) -> MagicMock:
        nonlocal call_count
        call_count += 1
        mock_resp = MagicMock()
        # First page succeeds, second fails
        mock_resp.ok = call_count == 1
        mock_resp.status = 200 if call_count == 1 else 500
        return mock_resp

    mock_page = AsyncMock()
    mock_page.goto.side_effect = _side_effect_goto
    mock_page.evaluate.return_value = _TEST_SECTIONS
    mock_page.close = AsyncMock()

    mock_browser = AsyncMock()
    mock_browser.new_page.return_value = mock_page
    mock_browser.close = AsyncMock()

    mock_pw = AsyncMock()
    mock_pw.chromium.launch.return_value = mock_browser

    mock_ctx = AsyncMock()
    mock_ctx.__aenter__.return_value = mock_pw
    mock_ctx.__aexit__.return_value = None

    with patch("workers.main.async_playwright", return_value=mock_ctx):
        with patch("workers.main._is_robots_allowed", return_value=True):
            await render_nav_pages(ctx, str(iid))

    # Good page got chunks; bad page recorded as failed
    chunk_count = await _count_chunks(ctx["db_engine"], iid)
    assert chunk_count == 2

    good_status = await _get_nav_page_status(test_settings, good_pid)
    bad_status = await _get_nav_page_status(test_settings, bad_pid)
    assert good_status == "rendered"
    assert bad_status == "failed"

    await ctx["db_engine"].dispose()
