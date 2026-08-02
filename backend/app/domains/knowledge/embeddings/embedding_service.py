"""Calls the Ollama provider's bge-m3 embedding endpoint for both ingestion
and query-time embedding.

Deliberately talks to `providers.ollama` directly rather than through
`providers.gateway.ModelGateway` — per CONTEXT.md, graceful degradation
(Ollama -> Claude fallback) applies to generation, not embeddings; `bge-m3`
has no Claude equivalent in this architecture.
"""

from app.domains.providers.ollama.embeddings import OllamaEmbeddingsClient


class EmbeddingService:
    def __init__(self, ollama_embeddings: OllamaEmbeddingsClient) -> None:
        self._ollama_embeddings = ollama_embeddings

    async def embed_text(self, text: str) -> list[float]:
        """Embed a single query string (retrieval time).

        Dimension/shape validation already happens in
        `OllamaEmbeddingsClient.embed_batch` (raises `ProviderResponseError`
        on a mismatch) — nothing to re-check here.
        """

        return await self._ollama_embeddings.embed(text=text)

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Embed a batch of transcript chunks (ingestion time)."""

        return await self._ollama_embeddings.embed_batch(texts=texts)
