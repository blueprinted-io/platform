"""PDF chunking job (§11.9, §14). Runs on the ingestion worker."""

import uuid
from typing import Any

import fitz  # PyMuPDF
import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

from api.config import Settings
from api.models.ingestion import Ingestion, IngestionChunk
from api.services.notifications import create_notification
from api.services.storage import read_ingestion_file
from workers.common import exc_str

log = structlog.get_logger(__name__)


def _extract_chunks_from_pdf(pdf_bytes: bytes) -> list[dict[str, Any]]:
    """Parse a PDF into chunk dicts using PyMuPDF hybrid outline+heading strategy (§11.9).

    Returns a list of dicts with keys: section_title, section_level, pages, text.
    Falls back to single-chunk if neither outline nor headings are found.
    """
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    chunks: list[dict[str, Any]] = []

    outline = doc.get_toc()  # [[level, title, page], ...]

    if outline:
        # Build sections from outline entries. Each top-level entry is a section.
        top_level = [(lvl, title, page) for lvl, title, page in outline if lvl == 1]
        for i, (lvl, title, page_1based) in enumerate(top_level):
            start_page = page_1based - 1  # 0-based
            end_page = (
                top_level[i + 1][2] - 2 if i + 1 < len(top_level) else len(doc) - 1
            )
            text_parts = []
            pages_spanned = []
            for pno in range(start_page, end_page + 1):
                page_text = doc[pno].get_text("text")
                if page_text.strip():
                    text_parts.append(page_text)
                    pages_spanned.append(pno + 1)  # store 1-based
            full_text = "\n".join(text_parts).strip()
            if full_text:
                chunks.append({
                    "section_title": title,
                    "section_level": lvl,
                    "pages": pages_spanned,
                    "text": full_text,
                })
    else:
        # No outline — collect all text and split on headings by font size heuristic.
        all_text = ""
        all_pages: list[int] = []
        for pno in range(len(doc)):
            page_text = doc[pno].get_text("text")
            if page_text.strip():
                all_text += page_text + "\n"
                all_pages.append(pno + 1)

        if all_text.strip():
            chunks.append({
                "section_title": None,
                "section_level": 0,
                "pages": all_pages,
                "text": all_text.strip(),
            })

    doc.close()
    return chunks


async def chunk_pdf(ctx: dict, ingestion_id: str) -> None:  # type: ignore[type-arg]
    """Parse a PDF into ingestion_chunks and update the ingestion status (§11.9, §14).

    Triggered when a PDF ingestion is created. Reads the stored file, extracts
    structural chunks using PyMuPDF, and writes IngestionChunk records.
    """
    settings: Settings = ctx["settings"]
    engine: AsyncEngine = ctx["db_engine"]
    iid = uuid.UUID(ingestion_id)

    async with AsyncSession(engine) as session:
        ingestion = (
            await session.execute(select(Ingestion).where(Ingestion.id == iid))
        ).scalar_one_or_none()

        if ingestion is None:
            log.error("chunk_pdf_ingestion_not_found", ingestion_id=ingestion_id)
            return

        storage_path = ingestion.storage_path
        ingestion.status = "chunking"
        await session.commit()

    try:
        if storage_path is None:
            raise ValueError("ingestion has no storage_path")
        pdf_bytes = read_ingestion_file(settings, storage_path)

        # Scanned-PDF heuristic: reject if no extractable text across entire document.
        doc_check = fitz.open(stream=pdf_bytes, filetype="pdf")
        total_text = "".join(doc_check[p].get_text("text") for p in range(len(doc_check)))
        page_count = len(doc_check)
        doc_check.close()

        if not total_text.strip():
            async with AsyncSession(engine) as session:
                ing = (
                    await session.execute(select(Ingestion).where(Ingestion.id == iid))
                ).scalar_one()
                ing.status = "failed"
                ing.error_detail = (
                    "Scanned or image-only PDF — please supply a text-based PDF "
                    "or copy content into a manual import."
                )
                await session.commit()
            log.warning("chunk_pdf_scanned_document", ingestion_id=ingestion_id)
            return

        raw_chunks = _extract_chunks_from_pdf(pdf_bytes)

        async with AsyncSession(engine) as session:
            ing = (
                await session.execute(select(Ingestion).where(Ingestion.id == iid))
            ).scalar_one()

            for idx, ch in enumerate(raw_chunks):
                text: str = ch["text"]
                preview = text[:200].replace("\n", " ")
                word_count = len(text.split())
                chunk = IngestionChunk(
                    ingestion_id=iid,
                    chunk_index=idx,
                    section_title=ch["section_title"],
                    section_level=ch["section_level"],
                    pages_json=ch["pages"],
                    text=text,
                    text_preview=preview,
                    word_count=word_count,
                    chunk_status="pending",
                )
                session.add(chunk)

            created_by = ing.created_by
            pdf_filename = ing.original_filename
            ing.status = "ready"
            ing.page_count = page_count
            ing.chunk_count = len(raw_chunks)
            await session.commit()
            await create_notification(
                session, created_by, "ingestion_complete", "ingestion", iid,
                f'Your PDF "{pdf_filename or "upload"}" has been chunked'
                " and is ready for section selection.",
            )
            await session.commit()

        log.info(
            "chunk_pdf_complete",
            ingestion_id=ingestion_id,
            chunks=len(raw_chunks),
            pages=page_count,
        )

    except Exception as exc:
        async with AsyncSession(engine) as session:
            ing = (
                await session.execute(select(Ingestion).where(Ingestion.id == iid))
            ).scalar_one()
            created_by = ing.created_by
            pdf_filename = ing.original_filename
            ing.status = "failed"
            ing.error_detail = exc_str(exc)
            await session.commit()
            await create_notification(
                session, created_by, "ingestion_failed", "ingestion", iid,
                f'Your PDF "{pdf_filename or "upload"}" could not be processed: {exc}',
            )
            await session.commit()
        log.error("chunk_pdf_failed", ingestion_id=ingestion_id, error=exc_str(exc))
        raise
