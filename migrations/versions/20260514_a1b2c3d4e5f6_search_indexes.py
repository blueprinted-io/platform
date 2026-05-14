"""Add GIN indexes for full-text search (§12).

Revision ID: a1b2c3d4e5f6
Revises: d6e7f8a9b0c1
"""

from alembic import op

revision: str = "a1b2c3d4e5f6"
down_revision: str | None = "d6e7f8a9b0c1"
branch_labels: None = None
depends_on: None = None

# tsvector expressions — must exactly match the expressions used in api/services/search.py
# so Postgres can use these indexes for the WHERE clause and ORDER BY ts_rank.
_INDEXES = [
    (
        "facts_fts_idx",
        "facts",
        "to_tsvector('english', title || ' ' || body)",
    ),
    (
        "concepts_fts_idx",
        "concepts",
        "to_tsvector('english', title || ' ' || summary || ' ' || explanation || ' ' || COALESCE(analogies, ''))",
    ),
    (
        "principles_fts_idx",
        "principles",
        "to_tsvector('english', title || ' ' || summary || ' ' || explanation || ' ' || COALESCE(analogies, ''))",
    ),
    (
        "tasks_fts_idx",
        "tasks",
        "to_tsvector('english', title || ' ' || outcome || ' ' || procedure_name || ' ' || COALESCE(software_name, '') || ' ' || COALESCE(software_version, ''))",
    ),
    (
        "workflows_fts_idx",
        "workflows",
        "to_tsvector('english', title || ' ' || objective)",
    ),
]


def upgrade() -> None:
    for idx_name, table, expr in _INDEXES:
        op.execute(f"CREATE INDEX {idx_name} ON {table} USING GIN ({expr})")


def downgrade() -> None:
    for idx_name, _table, _expr in _INDEXES:
        op.execute(f"DROP INDEX IF EXISTS {idx_name}")
