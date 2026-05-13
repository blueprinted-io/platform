"""Alembic migration environment.

Uses the synchronous psycopg2 driver for CLI migrations (run outside the async
event loop). The async engine in api/database.py is for application runtime only.

Multi-tenant aware from the start: the system schema (public) is migrated first,
then each tenant schema in turn. Sprint 1 has no tenant schemas — this path is
stubbed for Sprint 4 when the first tenant schema migration is written.
"""

import os
from logging.config import fileConfig

from alembic import context
from sqlalchemy import create_engine, pool

import api.models  # noqa: F401 — registers all ORM models in Base.metadata
from api.database import Base

# Alembic Config object — provides access to .ini file values
config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def get_url() -> str:
    url = os.environ.get("DATABASE_URL_SYNC", "")
    if not url:
        raise RuntimeError(
            "DATABASE_URL_SYNC environment variable is not set. "
            "Set it before running migrations."
        )
    return url


def run_migrations_offline() -> None:
    """Run migrations without a live database connection (generates SQL)."""
    context.configure(
        url=get_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations against a live database connection."""
    connectable = create_engine(get_url(), poolclass=pool.NullPool)

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
