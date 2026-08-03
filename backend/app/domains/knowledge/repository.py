"""pgvector similarity-search queries and episode/chunk lookups.

Transaction ownership matches every other repository in this codebase
(sessions/repository.py, artifacts/repository.py): only `add()`/`flush()`
here, never `commit()`/`rollback()` — that's `app.database.session.get_db`'s
job for request-scoped calls, or the caller's explicit `db.commit()` for
standalone scripts (see `ingestion/cli.py`).
"""

import logging
import uuid
from dataclasses import dataclass
from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.domains.knowledge.models import Citation, Episode, TranscriptChunk

logger = logging.getLogger(__name__)

# Initial cosine-distance cutoff for `similarity_search` (retrieval pipeline
# review, recommendation #1). bge-m3, this corpus: sampling real queries via
# the retrieval-pipeline investigation's temporary logging showed genuinely
# on-topic chunks landing at distance ~0.34-0.48, while a topically-adjacent
# but not-actually-covered query ("personal branding strategies" against a
# corpus with no personal-branding content) landed at ~0.49-0.54, and a
# fully unrelated query at ~0.62-0.68 -- 0.48 sits in the empirical gap
# between the two closest clusters. Single-episode sample (57 chunks); treat
# as a first cut to be revisited once ingestion covers more of the corpus,
# not a permanently-correct number.
_MAX_COSINE_DISTANCE = 0.48


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

        Also excludes anything farther than `_MAX_COSINE_DISTANCE` (retrieval
        pipeline review, recommendation #1): an unbounded `ORDER BY ...
        LIMIT` always returns exactly `top_k` rows regardless of how distant
        they actually are, which is what let a query like "personal
        branding strategies" retrieve the closest-available-but-still-
        irrelevant coaching/career/values chunks when nothing in the corpus
        was actually on topic. If every candidate is farther than the
        threshold, this returns an empty list -- QA/Research already treat
        an empty result as "no grounding" and respond accordingly (their
        existing `if not ...chunks:` paths), so no new handling is needed
        there; this filter is the single point both skills share.

        Eager-loads `.episode` (`selectinload`) — required, not optional:
        `TranscriptChunkRead.episode` is read via `from_attributes` by
        `retrieval_service.py`, and accessing an unloaded relationship
        outside this call would raise `MissingGreenlet` under the async
        engine (same class of bug as the `sessions.messages` fix).
        """

        # The query additionally selects the cosine-distance expression
        # itself (`distance_expr.label(...)`) so it can both be filtered on
        # (`.where(...)` below) and logged (diagnostic logging retained from
        # the retrieval-pipeline investigation -- still useful to see what
        # passed/was excluded and at what distance).
        distance_expr = TranscriptChunk.embedding.cosine_distance(query_embedding)
        stmt = (
            select(TranscriptChunk, distance_expr.label("distance"))
            .options(selectinload(TranscriptChunk.episode))
            .where(distance_expr <= _MAX_COSINE_DISTANCE)
            .order_by(distance_expr)
            .limit(top_k)
        )
        if episode_ids:
            stmt = stmt.where(TranscriptChunk.episode_id.in_(episode_ids))

        result = await self._db.execute(stmt)
        rows = result.all()

        # DIAGNOSTIC LOGGING (retrieval-pipeline investigation,
        # personal-branding-returns-unrelated-chunks issue). Cosine
        # *distance* (0 = identical, larger = less similar) — not a
        # similarity score. Every row here already passed
        # `_MAX_COSINE_DISTANCE` (enforced in SQL above), so this now shows
        # the post-filter result set, not the raw top-k candidates.
        for chunk, distance in rows:
            logger.info(
                "RETRIEVAL_DEBUG chunk_id=%s distance=%.4f episode=%r timestamps=%d-%d content_preview=%r",
                chunk.id,
                distance,
                chunk.episode.title if chunk.episode else None,
                chunk.start_timestamp_seconds,
                chunk.end_timestamp_seconds,
                chunk.content[:150],
            )

        return [chunk for chunk, _distance in rows]

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
