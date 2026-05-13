"""Concept ORM model.

§9.5 — explanatory, contextual knowledge. Domain-agnostic. Immutable once confirmed.
"""

from pgvector.sqlalchemy import Vector
from sqlalchemy import ARRAY, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from api.database import Base
from api.models.base import LifecycleMixin


class Concept(LifecycleMixin, Base):
    __tablename__ = "concepts"

    title: Mapped[str] = mapped_column(Text, nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    explanation: Mapped[str] = mapped_column(Text, nullable=False)
    analogies: Mapped[str | None] = mapped_column(Text, nullable=True)
    tags: Mapped[list[str]] = mapped_column(
        ARRAY(String), nullable=False, default=list, server_default="{}"
    )
    embedding: Mapped[Vector | None] = mapped_column(Vector(1536), nullable=True)
