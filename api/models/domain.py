"""Domain and UserDomain ORM models.

§7.1 — domain registry and user assignment
"""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from api.database import Base


class Domain(Base):
    __tablename__ = "domains"

    name: Mapped[str] = mapped_column(Text, primary_key=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    created_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    # NULL = active; non-NULL = soft-deleted (§7.1)
    disabled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class UserDomain(Base):
    __tablename__ = "user_domains"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), primary_key=True
    )
    domain: Mapped[str] = mapped_column(Text, ForeignKey("domains.name"), primary_key=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    created_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
