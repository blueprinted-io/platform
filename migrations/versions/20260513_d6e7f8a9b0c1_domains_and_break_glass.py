"""domains_and_break_glass

Revision ID: d6e7f8a9b0c1
Revises: b4c5d6e7f8a9
Create Date: 2026-05-13 14:00:00.000000+00:00

Adds:
  - domains table (§7.1)
  - user_domains table (§7.1)
  - self_confirmed_by_admin BOOL on all five governed record tables (§5.1, §9.2)
  - domain NOT NULL constraint on tasks, workflows, principles (§7.4)

The domain NOT NULL migration is safe: no production records exist yet (Sprint 4
was just completed). The ALTER is preceded by a no-op UPDATE to satisfy any
tooling that validates pre-conditions before adding constraints.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "d6e7f8a9b0c1"
down_revision: str | None = "b4c5d6e7f8a9"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_GOVERNED_TABLES = ("facts", "concepts", "tasks", "workflows", "principles")
_DOMAIN_SCOPED_TABLES = ("tasks", "workflows", "principles")


def upgrade() -> None:
    op.create_table(
        "domains",
        sa.Column("name", sa.Text(), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
        sa.Column("created_by", sa.UUID(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("disabled_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.create_table(
        "user_domains",
        sa.Column("user_id", sa.UUID(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("domain", sa.Text(), sa.ForeignKey("domains.name"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
        sa.Column("created_by", sa.UUID(), sa.ForeignKey("users.id"), nullable=False),
        sa.PrimaryKeyConstraint("user_id", "domain"),
    )

    for table in _GOVERNED_TABLES:
        op.add_column(
            table,
            sa.Column(
                "self_confirmed_by_admin",
                sa.Boolean(),
                nullable=False,
                server_default="false",
            ),
        )

    for table in _DOMAIN_SCOPED_TABLES:
        # Ensure no NULLs exist before adding the NOT NULL constraint.
        # In practice no rows exist at this point in the rebuild.
        op.execute(f"UPDATE {table} SET domain = 'unknown' WHERE domain IS NULL")  # noqa: S608
        op.alter_column(table, "domain", existing_type=sa.Text(), nullable=False)


def downgrade() -> None:
    for table in _DOMAIN_SCOPED_TABLES:
        op.alter_column(table, "domain", existing_type=sa.Text(), nullable=True)

    for table in _GOVERNED_TABLES:
        op.drop_column(table, "self_confirmed_by_admin")

    op.drop_table("user_domains")
    op.drop_table("domains")
