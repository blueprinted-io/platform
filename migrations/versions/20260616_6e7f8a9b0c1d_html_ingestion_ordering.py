"""Add nav_order to ingestion_nav_pages and nav_page_id FK to ingestion_chunks.

Fixes non-deterministic chunk ordering and loss of parent page context when
rendering multi-page HTML site-nav ingestions.

Revision ID: 6e7f8a9b0c1d
Revises: 5d6e7f8a9b0c
Create Date: 2026-06-16
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision: str = "6e7f8a9b0c1d"
down_revision: str | None = "5d6e7f8a9b0c"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "ingestion_nav_pages",
        sa.Column("nav_order", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "ingestion_chunks",
        sa.Column(
            "nav_page_id",
            UUID(as_uuid=True),
            nullable=True,
        ),
    )
    op.create_foreign_key(
        "fk_ingestion_chunks_nav_page_id",
        "ingestion_chunks",
        "ingestion_nav_pages",
        ["nav_page_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_ingestion_chunks_nav_page_id", "ingestion_chunks", type_="foreignkey"
    )
    op.drop_column("ingestion_chunks", "nav_page_id")
    op.drop_column("ingestion_nav_pages", "nav_order")
