"""Playwright-based HTML ingestion jobs (§11.10, §11.11). Run on the ingestion worker.

Requires Playwright with Chromium: run `playwright install chromium` after
installing dependencies.
"""

import re
import uuid
from typing import Any
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser

import sqlalchemy as sa
import structlog
from playwright.async_api import Browser, async_playwright
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

from api.models.ingestion import Ingestion, IngestionChunk, IngestionNavPage
from api.models.settings import SystemSetting
from api.services.notifications import create_notification
from workers.common import exc_str

log = structlog.get_logger(__name__)

# JS expression that extracts heading-structured sections from the main content
# area. Returns [{level, title, text}, ...] — one entry per heading-bounded block.
# Falls back to a single entry for the full content if no headings are present.
_EXTRACT_SECTIONS_JS = """
() => {
    // Prefer <main>, then <article>, then <body>.
    const root = document.querySelector('main') ||
                 document.querySelector('article') ||
                 document.body;

    const headings = Array.from(root.querySelectorAll('h1,h2,h3,h4,h5,h6'));
    if (headings.length === 0) {
        const text = (root.innerText || '').trim();
        const title = document.title || null;
        return text ? [{level: 0, title: title, text: text}] : [];
    }

    const sections = [];
    for (let i = 0; i < headings.length; i++) {
        const h = headings[i];
        const level = parseInt(h.tagName[1], 10);
        const title = h.innerText.trim();
        // Collect all text nodes between this heading and the next heading.
        let text = '';
        let node = h.nextSibling;
        while (node && node !== headings[i + 1]) {
            if (node.innerText) text += node.innerText;
            else if (node.textContent) text += node.textContent;
            node = node.nextSibling;
        }
        sections.push({level: level, title: title, text: text.trim()});
    }
    return sections;
}
"""

# JS expression that finds navigable links within nav/aside/role=navigation.
# Returns [{url, text, depth}, ...] where depth is the nesting level of the
# containing <ul>/<ol> elements within each nav root (0 = direct child of root).
_EXTRACT_NAV_LINKS_JS = """
() => {
    const navRoots = Array.from(document.querySelectorAll(
        'nav, aside, [role="navigation"]'
    ));
    const seen = new Set();
    const links = [];
    for (const nav of navRoots) {
        for (const a of nav.querySelectorAll('a[href]')) {
            const href = a.href;
            if (!href || seen.has(href)) continue;
            if (!href.startsWith('http://') && !href.startsWith('https://')) continue;
            seen.add(href);
            // Count <ul>/<ol> ancestors between the <a> and the nav root.
            let depth = 0;
            let node = a.parentElement;
            while (node && node !== nav) {
                if (node.tagName === 'UL' || node.tagName === 'OL') depth++;
                node = node.parentElement;
            }
            links.push({
                url: href,
                text: (a.innerText || a.textContent || '').trim(),
                depth: depth,
            });
        }
    }
    return links;
}
"""


def _is_robots_allowed(url: str) -> bool:
    """Return True if robots.txt permits crawling url, False if disallowed."""
    parsed = urlparse(url)
    robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
    rp = RobotFileParser()
    rp.set_url(robots_url)
    try:
        rp.read()
    except Exception:
        # If robots.txt is unreachable, allow by default.
        return True
    return rp.can_fetch("*", url)


def _make_chunks_from_sections(
    sections: list[dict[str, Any]],
    ingestion_id: uuid.UUID,
    source_url: str | None = None,
) -> list[IngestionChunk]:
    """Convert extracted JS sections into IngestionChunk ORM objects."""
    chunks = []
    for i, section in enumerate(sections):
        text = section.get("text") or ""
        if not text.strip():
            continue
        preview = text[:200]
        word_count = len(re.findall(r"\w+", text))
        chunk = IngestionChunk(
            ingestion_id=ingestion_id,
            chunk_index=i,
            section_title=section.get("title"),
            section_level=section.get("level", 0),
            pages_json=None,  # HTML has no pages
            source_url=source_url,
            text=text,
            text_preview=preview,
            word_count=word_count,
            chunk_status="pending",
            is_scanned=False,
        )
        chunks.append(chunk)
    return chunks


async def _render_and_chunk(
    browser: Browser,
    url: str,
    ingestion_id: uuid.UUID,
    respect_robots: bool,
) -> list[IngestionChunk]:
    """Render a single URL with Playwright and return IngestionChunk objects."""
    if respect_robots and not _is_robots_allowed(url):
        raise ValueError(f"robots.txt disallows crawling {url}")

    page = await browser.new_page()
    try:
        response = await page.goto(url, wait_until="networkidle", timeout=30_000)
        if response is None or not response.ok:
            status = response.status if response else "no response"
            raise ValueError(f"Page returned HTTP {status}: {url}")

        sections: list[dict[str, Any]] = await page.evaluate(_EXTRACT_SECTIONS_JS)
    finally:
        await page.close()

    if not sections:
        raise ValueError(
            "No extractable content — page may require authentication "
            "or render client-only content"
        )

    return _make_chunks_from_sections(sections, ingestion_id, source_url=url)


