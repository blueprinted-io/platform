"""Workflow ORM models.

§9.5 — ordered sequence of Tasks with attached Principles. The consumable product.
Workflow composition is always a human act — never produced by the ingestion pipeline.
"""

import uuid
from datetime import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import ARRAY, Boolean, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from api.database import Base
from api.models.base import LifecycleMixin


class Workflow(LifecycleMixin, Base):
    __tablename__ = "workflows"

    title: Mapped[str] = mapped_column(Text, nullable=False)
    objective: Mapped[str] = mapped_column(Text, nullable=False)
    domain: Mapped[str | None] = mapped_column(Text, nullable=True)
    tags: Mapped[list[str]] = mapped_column(
        ARRAY(String), nullable=False, default=list, server_default="{}"
    )
    ingestion_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    # Server-managed flags: set by background jobs when referenced tasks change
    has_incoming_task_change: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )
    has_pending_task_confirm: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )
    embedding: Mapped[Vector | None] = mapped_column(Vector(1536), nullable=True)

    task_refs: Mapped[list["WorkflowTaskRef"]] = relationship(
        "WorkflowTaskRef",
        back_populates="workflow",
        order_by="WorkflowTaskRef.order_index",
        cascade="all, delete-orphan",
    )
    principle_refs: Mapped[list["WorkflowPrincipleRef"]] = relationship(
        "WorkflowPrincipleRef",
        back_populates="workflow",
        cascade="all, delete-orphan",
    )


class WorkflowTaskRef(Base):
    __tablename__ = "workflow_task_refs"

    # task_record_id is a stored reference (no DB-level FK — record_id is not unique)
    workflow_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("workflows.id"), primary_key=True
    )
    task_record_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True
    )
    order_index: Mapped[int] = mapped_column(Integer, nullable=False)

    workflow: Mapped["Workflow"] = relationship("Workflow", back_populates="task_refs")


class WorkflowPrincipleRef(Base):
    __tablename__ = "workflow_principle_refs"

    workflow_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("workflows.id"), primary_key=True
    )
    principle_record_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True
    )
    attached_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    attached_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )

    workflow: Mapped["Workflow"] = relationship("Workflow", back_populates="principle_refs")
