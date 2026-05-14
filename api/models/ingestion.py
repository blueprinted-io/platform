"""ORM models for the ingestion pipeline tables (SS11.13-SS11.15)."""

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Text, func
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from api.database import Base


class Ingestion(Base):
    """Ingestion job record — one per uploaded PDF, HTML source, or JSON payload (§11.13)."""

    __tablename__ = "ingestions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_type: Mapped[str] = mapped_column(Text, nullable=False)  # 'pdf' | 'html' | 'json'
    status: Mapped[str] = mapped_column(Text, nullable=False, default="pending")
    created_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )
    original_filename: Mapped[str | None] = mapped_column(Text, nullable=True)
    storage_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_sha256: Mapped[str | None] = mapped_column(Text, nullable=True)
    page_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    chunk_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    error_detail: Mapped[str | None] = mapped_column(Text, nullable=True)

    chunks: Mapped[list["IngestionChunk"]] = relationship(
        "IngestionChunk", back_populates="ingestion", order_by="IngestionChunk.chunk_index"
    )
    candidates: Mapped[list["IngestionCandidate"]] = relationship(
        "IngestionCandidate", back_populates="ingestion"
    )
    nav_pages: Mapped[list["IngestionNavPage"]] = relationship(
        "IngestionNavPage", back_populates="ingestion"
    )


class IngestionChunk(Base):
    """One structural section of an ingested source document (§11.14)."""

    __tablename__ = "ingestion_chunks"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    ingestion_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("ingestions.id", ondelete="CASCADE"), nullable=False
    )
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    section_title: Mapped[str | None] = mapped_column(Text, nullable=True)
    section_level: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    pages_json: Mapped[list[int] | None] = mapped_column(JSON, nullable=True)
    source_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    text_preview: Mapped[str] = mapped_column(Text, nullable=False)
    word_count: Mapped[int] = mapped_column(Integer, nullable=False)
    chunk_status: Mapped[str] = mapped_column(Text, nullable=False, default="pending")
    is_scanned: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )
    error_detail: Mapped[str | None] = mapped_column(Text, nullable=True)
    candidate_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    ingestion: Mapped[Ingestion] = relationship("Ingestion", back_populates="chunks")
    candidates: Mapped[list["IngestionCandidate"]] = relationship(
        "IngestionCandidate", back_populates="chunk"
    )


class IngestionCandidate(Base):
    """LLM-extracted candidate record awaiting human review (§11.8)."""

    __tablename__ = "ingestion_candidates"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    ingestion_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("ingestions.id", ondelete="CASCADE"), nullable=False
    )
    chunk_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("ingestion_chunks.id", ondelete="CASCADE"),
        nullable=True,  # NULL for JSON ingestions (no chunks)
    )
    record_type: Mapped[str] = mapped_column(Text, nullable=False)  # 'task' | 'principle'
    proposed_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    candidate_status: Mapped[str] = mapped_column(Text, nullable=False, default="pending")
    review_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    committed_record_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    reviewed_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    ingestion: Mapped[Ingestion] = relationship("Ingestion", back_populates="candidates")
    chunk: Mapped[IngestionChunk | None] = relationship(
        "IngestionChunk", back_populates="candidates"
    )


class IngestionNavPage(Base):
    """Discovered navigable page from an HTML site-nav crawl (§11.15)."""

    __tablename__ = "ingestion_nav_pages"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    ingestion_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("ingestions.id", ondelete="CASCADE"), nullable=False
    )
    url: Mapped[str] = mapped_column(Text, nullable=False)
    title: Mapped[str | None] = mapped_column(Text, nullable=True)
    nav_level: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    parent_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("ingestion_nav_pages.id"), nullable=True
    )
    nav_status: Mapped[str] = mapped_column(Text, nullable=False, default="pending")
    error_detail: Mapped[str | None] = mapped_column(Text, nullable=True)
    chunk_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    ingestion: Mapped[Ingestion] = relationship("Ingestion", back_populates="nav_pages")