async def crawl_html(
    ctx: dict,  # type: ignore[type-arg]
    ingestion_id: str,
    mode: str = "single",
) -> None:
    """Playwright-based HTML ingestion job (§11.10, §11.11).

    Single-page mode: renders the URL, chunks by headings, sets ingestion ready.
    Site-nav mode: discovers nav links, creates IngestionNavPage rows, sets ingestion ready.
    """
    engine: AsyncEngine = ctx["db_engine"]
    iid = uuid.UUID(ingestion_id)

    async with AsyncSession(engine) as session:
        ingestion = (
            await session.execute(select(Ingestion).where(Ingestion.id == iid))
        ).scalar_one_or_none()
        if ingestion is None:
            log.error("crawl_html_ingestion_not_found", ingestion_id=ingestion_id)
            return

        url = ingestion.source_url or ""
        ingestion.status = "chunking"
        await session.commit()

    respect_robots: bool = True
    try:
        async with AsyncSession(engine) as _s:
            result = await _s.execute(
                select(SystemSetting.value).where(
                    SystemSetting.key == "ingestion_html_respect_robots_txt"
                )
            )
            row = result.scalar_one_or_none()
            if row is not None:
                respect_robots = str(row).lower() not in ("false", "0", "no")
    except Exception as settings_exc:
        log.debug("crawl_html_robots_setting_lookup_failed", error=str(settings_exc))

    try:
        async with async_playwright() as pw:
            browser = await pw.chromium.launch(headless=True)
            try:
                if mode == "single":
                    chunks = await _render_and_chunk(browser, url, iid, respect_robots)

                    async with AsyncSession(engine) as session:
                        for chunk in chunks:
                            session.add(chunk)
                        ingestion_row = (
                            await session.execute(
                                select(Ingestion).where(Ingestion.id == iid)
                            )
                        ).scalar_one()
                        html_created_by = ingestion_row.created_by
                        ingestion_row.status = "ready"
                        ingestion_row.chunk_count = len(chunks)
                        await session.commit()
                        await create_notification(
                            session, html_created_by,
                            "ingestion_complete", "ingestion", iid,
                            f"Your HTML import is ready for section selection"
                            f" ({len(chunks)} sections found).",
                        )
                        await session.commit()

                    log.info(
                        "crawl_html_single_done",
                        ingestion_id=ingestion_id,
                        chunk_count=len(chunks),
                    )

                else:  # site-nav
                    if respect_robots and not _is_robots_allowed(url):
                        raise ValueError(f"robots.txt disallows crawling {url}")

                    page = await browser.new_page()
                    try:
                        response = await page.goto(url, wait_until="networkidle", timeout=30_000)
                        if response is None or not response.ok:
                            status_code = response.status if response else "no response"
                            raise ValueError(
                                f"Root URL returned HTTP {status_code}: {url}"
                            )
                        raw_links: list[dict[str, Any]] = await page.evaluate(
                            _EXTRACT_NAV_LINKS_JS
                        )
                    finally:
                        await page.close()

                    # Deduplicate and normalise to same origin by default.
                    root_origin = urlparse(url).netloc
                    seen_urls: set[str] = set()
                    nav_pages = []
                    for i, link in enumerate(raw_links):
                        link_url: str = link["url"]
                        if urlparse(link_url).netloc != root_origin:
                            continue
                        link_url_norm = link_url.rstrip("/")
                        if link_url_norm in seen_urls:
                            continue
                        seen_urls.add(link_url_norm)
                        nav_pages.append(
                            IngestionNavPage(
                                ingestion_id=iid,
                                url=link_url,
                                title=link["text"] or None,
                                nav_level=link.get("depth", 0) + 1,
                                nav_order=i,
                            )
                        )

                    async with AsyncSession(engine) as session:
                        for nav_page in nav_pages:
                            session.add(nav_page)
                        ingestion_row = (
                            await session.execute(
                                select(Ingestion).where(Ingestion.id == iid)
                            )
                        ).scalar_one()
                        sitenav_created_by = ingestion_row.created_by
                        ingestion_row.status = "ready"
                        await session.commit()
                        await create_notification(
                            session, sitenav_created_by,
                            "ingestion_complete", "ingestion", iid,
                            f"Your HTML site navigation has been crawled"
                            f" ({len(nav_pages)} pages discovered)."
                            " Select which pages to import.",
                        )
                        await session.commit()

                    log.info(
                        "crawl_html_sitenav_done",
                        ingestion_id=ingestion_id,
                        nav_page_count=len(nav_pages),
                    )
            finally:
                await browser.close()

    except Exception as exc:
        error_msg = exc_str(exc)
        log.error("crawl_html_failed", ingestion_id=ingestion_id, error=error_msg)
        async with AsyncSession(engine) as session:
            failed_row = (
                await session.execute(select(Ingestion).where(Ingestion.id == iid))
            ).scalar_one_or_none()
            if failed_row is not None:
                html_failed_by = failed_row.created_by
                failed_row.status = "failed"
                failed_row.error_detail = error_msg
                await session.commit()
                await create_notification(
                    session, html_failed_by, "ingestion_failed", "ingestion", iid,
                    f"Your HTML import failed: {error_msg}",
                )
                await session.commit()
        raise


