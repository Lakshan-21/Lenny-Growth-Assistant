"""Text-generation calls against Claude (secondary/fallback path)."""

from collections.abc import AsyncIterator

from app.domains.providers.anthropic.client import AnthropicClient


class AnthropicProvider:
    """Satisfies the `providers.base.ModelProvider` protocol structurally —
    same shape as `providers.ollama.generation.OllamaProvider`, so
    `ModelGateway` (gateway.py) can treat both interchangeably."""

    def __init__(self, client: AnthropicClient) -> None:
        self._client = client

    async def generate(self, *, prompt: str, system: str | None = None) -> str:
        return await self._client.create_message(prompt=prompt, system=system)

    async def stream(self, *, prompt: str, system: str | None = None) -> AsyncIterator[str]:
        async for chunk in self._client.stream_message(prompt=prompt, system=system):
            yield chunk

    async def embed(self, *, text: str) -> list[float]:
        """Not supported — Claude has no embedding role in this architecture
        (see `providers.base.ModelProvider` docstring)."""

        raise NotImplementedError("Anthropic provider does not support embeddings in this architecture")
