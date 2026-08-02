"""SQLAlchemy 2.0 models: `Session`, `Message` (DATABASE_SCHEMA.md §2, migrations #3–#4).

Mirrors DATABASE_SCHEMA.md exactly, including the `messages.role` CHECK
(user | assistant | system) and the `skill_used`-only-for-assistant guard.
Triggers (`touch_session_updated_at`) and the `profiles`-style auto-insert
pattern are DB-level concerns, not modeled here.
"""

import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, ForeignKey, Text, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base

MESSAGE_ROLES = ("user", "assistant", "system")
SKILL_TYPES = ("qa", "research", "ship30", "artifact")
DEFAULT_SESSION_TITLE = "New session"


class Session(Base):
    """A chat-based unit of work owned by a user (DOMAIN_MODEL.md §4.2)."""

    __tablename__ = "sessions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("auth.users.id", ondelete="CASCADE"),
        nullable=False,
    )
    title: Mapped[str] = mapped_column(Text, nullable=False, server_default=DEFAULT_SESSION_TITLE)
    created_at: Mapped[datetime] = mapped_column(server_default=text("now()"))
    updated_at: Mapped[datetime] = mapped_column(server_default=text("now()"))

    messages: Mapped[list["Message"]] = relationship(
        back_populates="session",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="Message.created_at",
    )


class Message(Base):
    """A single turn within a `Session` (DOMAIN_MODEL.md §4.3).

    `role` includes `system` alongside `user`/`assistant` (DATABASE_SCHEMA.md
    CHANGE 1) for router/skill-injected context, hand-off markers, and
    operational breadcrumbs — see that document for the full rationale.
    """

    __tablename__ = "messages"
    __table_args__ = (
        CheckConstraint(f"role IN {MESSAGE_ROLES}", name="ck_messages_role"),
        CheckConstraint(f"skill_used IS NULL OR skill_used IN {SKILL_TYPES}", name="ck_messages_skill_used"),
        CheckConstraint(
            "role = 'assistant' OR skill_used IS NULL",
            name="ck_messages_skill_used_only_for_assistant",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False
    )
    role: Mapped[str] = mapped_column(Text, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    skill_used: Mapped[str | None] = mapped_column(Text, default=None)
    created_at: Mapped[datetime] = mapped_column(server_default=text("now()"))

    session: Mapped[Session] = relationship(back_populates="messages")
    citations: Mapped[list["Citation"]] = relationship(
        "Citation",
        back_populates="message",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="Citation.created_at",
    )
