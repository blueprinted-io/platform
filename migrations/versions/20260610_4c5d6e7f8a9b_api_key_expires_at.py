"""Add expires_at to api_keys table.

Revision ID: 4c5d6e7f8a9b
Revises: 3b4c5d6e7f8a
Create Date: 2026-06-10
"""

from alembic import op
import sqlalchemy as sa

revision: str = "4c5d6e7f8a9b"
down_revision: str | None = "3b4c5d6e7f8a"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "api_keys",
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("api_keys", "expires_at")
