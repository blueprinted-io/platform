"""core_governed_schema

Revision ID: b4c5d6e7f8a9
Revises: ee74faf5ad0a
Create Date: 2026-05-13 12:00:00.000000+00:00

Creates all core governed record tables:
  facts, concepts, principles, tasks (+ sub-tables), workflows (+ sub-tables),
  relationships (stub), review_claims (Sprint 5).

Enables the pgvector extension before creating vector(1536) columns.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector  # type: ignore[import-untyped]

revision: str = "b4c5d6e7f8a9"
down_revision: str | None = "ee74faf5ad0a"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _lifecycle_cols() -> list[sa.Column]:
    """Return fresh lifecycle column instances for each table.

    ForeignKey objects cannot be reused across tables, so this must be called
    once per create_table invocation.
    """
    return [
        sa.Column("record_id", sa.UUID(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("status", sa.Text(), nullable=False, server_default="draft"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("created_by", sa.UUID(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("updated_by", sa.UUID(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reviewed_by", sa.UUID(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("change_note", sa.Text(), nullable=True),
        sa.Column("needs_review_flag", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("needs_review_note", sa.Text(), nullable=True),
    ]


def upgrade() -> None:
    # pgvector extension must exist before any vector(1536) column is created.
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    op.create_table(
        "facts",
        sa.Column("id", sa.UUID(), nullable=False),
        *_lifecycle_cols(),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("tags", sa.ARRAY(sa.String()), server_default="{}", nullable=False),
        sa.Column("embedding", Vector(1536), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_facts_record_id", "facts", ["record_id"])

    op.create_table(
        "concepts",
        sa.Column("id", sa.UUID(), nullable=False),
        *_lifecycle_cols(),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("explanation", sa.Text(), nullable=False),
        sa.Column("analogies", sa.Text(), nullable=True),
        sa.Column("tags", sa.ARRAY(sa.String()), server_default="{}", nullable=False),
        sa.Column("embedding", Vector(1536), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_concepts_record_id", "concepts", ["record_id"])

    op.create_table(
        "principles",
        sa.Column("id", sa.UUID(), nullable=False),
        *_lifecycle_cols(),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("explanation", sa.Text(), nullable=False),
        sa.Column("analogies", sa.Text(), nullable=True),
        sa.Column("domain", sa.Text(), nullable=True),
        sa.Column("tags", sa.ARRAY(sa.String()), server_default="{}", nullable=False),
        sa.Column("ingestion_id", sa.UUID(), nullable=True),
        sa.Column("embedding", Vector(1536), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_principles_record_id", "principles", ["record_id"])

    op.create_table(
        "tasks",
        sa.Column("id", sa.UUID(), nullable=False),
        *_lifecycle_cols(),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("outcome", sa.Text(), nullable=False),
        sa.Column("procedure_name", sa.Text(), nullable=False),
        sa.Column("domain", sa.Text(), nullable=True),
        sa.Column("software_name", sa.Text(), nullable=True),
        sa.Column("software_version", sa.Text(), nullable=True),
        sa.Column("media_url", sa.Text(), nullable=True),
        sa.Column("ingestion_id", sa.UUID(), nullable=True),
        sa.Column("has_deprecated_fact_ref", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("has_deprecated_concept_ref", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("tags", sa.ARRAY(sa.String()), server_default="{}", nullable=False),
        sa.Column("embedding", Vector(1536), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_tasks_record_id", "tasks", ["record_id"])

    op.create_table(
        "task_steps",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("task_id", sa.UUID(), sa.ForeignKey("tasks.id"), nullable=False),
        sa.Column("order_index", sa.Integer(), nullable=False),
        sa.Column("step", sa.Text(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("completion", sa.Text(), nullable=False),
        sa.Column("irreversible", sa.Boolean(), server_default="false", nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_task_steps_task_id", "task_steps", ["task_id"])

    op.create_table(
        "task_step_actions",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("step_id", sa.UUID(), sa.ForeignKey("task_steps.id"), nullable=False),
        sa.Column("order_index", sa.Integer(), nullable=False),
        sa.Column("instruction", sa.Text(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_task_step_actions_step_id", "task_step_actions", ["step_id"])

    op.create_table(
        "task_fact_refs",
        # fact_record_id carries no DB-level FK: record_id is not unique across versions
        sa.Column("task_id", sa.UUID(), sa.ForeignKey("tasks.id"), nullable=False),
        sa.Column("fact_record_id", sa.UUID(), nullable=False),
        sa.Column("order_index", sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint("task_id", "fact_record_id"),
    )

    op.create_table(
        "task_concept_refs",
        sa.Column("task_id", sa.UUID(), sa.ForeignKey("tasks.id"), nullable=False),
        sa.Column("concept_record_id", sa.UUID(), nullable=False),
        sa.Column("order_index", sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint("task_id", "concept_record_id"),
    )

    op.create_table(
        "task_step_screenshots",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("step_id", sa.UUID(), sa.ForeignKey("task_steps.id"), nullable=False),
        sa.Column("order_index", sa.Integer(), nullable=False),
        sa.Column("storage_path", sa.Text(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_task_step_screenshots_step_id", "task_step_screenshots", ["step_id"])

    op.create_table(
        "workflows",
        sa.Column("id", sa.UUID(), nullable=False),
        *_lifecycle_cols(),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("objective", sa.Text(), nullable=False),
        sa.Column("domain", sa.Text(), nullable=True),
        sa.Column("tags", sa.ARRAY(sa.String()), server_default="{}", nullable=False),
        sa.Column("ingestion_id", sa.UUID(), nullable=True),
        sa.Column("has_incoming_task_change", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("has_pending_task_confirm", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("embedding", Vector(1536), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_workflows_record_id", "workflows", ["record_id"])

    op.create_table(
        "workflow_task_refs",
        sa.Column("workflow_id", sa.UUID(), sa.ForeignKey("workflows.id"), nullable=False),
        sa.Column("task_record_id", sa.UUID(), nullable=False),
        sa.Column("order_index", sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint("workflow_id", "task_record_id"),
    )

    op.create_table(
        "workflow_principle_refs",
        sa.Column("workflow_id", sa.UUID(), sa.ForeignKey("workflows.id"), nullable=False),
        sa.Column("principle_record_id", sa.UUID(), nullable=False),
        sa.Column("attached_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("attached_by", sa.UUID(), sa.ForeignKey("users.id"), nullable=False),
        sa.PrimaryKeyConstraint("workflow_id", "principle_record_id"),
    )

    # Relationships table — all writes rejected with HTTP 422 in v1 (§9.4)
    op.create_table(
        "relationships",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("source_id", sa.UUID(), nullable=False),
        sa.Column("source_type", sa.Text(), nullable=False),
        sa.Column("target_id", sa.UUID(), nullable=False),
        sa.Column("target_type", sa.Text(), nullable=False),
        sa.Column("kind", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("created_by", sa.UUID(), nullable=False),
        sa.Column("agent_suggested", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )

    # Review claims — Sprint 5 adds the API; table created here for schema completeness (§8.2)
    op.create_table(
        "review_claims",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("entity_type", sa.Text(), nullable=False),
        sa.Column("entity_id", sa.UUID(), nullable=False),
        sa.Column("claimed_by", sa.UUID(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("claimed_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("released_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_review_claims_entity", "review_claims", ["entity_type", "entity_id"])


def downgrade() -> None:
    op.drop_table("review_claims")
    op.drop_table("relationships")
    op.drop_table("workflow_principle_refs")
    op.drop_table("workflow_task_refs")
    op.drop_table("workflows")
    op.drop_table("task_step_screenshots")
    op.drop_table("task_concept_refs")
    op.drop_table("task_fact_refs")
    op.drop_table("task_step_actions")
    op.drop_table("task_steps")
    op.drop_table("tasks")
    op.drop_table("principles")
    op.drop_table("concepts")
    op.drop_table("facts")
