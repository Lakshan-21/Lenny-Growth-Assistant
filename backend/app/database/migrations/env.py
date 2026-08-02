"""Alembic migration environment.

Async-aware: the app uses `create_async_engine`/asyncpg (database/session.py),
so migrations run against an async engine too, via `connection.run_sync(...)`
— the standard pattern for SQLAlchemy 2.0 async projects, rather than
pulling in a second, sync-only driver just for migrations.

`target_metadata` is `Base.metadata` after `app.database.models_registry`
has been imported, so every domain's models are registered before Alembic
compares the live database against the ORM (autogenerate) — see that
module's docstring for why this indirection exists.
"""

import asyncio
from logging.config import fileConfig

from sqlalchemy import Connection, pool
from sqlalchemy.ext.asyncio import async_engine_from_config

from alembic import context

# Import order matters here: `models_registry` must be imported before
# `target_metadata = Base.metadata` below, so every table is registered.
from app.config import get_settings
from app.database import models_registry  # noqa: F401
from app.database.base import Base

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

# DATABASE_URL is sourced from Settings (env-driven), not from alembic.ini,
# so migrations always run against the same connection string the app
# itself uses — no value is duplicated/hardcoded in alembic.ini.
config.set_main_option("sqlalchemy.url", get_settings().DATABASE_URL)


def include_object(object, name, type_, reflected, compare_to) -> bool:
    """Exclude Supabase-managed schemas from autogenerate comparison.

    `Base.metadata` now contains a minimal stub for `auth.users`
    (database/base.py) so ORM `ForeignKey("auth.users.id")` references can
    resolve (see that module's docstring). That stub is intentionally far
    narrower than the real table — without this exclusion, `alembic revision
    --autogenerate` would see "missing" columns/constraints versus the live
    `auth.users` and propose altering/dropping them. We never own that
    table, so autogenerate must never touch it.
    """

    if type_ == "table" and getattr(object, "schema", None) == "auth":
        return False
    return True


def run_migrations_offline() -> None:
    """Emit SQL to stdout without a live DB connection (`alembic upgrade
    head --sql`). Not the primary workflow for this project but kept for
    completeness / CI dry-run use.
    """

    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        include_object=include_object,
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata, include_object=include_object)

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Primary workflow: run migrations against a live async engine."""

    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
