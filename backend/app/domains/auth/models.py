"""SQLAlchemy 2.0 model: `Profile` (DATABASE_SCHEMA.md §2).

NOTE — structural deviation, flagged per task instructions: REPOSITORY_STRUCTURE.md's
`auth/` file listing does not include a `models.py` (it predates DATABASE_SCHEMA.md,
which later introduced the `profiles` table). `Profile` is placed here because the
`auth` domain is its natural owner (it extends Supabase's `auth.users`, which no other
domain touches). This file is additive only — no other part of REPOSITORY_STRUCTURE.md
is affected. Documentation itself is left unmodified; this gap should be reconciled
there in a future documentation pass.

`auth.users` itself is Supabase-managed and intentionally has no ORM mapping here —
`Profile.id` references it by qualified table name only, for FK/DDL purposes.
"""

import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class Profile(Base):
    """Optional profile data extending `auth.users` (DATABASE_SCHEMA.md §2).

    `auth.users` remains the source of truth for identity/credentials; this
    table is auto-provisioned by the `handle_new_user` DB trigger on
    `auth.users` insert — application code should not INSERT into this
    table directly, only SELECT/UPDATE.
    """

    __tablename__ = "profiles"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("auth.users.id", ondelete="CASCADE"),
        primary_key=True,
    )
    display_name: Mapped[str | None] = mapped_column(default=None)
    created_at: Mapped[datetime] = mapped_column(server_default=text("now()"))
    updated_at: Mapped[datetime] = mapped_column(server_default=text("now()"))
