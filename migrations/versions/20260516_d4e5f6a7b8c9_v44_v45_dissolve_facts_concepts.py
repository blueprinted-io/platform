"""v4.4/v4.5 — dissolve Facts and Concepts; procedure_name drop; images rename.

Revision ID: d4e5f6a7b8c9
Revises: c3d4e5f6a7b8
Create Date: 2026-05-16

v4.4: Facts and Concepts are dissolved as independently governed records.
  - Drop facts, concepts, task_fact_refs, task_concept_refs tables.
  - Drop has_deprecated_fact_ref, has_deprecated_concept_ref from tasks.
  - Rename raw_facts → facts, raw_concepts → concepts on tasks.

v4.5: Procedure field corrections.
  - Drop procedure_name from tasks (duplicated title).
  - Rename task_step_screenshots → task_step_images.
  - Add caption TEXT to task_step_images.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "d4e5f6a7b8c9"
down_revision: str | None = "c3d4e5f6a7b8"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # v4.4 — drop junction tables before governed tables (FK order)
    op.drop_table("task_concept_refs")
    op.drop_table("task_fact_refs")
    op.drop_table("concepts")
    op.drop_table("facts")

    # v4.4 — drop deprecated-ref flags from tasks
    op.drop_column("tasks", "has_deprecated_fact_ref")
    op.drop_column("tasks", "has_deprecated_concept_ref")

    # v4.4 — promote raw_facts/raw_concepts to first-class columns
    op.alter_column("tasks", "raw_facts", new_column_name="facts")
    op.alter_column("tasks", "raw_concepts", new_column_name="concepts")

    # v4.5 — drop procedure_name (duplicated title)
    op.drop_column("tasks", "procedure_name")

    # v4.5 — rename screenshots table and add caption
    op.rename_table("task_step_screenshots", "task_step_images")
    op.add_column("task_step_images", sa.Column("caption", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("task_step_images", "caption")
    op.rename_table("task_step_images", "task_step_screenshots")

    op.add_column("tasks", sa.Column("procedure_name", sa.Text(), nullable=True))

    op.alter_column("tasks", "concepts", new_column_name="raw_concepts")
    op.alter_column("tasks", "facts", new_column_name="raw_facts")

    op.add_column(
        "tasks",
        sa.Column(
            "has_deprecated_concept_ref",
            sa.Boolean(),
            nullable=False,
            server_default="false",
        ),
    )
    op.add_column(
        "tasks",
        sa.Column(
            "has_deprecated_fact_ref",
            sa.Boolean(),
            nullable=False,
            server_default="false",
        ),
    )

    # Recreating the governed tables on downgrade — schema only, no data.
    op.create_table(
        "facts",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("record_id", sa.UUID(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("tags", sa.ARRAY(sa.Text()), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "concepts",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("record_id", sa.UUID(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("explanation", sa.Text(), nullable=False),
        sa.Column("analogies", sa.Text(), nullable=True),
        sa.Column("tags", sa.ARRAY(sa.Text()), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "task_fact_refs",
        sa.Column("task_id", sa.UUID(), nullable=False),
        sa.Column("fact_record_id", sa.UUID(), nullable=False),
        sa.Column("order_index", sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint("task_id", "fact_record_id"),
    )
    op.create_table(
        "task_concept_refs",
        sa.Column("task_id", sa.UUID(), nullable=False),
        sa.Column("concept_record_id", sa.UUID(), nullable=False),
        sa.Column("order_index", sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint("task_id", "concept_record_id"),
    )
