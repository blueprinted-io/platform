"""Add return_severity to governed record tables (§9.2, Sprint 11 prep).

Revision ID: 3b4c5d6e7f8a
Revises: 2a3b4c5d6e7f
Create Date: 2026-06-10
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "3b4c5d6e7f8a"
down_revision: str | None = "2a3b4c5d6e7f"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    for table in ("tasks", "workflows", "principles"):
        op.add_column(table, sa.Column("return_severity", sa.Text(), nullable=True))


def downgrade() -> None:
    for table in ("tasks", "workflows", "principles"):
        op.drop_column(table, "return_severity")
