"""Add ingestion_triage_estimates table; add triage_complete/extraction_queued chunk statuses (§11.5a, §11.8a).

Revision ID: 1a2b3c4d5e6f
Revises: f6a7b8c9d0e1
Create Date: 2026-05-27
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision: str = "1a2b3c4d5e6f"
down_revision: str | None = "f6a7b8c9d0e1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "ingestion_triage_estimates",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "ingestion_id",
            UUID(as_uuid=True),
            sa.ForeignKey("ingestions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "chunk_id",
            UUID(as_uuid=True),
            sa.ForeignKey("ingestion_chunks.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("record_type", sa.Text, nullable=False),
        sa.Column("approved_type", sa.Text, nullable=False),
        sa.Column("estimated_title", sa.Text, nullable=False),
        sa.Column("estimate_status", sa.Text, nullable=False, server_default="pending"),
        sa.Column(
            "merged_into_id",
            UUID(as_uuid=True),
            sa.ForeignKey("ingestion_triage_estimates.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("sort_order", sa.Integer, nullable=False),
    )
    op.create_index(
        "ix_ingestion_triage_estimates_chunk_id",
        "ingestion_triage_estimates",
        ["chunk_id"],
    )
    op.create_index(
        "ix_ingestion_triage_estimates_ingestion_id",
        "ingestion_triage_estimates",
        ["ingestion_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_ingestion_triage_estimates_ingestion_id")
    op.drop_index("ix_ingestion_triage_estimates_chunk_id")
    op.drop_table("ingestion_triage_estimates")
