"""The `ModelProvider` protocol both `ollama` and `anthropic` implement
(REPOSITORY_STRUCTURE.md §3: "generate, stream, embed")."""

from collections.abc import AsyncIterator
from typing import Protocol, runtime_checkable


@runtime_checkable
class ModelProvider(Protocol):
    """Structural interface for a single model provider.

    `embed` is part of the shared shape for interface uniformity, but per
    CONTEXT.md only Ollama's `bge-m3` is actually used for embeddings in
    this architecture — `AnthropicProvider.embed` raises `NotImplementedError`
    (there is no Claude-embedding fallback path; see `knowledge/embeddings/
    embedding_service.py`, which calls Ollama directly rather than through
    `ModelGateway`).
    """

    async def generate(self, *, prompt: str, system: str | None = None) -> str:
        """Non-streaming text generation."""
        ...

    def stream(self, *, prompt: str, system: str | None = None) -> AsyncIterator[str]:
        """Streaming text generation (token/chunk iterator)."""
        ...

    async def embed(self, *, text: str) -> list[float]:
        """Embed a single string. See class docstring re: Anthropic."""
        ...
