"""Add unique constraint on (record_id, version) for tasks, workflows, principles.

Prevents duplicate draft versions being created under concurrent load.

Revision ID: 5d6e7f8a9b0c
Revises: 4c5d6e7f8a9b
Create Date: 2026-06-10
"""

from alembic import op

revision: str = "5d6e7f8a9b0c"
down_revision: str | None = "4c5d6e7f8a9b"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_unique_constraint("uq_tasks_record_version", "tasks", ["record_id", "version"])
    op.create_unique_constraint("uq_workflows_record_version", "workflows", ["record_id", "version"])
    op.create_unique_constraint("uq_principles_record_version", "principles", ["record_id", "version"])


def downgrade() -> None:
    op.drop_constraint("uq_principles_record_version", "principles", type_="unique")
    op.drop_constraint("uq_workflows_record_version", "workflows", type_="unique")
    op.drop_constraint("uq_tasks_record_version", "tasks", type_="unique")
