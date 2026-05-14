"""Ingestion pipeline tables: ingestions, ingestion_chunks, ingestion_candidates, ingestion_nav_pages.

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "b2c3d4e5f6a7"
down_revision: str | None = "a1b2c3d4e5f6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "ingestions",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("source_type", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False, server_default="pending"),
        sa.Column("created_by", sa.UUID(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("original_filename", sa.Text(), nullable=True),
        sa.Column("storage_path", sa.Text(), nullable=True),
        sa.Column("source_url", sa.Text(), nullable=True),
        sa.Column("source_sha256", sa.Text(), nullable=True),
        sa.Column("page_count", sa.Integer(), nullable=True),
        sa.Column("chunk_count", sa.Integer(), nullable=True),
        sa.Column("error_detail", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_ingestions_created_by", "ingestions", ["created_by"])
    op.create_index("ix_ingestions_source_sha256", "ingestions", ["source_sha256"])

    op.create_table(
        "ingestion_chunks",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column(
            "ingestion_id",
            sa.UUID(),
            sa.ForeignKey("ingestions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("section_title", sa.Text(), nullable=True),
        sa.Column("section_level", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("pages_json", sa.JSON(), nullable=True),
        sa.Column("source_url", sa.Text(), nullable=True),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("text_preview", sa.Text(), nullable=False),
        sa.Column("word_count", sa.Integer(), nullable=False),
        sa.Column(
            "chunk_status", sa.Text(), nullable=False, server_default="pending"
        ),
        sa.Column(
            "is_scanned", sa.Boolean(), nullable=False, server_default="false"
        ),
        sa.Column("error_detail", sa.Text(), nullable=True),
        sa.Column("candidate_count", sa.Integer(), nullable=False, server_default="0"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_ingestion_chunks_ingestion_id", "ingestion_chunks", ["ingestion_id"]
    )
    op.create_index(
        "ix_ingestion_chunks_status", "ingestion_chunks", ["ingestion_id", "chunk_status"]
    )

    op.create_table(
        "ingestion_candidates",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column(
            "ingestion_id",
            sa.UUID(),
            sa.ForeignKey("ingestions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "chunk_id",
            sa.UUID(),
            sa.ForeignKey("ingestion_chunks.id", ondelete="CASCADE"),
            nullable=True,  # NULL for JSON ingestions which have no chunks
        ),
        sa.Column("record_type", sa.Text(), nullable=False),
        sa.Column("proposed_json", sa.JSON(), nullable=False),
        sa.Column(
            "candidate_status", sa.Text(), nullable=False, server_default="pending"
        ),
        sa.Column("review_note", sa.Text(), nullable=True),
        sa.Column("committed_record_id", sa.UUID(), nullable=True),
        sa.Column("reviewed_by", sa.UUID(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_ingestion_candidates_ingestion_id",
        "ingestion_candidates",
        ["ingestion_id"],
    )
    op.create_index(
        "ix_ingestion_candidates_chunk_id", "ingestion_candidates", ["chunk_id"]
    )

    op.create_table(
        "ingestion_nav_pages",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column(
            "ingestion_id",
            sa.UUID(),
            sa.ForeignKey("ingestions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("url", sa.Text(), nullable=False),
        sa.Column("title", sa.Text(), nullable=True),
        sa.Column("nav_level", sa.Integer(), nullable=False, server_default="1"),
        sa.Column(
            "parent_id",
            sa.UUID(),
            sa.ForeignKey("ingestion_nav_pages.id"),
            nullable=True,
        ),
        sa.Column(
            "nav_status", sa.Text(), nullable=False, server_default="pending"
        ),
        sa.Column("error_detail", sa.Text(), nullable=True),
        sa.Column("chunk_count", sa.Integer(), nullable=False, server_default="0"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_ingestion_nav_pages_ingestion_id",
        "ingestion_nav_pages",
        ["ingestion_id"],
    )


def downgrade() -> None:
    op.drop_table("ingestion_nav_pages")
    op.drop_table("ingestion_candidates")
    op.drop_table("ingestion_chunks")
    op.drop_table("ingestions")
