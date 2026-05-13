"""Fact ORM model.

§9.5 — atomic, declarative, verifiable statements. Domain-agnostic. Immutable once confirmed.
"""

from pgvector.sqlalchemy import Vector
from sqlalchemy import ARRAY, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from api.database import Base
from api.models.base import LifecycleMixin


class Fact(LifecycleMixin, Base):
    __tablename__ = "facts"

    title: Mapped[str] = mapped_column(Text, nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    tags: Mapped[list[str]] = mapped_column(
        ARRAY(String), nullable=False, default=list, server_default="{}"
    )
    # Dimension fixed at schema creation time — changing requires a migration (§12)
    embedding: Mapped[Vector | None] = mapped_column(Vector(1536), nullable=True)
