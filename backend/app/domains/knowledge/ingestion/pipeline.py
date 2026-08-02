"""Orchestrates the ingestion sequence: load -> chunk -> embed -> upsert
(IMPLEMENTATION_PLAN.md Phase 2)."""

import logging
from pathlib import Path

from app.domains.knowledge.embeddings.embedding_service import EmbeddingService
from app.domains.knowledge.exceptions import TranscriptLoadError
from app.domains.knowledge.ingestion.chunking import chunk_segments
from app.domains.knowledge.ingestion.loaders import load_episode
from app.domains.knowledge.models import Episode
from app.domains.knowledge.repository import KnowledgeRepository, TranscriptChunkInsert

logger = logging.getLogger(__name__)

# Episode directories known to be unfit for ingestion, keyed by the
# `episodes/{name}/` folder name:
#   - "andy-raskin_": a confirmed content duplicate of "andy-raskin" (same
#     video_id, near byte-identical transcript.md).
#   - "teaser_2021": a promotional teaser clip, not a real guest interview
#     (no real guest, missing duration_seconds in its frontmatter).
_EXCLUDED_EPISODE_DIR_NAMES = frozenset({"andy-raskin_", "teaser_2021"})


def discover_transcript_files(directory: str) -> list[Path]:
    """Find every ingestible transcript source file under `directory`.

    Two discovery rules, combined:
      - `*.json` directly inside `directory` (non-recursive) -- the
        original flat-directory-of-JSON-files layout.
      - `transcript.md` anywhere under `directory` (recursive) -- the real
        corpus's `episodes/{guest}/transcript.md` layout -- excluding any
        folder listed in `_EXCLUDED_EPISODE_DIR_NAMES`.

    Returns a sorted list so ingestion order is deterministic.
    """

    dir_path = Path(directory)
    if not dir_path.is_dir():
        raise TranscriptLoadError(f"Transcript directory not found: {directory}")

    json_files = dir_path.glob("*.json")
    markdown_files = (
        path for path in dir_path.rglob("transcript.md") if path.parent.name not in _EXCLUDED_EPISODE_DIR_NAMES
    )
    return sorted([*json_files, *markdown_files])


class IngestionPipeline:
    def __init__(self, repository: KnowledgeRepository, embedding_service: EmbeddingService) -> None:
        self._repository = repository
        self._embedding_service = embedding_service

    async def ingest_episode(self, source_path: str) -> Episode:
        """Ingest a single episode transcript file end-to-end.

        DATABASE_SCHEMA.md §8 risk #3: this always creates a *new* episode
        + chunk set — it does not detect or delete-and-replace an existing
        episode from the same source (`citations.transcript_chunk_id` is
        `ON DELETE RESTRICT`, so blind delete-and-replace on re-ingestion
        is unsafe). Re-running this on an already-ingested source will
        produce a duplicate episode; de-duplication is a follow-up, not
        required by the current scope.
        """

        raw_episode = load_episode(source_path)

        episode = await self._repository.create_episode(
            title=raw_episode.title,
            guest_name=raw_episode.guest_name,
            published_at=raw_episode.published_at,
            source_url=raw_episode.source_url,
        )

        drafts = chunk_segments(raw_episode.segments)
        if not drafts:
            logger.warning(
                "No chunks produced for %s (episode_id=%s, title=%r) -- nothing to embed/store",
                source_path, episode.id, episode.title,
            )
            return episode

        embeddings = await self._embedding_service.embed_batch([draft.content for draft in drafts])
        if len(embeddings) != len(drafts):
            raise TranscriptLoadError(
                f"{source_path}: embedding provider returned {len(embeddings)} vectors "
                f"for {len(drafts)} chunks"
            )

        inserts = [
            TranscriptChunkInsert(
                content=draft.content,
                embedding=embedding,
                start_offset=draft.start_offset,
                end_offset=draft.end_offset,
                start_timestamp_seconds=draft.start_timestamp_seconds,
                end_timestamp_seconds=draft.end_timestamp_seconds,
            )
            for draft, embedding in zip(drafts, embeddings, strict=True)
        ]
        await self._repository.create_transcript_chunks(episode_id=episode.id, chunks=inserts)

        logger.info(
            "Ingested %r (episode_id=%s): %d chunk(s) from %s",
            episode.title, episode.id, len(inserts), source_path,
        )
        return episode

    async def ingest_directory(self, directory: str) -> list[Episode]:
        """Ingest every transcript source file found under `directory` by
        `discover_transcript_files` (`*.json` non-recursive, plus
        `transcript.md` recursively, sorted for deterministic ordering)."""

        file_paths = discover_transcript_files(directory)
        if not file_paths:
            logger.warning("No transcript source files found in %s", directory)
            return []

        episodes: list[Episode] = []
        for file_path in file_paths:
            episodes.append(await self.ingest_episode(str(file_path)))
        return episodes
