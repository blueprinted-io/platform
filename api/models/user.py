"""User ORM model.

Users are provisioned just-in-time on first authenticated request. The OIDC
subject (sub) is the stable identity key; email and roles are synced from the
JWT on each request so Authentik remains the authoritative source.
"""

import uuid
from datetime import datetime

from sqlalchemy import ARRAY, Boolean, DateTime, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from api.database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    # OIDC subject — stable identity across token refreshes
    sub: Mapped[str] = mapped_column(Text, nullable=False, unique=True, index=True)
    email: Mapped[str] = mapped_column(Text, nullable=False)
    display_name: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Cache of roles from the last valid JWT; Authentik is authoritative
    roles: Mapped[list[str]] = mapped_column(
        ARRAY(String), nullable=False, server_default="{}"
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )
