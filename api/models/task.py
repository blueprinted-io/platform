"""Task ORM models.

§9.5 — governed procedure unit. References Facts and Concepts. Steps are owned by the Task.
task.irreversible is derived: True if any step has irreversible=True.
"""

import uuid

from pgvector.sqlalchemy import Vector
from sqlalchemy import ARRAY, Boolean, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from api.database import Base
from api.models.base import LifecycleMixin


class Task(LifecycleMixin, Base):
    __tablename__ = "tasks"

    title: Mapped[str] = mapped_column(Text, nullable=False)
    outcome: Mapped[str] = mapped_column(Text, nullable=False)
    procedure_name: Mapped[str] = mapped_column(Text, nullable=False)
    domain: Mapped[str] = mapped_column(Text, nullable=False)
    software_name: Mapped[str | None] = mapped_column(Text, nullable=True)
    software_version: Mapped[str | None] = mapped_column(Text, nullable=True)
    media_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    ingestion_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    has_deprecated_fact_ref: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )
    has_deprecated_concept_ref: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )
    tags: Mapped[list[str]] = mapped_column(
        ARRAY(String), nullable=False, default=list, server_default="{}"
    )
    embedding: Mapped[Vector | None] = mapped_column(Vector(1536), nullable=True)

    steps: Mapped[list["TaskStep"]] = relationship(
        "TaskStep",
        back_populates="task",
        order_by="TaskStep.order_index",
        cascade="all, delete-orphan",
    )
    fact_refs: Mapped[list["TaskFactRef"]] = relationship(
        "TaskFactRef",
        back_populates="task",
        order_by="TaskFactRef.order_index",
        cascade="all, delete-orphan",
    )
    concept_refs: Mapped[list["TaskConceptRef"]] = relationship(
        "TaskConceptRef",
        back_populates="task",
        order_by="TaskConceptRef.order_index",
        cascade="all, delete-orphan",
    )


class TaskStep(Base):
    __tablename__ = "task_steps"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    task_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tasks.id"), nullable=False, index=True
    )
    order_index: Mapped[int] = mapped_column(Integer, nullable=False)
    step: Mapped[str] = mapped_column(Text, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    completion: Mapped[str] = mapped_column(Text, nullable=False)
    irreversible: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )

    task: Mapped["Task"] = relationship("Task", back_populates="steps")
    actions: Mapped[list["TaskStepAction"]] = relationship(
        "TaskStepAction",
        back_populates="step",
        order_by="TaskStepAction.order_index",
        cascade="all, delete-orphan",
    )


class TaskStepAction(Base):
    __tablename__ = "task_step_actions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    step_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("task_steps.id"), nullable=False, index=True
    )
    order_index: Mapped[int] = mapped_column(Integer, nullable=False)
    instruction: Mapped[str] = mapped_column(Text, nullable=False)

    step: Mapped["TaskStep"] = relationship("TaskStep", back_populates="actions")


class TaskFactRef(Base):
    __tablename__ = "task_fact_refs"

    # fact_record_id is a stored reference (no DB-level FK — record_id is not unique)
    task_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tasks.id"), primary_key=True
    )
    fact_record_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True
    )
    order_index: Mapped[int] = mapped_column(Integer, nullable=False)

    task: Mapped["Task"] = relationship("Task", back_populates="fact_refs")


class TaskConceptRef(Base):
    __tablename__ = "task_concept_refs"

    task_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tasks.id"), primary_key=True
    )
    concept_record_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True
    )
    order_index: Mapped[int] = mapped_column(Integer, nullable=False)

    task: Mapped["Task"] = relationship("Task", back_populates="concept_refs")


class TaskStepScreenshot(Base):
    """Step screenshots — storage endpoints are not in Sprint 4."""

    __tablename__ = "task_step_screenshots"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    step_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("task_steps.id"), nullable=False, index=True
    )
    order_index: Mapped[int] = mapped_column(Integer, nullable=False)
    storage_path: Mapped[str] = mapped_column(Text, nullable=False)
