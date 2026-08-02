"""SQLAlchemy 2.0 models: `Artifact`, `ResearchBrief` (DATABASE_SCHEMA.md §2,
migrations #8–#9).

The `research_briefs_check_artifact_type` trigger (DB-level cross-table
integrity guard) is not modeled here — it's enforced by Postgres, not the
ORM. `content_html` is deliberately absent: HTML is derived from
`content_markdown` at render time (ADR-4, ARCHITECTURE.md) — see
`renderers/html_renderer.py`.
"""

import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, ForeignKey, Text, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base

ARTIFACT_TYPES = ("qa_answer", "research_brief", "linkedin_post", "x_thread", "article")


class Artifact(Base):
    """A persisted, renderable output attached to a session/message
    (DOMAIN_MODEL.md §4.10)."""

    __tablename__ = "artifacts"
    __table_args__ = (
        CheckConstraint(f"artifact_type IN {ARTIFACT_TYPES}", name="ck_artifacts_artifact_type"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False
    )
    message_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("messages.id", ondelete="CASCADE"), nullable=False
    )
    artifact_type: Mapped[str] = mapped_column(Text, nullable=False)
    content_markdown: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(server_default=text("now()"))

    research_brief: Mapped["ResearchBrief | None"] = relationship(
        back_populates="artifact", uselist=False, cascade="all, delete-orphan", passive_deletes=True
    )


class ResearchBrief(Base):
    """Specializes an `Artifact` where `artifact_type = 'research_brief'`
    (DOMAIN_MODEL.md §4.9)."""

    __tablename__ = "research_briefs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    artifact_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("artifacts.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    topic: Mapped[str] = mapped_column(Text, nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(server_default=text("now()"))

    artifact: Mapped[Artifact] = relationship(back_populates="research_brief")
