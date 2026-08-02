"""SQLAlchemy 2.0 models: `Episode`, `TranscriptChunk`, `Citation`
(DATABASE_SCHEMA.md §2, migrations #5–#7).

`TranscriptChunk.embedding` uses `pgvector.sqlalchemy.Vector` (dimension
1024, matching bge-m3's dense output — DATABASE_SCHEMA.md §5, "confirm
against the deployed Ollama model before first ingestion"). Both the
text-level offsets and the audio-time timestamps are present per
DATABASE_SCHEMA.md CHANGE 2.
"""

import uuid
from datetime import date, datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import CheckConstraint, ForeignKey, Text, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base

EMBEDDING_DIMENSION = 1024


class Episode(Base):
    """A single Lenny's Podcast episode (DOMAIN_MODEL.md §4.6)."""

    __tablename__ = "episodes"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    title: Mapped[str] = mapped_column(Text, nullable=False)
    guest_name: Mapped[str | None] = mapped_column(Text, default=None)
    published_at: Mapped[date | None] = mapped_column(default=None)
    source_url: Mapped[str | None] = mapped_column(Text, default=None)
    created_at: Mapped[datetime] = mapped_column(server_default=text("now()"))

    transcript_chunks: Mapped[list["TranscriptChunk"]] = relationship(
        back_populates="episode", cascade="all, delete-orphan", passive_deletes=True
    )


class TranscriptChunk(Base):
    """A retrievable, embedded segment of an episode's transcript
    (DOMAIN_MODEL.md §4.7). Populated exclusively by the offline ingestion
    pipeline (`ingestion/`) — read-only at request time.
    """

    __tablename__ = "transcript_chunks"
    __table_args__ = (
        CheckConstraint("end_offset > start_offset", name="ck_transcript_chunks_offsets_valid"),
        CheckConstraint(
            "end_timestamp_seconds > start_timestamp_seconds AND start_timestamp_seconds >= 0",
            name="ck_transcript_chunks_timestamps_valid",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    episode_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("episodes.id", ondelete="CASCADE"), nullable=False
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    embedding: Mapped[list[float]] = mapped_column(Vector(EMBEDDING_DIMENSION), nullable=False)
    start_offset: Mapped[int] = mapped_column(nullable=False)
    end_offset: Mapped[int] = mapped_column(nullable=False)
    start_timestamp_seconds: Mapped[int] = mapped_column(nullable=False)
    end_timestamp_seconds: Mapped[int] = mapped_column(nullable=False)
    created_at: Mapped[datetime] = mapped_column(server_default=text("now()"))

    episode: Mapped[Episode] = relationship(back_populates="transcript_chunks")


class Citation(Base):
    """Links a generated message to the transcript chunk(s) that grounded
    it (DOMAIN_MODEL.md §4.8). Note the `RESTRICT` delete rule on
    `transcript_chunk_id` — see DATABASE_SCHEMA.md §8 risk #3.
    """

    __tablename__ = "citations"
    __table_args__ = (
        UniqueConstraint("message_id", "transcript_chunk_id", name="uq_citations_message_chunk"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    message_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("messages.id", ondelete="CASCADE"), nullable=False
    )
    transcript_chunk_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("transcript_chunks.id", ondelete="RESTRICT"),
        nullable=False,
    )
    display_label: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(server_default=text("now()"))

    message: Mapped["Message"] = relationship("Message", back_populates="citations")
    transcript_chunk: Mapped["TranscriptChunk"] = relationship("TranscriptChunk")

    @property
    def excerpt(self) -> str:
        """The transcript excerpt this citation grounds its claim in —
        read from `transcript_chunk.content`, not stored redundantly on
        this row. Requires `transcript_chunk` to already be loaded (see
        `sessions/repository.py`'s nested `selectinload` chain) — this is
        a plain attribute access, never a lazy DB call, so it's safe for
        `CitationRead`'s `from_attributes=True` to resolve like any other
        column.
        """

        return self.transcript_chunk.content
