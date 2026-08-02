"""Claude SDK client wrapper.

Isolates the third-party `anthropic` SDK behind a narrow interface, same
rationale as `auth/supabase_client.py` and `providers/ollama/client.py`.
"""

from collections.abc import AsyncIterator

import anthropic

from app.config import Settings
from app.domains.providers.exceptions import ProviderUnavailableError

# Anthropic SDK conditions that mean "this request could not be served
# right now" — connection failure, timeout, or the model/service being
# unavailable (bad model name, overloaded, internal error, rate limited).
# These are exactly the categories `gateway.py`'s fallback contract expects
# (ProviderUnavailableError) — see that module's docstring.
#
# Deliberately NOT included: AuthenticationError, PermissionDeniedError,
# BadRequestError — these are configuration/programming errors, not
# transient unavailability. Masking a bad API key as "provider unavailable"
# would make misconfiguration silently indistinguishable from Anthropic
# actually being down; they're left to propagate and surface as a genuine
# 500, same as `OllamaClient.post()` not retrying non-retryable 4xx.
_UNAVAILABLE_EXCEPTIONS: tuple[type[Exception], ...] = (
    anthropic.APIConnectionError,
    anthropic.APITimeoutError,
    anthropic.NotFoundError,
    anthropic.OverloadedError,
    anthropic.InternalServerError,
    anthropic.RateLimitError,
)

_MAX_TOKENS = 4096


class AnthropicClient:
    def __init__(self, settings: Settings) -> None:
        self._model = settings.ANTHROPIC_MODEL
        # The SDK's own built-in retry (default max_retries=2) handles
        # transient connection blips within a single Anthropic call — the
        # Ollama -> Anthropic switch itself (gateway.py) is the
        # higher-level retry/fallback this task is about; no need to
        # duplicate a manual retry loop here the way OllamaClient does
        # (that one talks to a bare HTTP API with no SDK-level retry).
        self._client = anthropic.AsyncAnthropic(
            api_key=settings.ANTHROPIC_API_KEY,
            timeout=settings.ANTHROPIC_REQUEST_TIMEOUT_SECONDS,
        )

    async def create_message(self, *, prompt: str, system: str | None = None) -> str:
        """Non-streaming Messages API call. Raises `ProviderUnavailableError`
        on connection failure, timeout, or a model/service-unavailable
        response — see `_UNAVAILABLE_EXCEPTIONS`."""

        try:
            response = await self._client.messages.create(**self._build_kwargs(prompt=prompt, system=system))
        except _UNAVAILABLE_EXCEPTIONS as exc:
            raise ProviderUnavailableError(f"Anthropic request failed: {exc}") from exc

        return _extract_text(response.content)

    async def stream_message(self, *, prompt: str, system: str | None = None) -> AsyncIterator[str]:
        """Streaming Messages API call — yields text deltas as they arrive.
        Same error-handling contract as `create_message`."""

        try:
            async with self._client.messages.stream(**self._build_kwargs(prompt=prompt, system=system)) as stream:
                async for text in stream.text_stream:
                    yield text
        except _UNAVAILABLE_EXCEPTIONS as exc:
            raise ProviderUnavailableError(f"Anthropic streaming request failed: {exc}") from exc

    def _build_kwargs(self, *, prompt: str, system: str | None) -> dict:
        kwargs: dict = {
            "model": self._model,
            "max_tokens": _MAX_TOKENS,
            "messages": [{"role": "user", "content": prompt}],
        }
        # Omit `system` entirely rather than passing `system=None` — the
        # SDK distinguishes "not provided" from an explicit value at the
        # type level (`Omit` sentinel), so passing None is the wrong shape.
        if system:
            kwargs["system"] = system
        return kwargs


def _extract_text(content_blocks: list) -> str:
    """Join every text content block in an Anthropic `Message.content`
    list — a response can in principle contain multiple blocks; for a
    plain text completion (no tool use) this is normally exactly one."""

    return "".join(block.text for block in content_blocks if block.type == "text")
