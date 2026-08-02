"""SQLAlchemy 2.0 declarative base shared by every domain's `models.py`.

DATABASE_SCHEMA.md is the source of truth for table/column/constraint
definitions — models here must mirror it exactly, not extend it.
"""

from sqlalchemy import Column, MetaData, Table
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase

# Explicit constraint-naming convention so Alembic autogenerate produces
# stable, predictable constraint/index names across migrations (standard
# SQLAlchemy recommendation; not a new architectural concept).
NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    """Shared declarative base. All domain models inherit from this."""

    metadata = MetaData(naming_convention=NAMING_CONVENTION)


# Minimal stub for Supabase's `auth.users` — NOT a model we own or manage
# (no migration in this repo ever issues CREATE/ALTER TABLE for it; auth.users
# is Supabase's, per CONTEXT.md). It's registered here purely so
# `ForeignKey("auth.users.id")` references in domain models (currently
# `auth.models.Profile.id`, `sessions.models.Session.user_id`) can be
# resolved by SQLAlchemy.
#
# Why this is required at all: a string-form ForeignKey target is resolved
# lazily against a real Table object in the same MetaData — not just at
# DDL-generation time, but whenever SQLAlchemy needs to walk FK dependencies,
# which includes ordinary `Session.flush()` (it topologically sorts tables
# by FK before issuing INSERTs). With no `auth.users` Table anywhere in
# `Base.metadata`, that walk fails with `NoReferencedTableError` — this is
# the bug this stub fixes. Only the referenced column (`id`) needs to exist
# here; flush() never issues DML against this table since no ORM class is
# mapped to it.
#
# IMPORTANT: `migrations/env.py` explicitly excludes schema "auth" from
# Alembic autogenerate comparisons (`include_object`) — without that
# exclusion, this stub being far narrower than the real `auth.users` would
# make autogenerate propose dropping every column Supabase actually has.
auth_users_table = Table(
    "users",
    Base.metadata,
    Column("id", UUID(as_uuid=True), primary_key=True),
    schema="auth",
)
