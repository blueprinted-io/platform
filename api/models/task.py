"""Task ORM models.

§9.5 — governed procedure unit. The atomic unit of knowledge in Blueprinted.
Facts and concepts are string arrays owned by the task. Steps are owned by the task.
Task.irreversible is derived: True if any step has irreversible=True.
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
    domain: Mapped[str] = mapped_column(Text, nullable=False)
    software_name: Mapped[str | None] = mapped_column(Text, nullable=True)
    software_version: Mapped[str | None] = mapped_column(Text, nullable=True)
    media_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    ingestion_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    facts: Mapped[list[str] | None] = mapped_column(ARRAY(Text), nullable=True)
    concepts: Mapped[list[str] | None] = mapped_column(ARRAY(Text), nullable=True)
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
    images: Mapped[list["TaskStepImage"]] = relationship(
        "TaskStepImage",
        back_populates="step",
        order_by="TaskStepImage.order_index",
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


class TaskStepImage(Base):
    __tablename__ = "task_step_images"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    step_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("task_steps.id"), nullable=False, index=True
    )
    order_index: Mapped[int] = mapped_column(Integer, nullable=False)
    storage_path: Mapped[str] = mapped_column(Text, nullable=False)
    caption: Mapped[str | None] = mapped_column(Text, nullable=True)

    step: Mapped["TaskStep"] = relationship("TaskStep", back_populates="images")
