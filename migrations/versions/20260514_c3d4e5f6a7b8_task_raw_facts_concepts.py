"""Add raw_facts and raw_concepts to tasks for ingestion commit.

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-05-14

Facts and concepts extracted by the ingestion pipeline are string arrays, not
references to governed Fact/Concept records. These columns preserve that content
on the committed Task so it is not stranded in proposed_json.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "c3d4e5f6a7b8"
down_revision: str | None = "b2c3d4e5f6a7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("tasks", sa.Column("raw_facts", sa.ARRAY(sa.Text()), nullable=True))
    op.add_column("tasks", sa.Column("raw_concepts", sa.ARRAY(sa.Text()), nullable=True))


def downgrade() -> None:
    op.drop_column("tasks", "raw_concepts")
    op.drop_column("tasks", "raw_facts")
