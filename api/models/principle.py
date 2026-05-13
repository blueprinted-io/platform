"""Principle ORM model.

§9.5 — foundational document-grain knowledge attached to Workflows. Full governed lifecycle.
"""

import uuid

from pgvector.sqlalchemy import Vector
from sqlalchemy import ARRAY, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from api.database import Base
from api.models.base import LifecycleMixin


class Principle(LifecycleMixin, Base):
    __tablename__ = "principles"

    title: Mapped[str] = mapped_column(Text, nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    explanation: Mapped[str] = mapped_column(Text, nullable=False)
    analogies: Mapped[str | None] = mapped_column(Text, nullable=True)
    domain: Mapped[str | None] = mapped_column(Text, nullable=True)
    tags: Mapped[list[str]] = mapped_column(
        ARRAY(String), nullable=False, default=list, server_default="{}"
    )
    ingestion_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    embedding: Mapped[Vector | None] = mapped_column(Vector(1536), nullable=True)
