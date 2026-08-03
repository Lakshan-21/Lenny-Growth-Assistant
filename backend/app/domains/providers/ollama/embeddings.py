"""bge-m3 embedding calls against Ollama, via the `POST /api/embed` endpoint
(the batch-capable embeddings endpoint — accepts either a single string or
a list of strings as `input`, returning one vector per input in order).

Called directly by `knowledge/embeddings/embedding_service.py` — not routed
through `ModelGateway` (embeddings have no Claude fallback in this
architecture; see `providers.base.ModelProvider` docstring).

Embedding-placement note (Ollama configuration review): when
`Settings.OLLAMA_EMBEDDING_FORCE_CPU` is true (the default), every request
here sets Ollama's `options.num_gpu = 0`, forcing bge-m3 onto CPU so the
generation model (llama3.1) has the GPU to itself instead of the two
models evicting each other on every call — see that setting's docstring
for the measured before/after numbers. Generation requests
(`ollama/generation.py`) are untouched by this change — they never set
`num_gpu`, so they keep Ollama's default placement.
"""

import logging

from pydantic import BaseModel, ValidationError

from app.config import Settings
from app.domains.providers.exceptions import ProviderResponseError
from app.domains.providers.ollama.client import OllamaClient

logger = logging.getLogger(__name__)

# Matches `knowledge.models.EMBEDDING_DIMENSION`. Duplicated here rather
# than imported, to avoid a providers -> knowledge import (knowledge
# already depends on providers; importing the other way would be circular).
# See DATABASE_SCHEMA.md §5 on confirming this against the deployed model.
_EXPECTED_EMBEDDING_DIMENSION = 1024


class _EmbedRequest(BaseModel):
    """Request body for Ollama's `POST /api/embed`.

    `options` mirrors Ollama's per-request runtime-options object — only
    `num_gpu` is ever set here, and only for CPU-placement purposes.
    `embed_batch` dumps this with `exclude_none=True`, so `options` is
    omitted from the request entirely (not sent as `"options": null`) when
    `OLLAMA_EMBEDDING_FORCE_CPU=false`, preserving Ollama's own default
    placement behavior in that case.
    """

    model: str
    input: str | list[str]
    options: dict[str, int] | None = None


class _EmbedResponse(BaseModel):
    model: str
    embeddings: list[list[float]]


class OllamaEmbeddingsClient:
    def __init__(self, settings: Settings, client: OllamaClient | None = None) -> None:
        self._client = client or OllamaClient(settings=settings)
        self._model = settings.OLLAMA_EMBEDDING_MODEL
        self._force_cpu = settings.OLLAMA_EMBEDDING_FORCE_CPU

    async def embed(self, *, text: str) -> list[float]:
        """Embed a single string (retrieval query time)."""

        vectors = await self.embed_batch(texts=[text])
        return vectors[0]

    async def embed_batch(self, *, texts: list[str]) -> list[list[float]]:
        """Embed a batch of strings in one request (ingestion time).

        Validates both the response shape and that every returned vector
        has the expected dimensionality — a silent short/long vector would
        otherwise surface later as an opaque pgvector insert failure
        instead of a clear provider-layer error.
        """

        if not texts:
            return []

        options = {"num_gpu": 0} if self._force_cpu else None
        logger.info(
            "Ollama embedding request placement: %s (model=%r, batch_size=%d)",
            "CPU (num_gpu=0)" if self._force_cpu else "GPU (Ollama default placement)",
            self._model,
            len(texts),
        )

        request = _EmbedRequest(model=self._model, input=texts, options=options)
        raw = await self._client.post("/api/embed", request.model_dump(exclude_none=True))

        try:
            response = _EmbedResponse.model_validate(raw)
        except ValidationError as exc:
            raise ProviderResponseError(
                f"Ollama /api/embed response did not match the expected shape: {exc}"
            ) from exc

        if len(response.embeddings) != len(texts):
            raise ProviderResponseError(
                f"Ollama /api/embed returned {len(response.embeddings)} embeddings "
                f"for {len(texts)} inputs"
            )

        for index, vector in enumerate(response.embeddings):
            if len(vector) != _EXPECTED_EMBEDDING_DIMENSION:
                raise ProviderResponseError(
                    f"Ollama /api/embed returned a {len(vector)}-dimensional vector "
                    f"at index {index}, expected {_EXPECTED_EMBEDDING_DIMENSION} "
                    f"(model={self._model!r}) — confirm OLLAMA_EMBEDDING_MODEL matches "
                    f"the dimension baked into transcript_chunks.embedding (DATABASE_SCHEMA.md §5)"
                )

        return response.embeddings
