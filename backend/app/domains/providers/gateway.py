"""The Model Gateway: attempts Ollama first, fails over to Claude on
timeout/health-check failure (graceful degradation, CONTEXT.md).

Emits a structured application-log entry per invocation (provider, whether
it was a fallback, latency) — no `ModelInvocation` database persistence in
MVP (REPOSITORY_STRUCTURE.md's MVP-simplification notes, DATABASE_SCHEMA.md
§8 risk #6).
"""

import logging
import time
from collections.abc import AsyncIterator

from app.domains.providers.base import ModelProvider
from app.domains.providers.exceptions import AllProvidersUnavailableError, ProviderUnavailableError

logger = logging.getLogger(__name__)


class ModelGateway:
    """Constructor-injected with both providers — every skill depends on
    this, never on `OllamaProvider`/`AnthropicProvider` directly."""

    def __init__(self, primary: ModelProvider, secondary: ModelProvider) -> None:
        self._primary = primary
        self._secondary = secondary

    async def generate(self, *, prompt: str, system: str | None = None) -> str:
        """Try `self._primary` (Ollama); on `ProviderUnavailableError`, fall
        back to `self._secondary` (Anthropic). Raises
        `AllProvidersUnavailableError` only if both fail — that is the one
        case PRD §6's "Availability" NFR allows to surface as a hard failure.
        """

        start = time.monotonic()
        try:
            result = await self._primary.generate(prompt=prompt, system=system)
            self._log_invocation(provider="ollama", was_fallback=False, start=start)
            return result
        except ProviderUnavailableError:
            logger.warning("Primary provider (ollama) unavailable, falling back to anthropic")

        try:
            result = await self._secondary.generate(prompt=prompt, system=system)
            self._log_invocation(provider="anthropic", was_fallback=True, start=start)
            return result
        except ProviderUnavailableError as exc:
            self._log_invocation(provider="anthropic", was_fallback=True, start=start, failed=True)
            raise AllProvidersUnavailableError() from exc

    async def stream(self, *, prompt: str, system: str | None = None) -> AsyncIterator[str]:
        """Streaming equivalent of `generate`.

        TODO: streaming failover is more delicate than non-streaming (the
        primary may fail mid-stream after already yielding partial output) —
        the strategy for that case (discard-and-restart on secondary vs.
        surface a partial-then-error result) is left as a TODO rather than
        guessed at, since it's a real product/UX decision.
        """

        raise NotImplementedError
        yield  # pragma: no cover - makes this an async generator for typing

    @staticmethod
    def _log_invocation(
        *, provider: str, was_fallback: bool, start: float, failed: bool = False
    ) -> None:
        logger.info(
            "model_invocation",
            extra={
                "provider": provider,
                "was_fallback": was_fallback,
                "failed": failed,
                "latency_ms": round((time.monotonic() - start) * 1000, 1),
            },
        )
