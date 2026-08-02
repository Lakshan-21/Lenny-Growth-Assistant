"""Runtime `search(query_text, k, filters) -> TranscriptChunk[]`, called
in-process by the QA and Research skills only (no HTTP endpoint in MVP).
"""

import uuid

from app.domains.knowledge.embeddings.embedding_service import EmbeddingService
from app.domains.knowledge.repository import KnowledgeRepository
from app.domains.knowledge.schemas import TranscriptChunkRead


class RetrievalService:
    def __init__(self, repository: KnowledgeRepository, embedding_service: EmbeddingService) -> None:
        self._repository = repository
        self._embedding_service = embedding_service

    async def search(
        self,
        *,
        query_text: str,
        top_k: int = 8,
        episode_ids: list[uuid.UUID] | None = None,
    ) -> list[TranscriptChunkRead]:
        """Embed `query_text` and run a cosine-similarity search against
        `transcript_chunks` (DATABASE_SCHEMA.md §5 similarity search strategy).

        Returns an empty list when nothing is found (e.g. an empty corpus)
        rather than raising — "no grounding available" is a valid, expected
        outcome for the caller (`skills/qa/service.py`) to handle
        explicitly, not an error condition at the retrieval layer.
        """

        query_embedding = await self._embedding_service.embed_text(query_text)
        chunks = await self._repository.similarity_search(
            query_embedding=query_embedding, top_k=top_k, episode_ids=episode_ids
        )
        return [TranscriptChunkRead.model_validate(chunk) for chunk in chunks]
