"""Knowledge domain schemas (Pydantic v2)."""

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class EpisodeRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    title: str
    guest_name: str | None = None
    published_at: date | None = None
    source_url: str | None = None


class TranscriptChunkRead(BaseModel):
    """Retrieval result shape — deliberately excludes `embedding` (never
    needed by callers once retrieval has already scored/ranked it)."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    episode_id: UUID
    content: str
    start_offset: int
    end_offset: int
    start_timestamp_seconds: int
    end_timestamp_seconds: int
    episode: EpisodeRead | None = None
    """Populated by the repository via a join when the caller needs
    episode metadata for citation display (title/guest/timestamp)."""


class CitationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    message_id: UUID
    transcript_chunk_id: UUID
    display_label: str
    created_at: datetime
