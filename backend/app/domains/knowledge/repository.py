"""pgvector similarity-search queries and episode/chunk lookups.

Transaction ownership matches every other repository in this codebase
(sessions/repository.py, artifacts/repository.py): only `add()`/`flush()`
here, never `commit()`/`rollback()` — that's `app.database.session.get_db`'s
job for request-scoped calls, or the caller's explicit `db.commit()` for
standalone scripts (see `ingestion/cli.py`).
"""

import uuid
from dataclasses import dataclass
from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.domains.knowledge.models import Citation, Episode, TranscriptChunk


@dataclass(frozen=True, slots=True)
class TranscriptChunkInsert:
    """Per-chunk input for `create_transcript_chunks`: a chunk's text/offset
    data (`ingestion.chunking.TranscriptChunkDraft`) plus its embedding.

    Deliberately not just "take a `TranscriptChunkDraft` and an embedding
    list" — kept as its own small type here (not imported from
    `ingestion.chunking`) so this repository doesn't depend on the
    ingestion subpackage; the dependency direction is ingestion ->
    repository, never the reverse.
    """

    content: str
    embedding: list[float]
    start_offset: int
    end_offset: int
    start_timestamp_seconds: int
    end_timestamp_seconds: int


class KnowledgeRepository:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def create_episode(
        self,
        *,
        title: str,
        guest_name: str | None,
        published_at: date | None,
        source_url: str | None,
    ) -> Episode:
        """Insert a new `Episode` row. Flushed immediately — ingestion needs
        the generated `id` right away to associate chunks with it."""

        episode = Episode(title=title, guest_name=guest_name, published_at=published_at, source_url=source_url)
        self._db.add(episode)
        await self._db.flush()
        return episode

    async def get_episode(self, episode_id: uuid.UUID) -> Episode | None:
        return await self._db.get(Episode, episode_id)

    async def create_transcript_chunks(
        self, *, episode_id: uuid.UUID, chunks: list[TranscriptChunkInsert]
    ) -> list[TranscriptChunk]:
        """Bulk-insert every chunk for one episode in a single flush
        (avoids one round trip per chunk for episodes with hundreds of
        chunks)."""

        rows = [
            TranscriptChunk(
                episode_id=episode_id,
                content=chunk.content,
                embedding=chunk.embedding,
                start_offset=chunk.start_offset,
                end_offset=chunk.end_offset,
                start_timestamp_seconds=chunk.start_timestamp_seconds,
                end_timestamp_seconds=chunk.end_timestamp_seconds,
            )
            for chunk in chunks
        ]
        self._db.add_all(rows)
        await self._db.flush()
        return rows

    async def similarity_search(
        self,
        *,
        query_embedding: list[float],
        top_k: int,
        episode_ids: list[uuid.UUID] | None = None,
    ) -> list[TranscriptChunk]:
        """`ORDER BY embedding <=> :query_embedding LIMIT :top_k` (cosine
        distance, matching the `idx_transcript_chunks_embedding` HNSW index
        and `vector_cosine_ops`, DATABASE_SCHEMA.md §5), optionally filtered
        by episode.

        Eager-loads `.episode` (`selectinload`) — required, not optional:
        `TranscriptChunkRead.episode` is read via `from_attributes` by
        `retrieval_service.py`, and accessing an unloaded relationship
        outside this call would raise `MissingGreenlet` under the async
        engine (same class of bug as the `sessions.messages` fix).
        """

        stmt = (
            select(TranscriptChunk)
            .options(selectinload(TranscriptChunk.episode))
            .order_by(TranscriptChunk.embedding.cosine_distance(query_embedding))
            .limit(top_k)
        )
        if episode_ids:
            stmt = stmt.where(TranscriptChunk.episode_id.in_(episode_ids))

        result = await self._db.execute(stmt)
        return list(result.scalars().all())

    async def create_citation(
        self,
        *,
        message_id: uuid.UUID,
        transcript_chunk_id: uuid.UUID,
        display_label: str,
    ) -> Citation:
        """Insert a new `Citation` row.

        Note: `uq_citations_message_chunk` (DATABASE_SCHEMA.md §2) rejects
        a duplicate (message_id, transcript_chunk_id) pair at the DB level
        — no need to pre-check here.
        """

        citation = Citation(message_id=message_id, transcript_chunk_id=transcript_chunk_id, display_label=display_label)
        self._db.add(citation)
        await self._db.flush()
        return citation