async def render_nav_pages(
    ctx: dict,  # type: ignore[type-arg]
    ingestion_id: str,
) -> None:
    """Render selected nav pages and create ingestion_chunks (§11.11).

    Called after the operator selects pages via POST /nav-select.
    Each selected page is rendered individually; chunks are appended to the ingestion.
    After rendering, the ingestion remains ready for section selection (§11.5).
    """
    engine: AsyncEngine = ctx["db_engine"]
    iid = uuid.UUID(ingestion_id)

    async with AsyncSession(engine) as session:
        result = await session.execute(
            select(IngestionNavPage)
            .where(
                IngestionNavPage.ingestion_id == iid,
                IngestionNavPage.nav_status == "selected",
            )
            .order_by(IngestionNavPage.nav_order)
        )
        pages = result.scalars().all()

    if not pages:
        log.info("render_nav_pages_nothing_to_do", ingestion_id=ingestion_id)
        return

    respect_robots = True

    try:
        async with async_playwright() as pw:
            browser = await pw.chromium.launch(headless=True)
            try:
                existing_chunk_count: int = 0
                async with AsyncSession(engine) as session:
                    count_result = await session.execute(
                        sa.select(sa.func.count()).where(
                            IngestionChunk.ingestion_id == iid
                        )
                    )
                    existing_chunk_count = count_result.scalar_one()

                chunk_offset = existing_chunk_count

                for nav_page in pages:
                    try:
                        chunks = await _render_and_chunk(
                            browser, nav_page.url, iid, respect_robots
                        )
                        # Re-index chunks to not overlap with existing ones and
                        # stamp the source nav page so the UI can group by page.
                        for i, chunk in enumerate(chunks):
                            chunk.chunk_index = chunk_offset + i
                            chunk.nav_page_id = nav_page.id
                        chunk_offset += len(chunks)

                        async with AsyncSession(engine) as session:
                            for chunk in chunks:
                                session.add(chunk)
                            page_row = (
                                await session.execute(
                                    select(IngestionNavPage).where(
                                        IngestionNavPage.id == nav_page.id
                                    )
                                )
                            ).scalar_one()
                            page_row.nav_status = "rendered"
                            page_row.chunk_count = len(chunks)
                            await session.commit()

                        log.info(
                            "nav_page_rendered",
                            ingestion_id=ingestion_id,
                            nav_page_id=str(nav_page.id),
                            chunk_count=len(chunks),
                        )

                    except Exception as page_exc:
                        error_msg = str(page_exc)
                        log.error(
                            "nav_page_render_failed",
                            ingestion_id=ingestion_id,
                            nav_page_id=str(nav_page.id),
                            error=error_msg,
                        )
                        async with AsyncSession(engine) as session:
                            failed_page = (
                                await session.execute(
                                    select(IngestionNavPage).where(
                                        IngestionNavPage.id == nav_page.id
                                    )
                                )
                            ).scalar_one_or_none()
                            if failed_page is not None:
                                failed_page.nav_status = "failed"
                                failed_page.error_detail = error_msg
                                await session.commit()

                # Update total chunk count on ingestion.
                async with AsyncSession(engine) as session:
                    count_result = await session.execute(
                        sa.select(sa.func.count()).where(
                            IngestionChunk.ingestion_id == iid
                        )
                    )
                    total_chunks = count_result.scalar_one()
                    ingestion_row = (
                        await session.execute(select(Ingestion).where(Ingestion.id == iid))
                    ).scalar_one_or_none()
                    if ingestion_row is not None:
                        ingestion_row.chunk_count = total_chunks
                        await session.commit()

                log.info(
                    "render_nav_pages_done",
                    ingestion_id=ingestion_id,
                    pages_processed=len(pages),
                    total_chunks=chunk_offset,
                )
            finally:
                await browser.close()

    except Exception as exc:
        log.error("render_nav_pages_failed", ingestion_id=ingestion_id, error=exc_str(exc))
        raise
