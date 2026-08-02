"""Low-level HTTP client for the local Ollama server.

Thin transport wrapper — `generation.py` and `embeddings.py` both compose
this rather than talking to Ollama's HTTP API directly, so retry/timeout
policy lives in exactly one place.
"""

import asyncio
import json as json_lib
import logging
from collections.abc import AsyncIterator

import httpx

from app.config import Settings
from app.domains.providers.exceptions import ProviderResponseError, ProviderUnavailableError

logger = logging.getLogger(__name__)

# 429/5xx and a couple of transient edge codes are worth a retry; anything
# else (400 bad request, 404 model not found, 401/403, ...) is a
# request-shape or config problem that retrying won't fix.
_RETRYABLE_STATUS_CODES = frozenset({408, 425, 429, 500, 502, 503, 504})
_MAX_ATTEMPTS = 3
_BACKOFF_BASE_SECONDS = 0.5


class OllamaClient:
    """Thin async HTTP transport over the local Ollama REST API.

    Owns exactly three concerns so `generation.py`/`embeddings.py` don't
    have to: pooled connection reuse, timeout enforcement, and bounded
    retry with exponential backoff on transient failures. Every failure
    mode surfaces as a `ProviderUnavailableError` (or its
    `ProviderResponseError` subclass), which `providers.gateway.ModelGateway`
    catches to trigger Claude fallback.
    """

    def __init__(self, settings: Settings) -> None:
        self._base_url = settings.OLLAMA_BASE_URL
        self._timeout_seconds = settings.OLLAMA_REQUEST_TIMEOUT_SECONDS
        self._client = httpx.AsyncClient(base_url=self._base_url, timeout=self._timeout_seconds)

    async def aclose(self) -> None:
        """Release the pooled connection. Wire into app shutdown when one exists."""

        await self._client.aclose()

    async def post(self, path: str, json: dict) -> dict:
        """`POST {base_url}{path}` with `json`; return the parsed JSON body.

        Retries up to `_MAX_ATTEMPTS` times with exponential backoff on
        connection errors, timeouts, and the retryable status codes above.
        Non-retryable status codes fail immediately (no point retrying a
        malformed request or a missing model). Raises
        `ProviderUnavailableError` if every attempt is exhausted, or
        `ProviderResponseError` if the server responds 2xx with a body that
        isn't valid JSON.
        """

        last_error: Exception | None = None

        for attempt in range(1, _MAX_ATTEMPTS + 1):
            try:
                response = await self._client.post(path, json=json)
            except httpx.TimeoutException as exc:
                last_error = exc
                logger.warning(
                    "Ollama request timed out (attempt %d/%d): POST %s", attempt, _MAX_ATTEMPTS, path
                )
            except httpx.TransportError as exc:
                # Covers connection-refused, DNS failure, etc. -- Ollama
                # simply isn't reachable right now.
                last_error = exc
                logger.warning(
                    "Ollama request failed to connect (attempt %d/%d): POST %s (%s)",
                    attempt, _MAX_ATTEMPTS, path, exc,
                )
            else:
                if response.status_code in _RETRYABLE_STATUS_CODES:
                    last_error = httpx.HTTPStatusError(
                        f"retryable status {response.status_code}",
                        request=response.request,
                        response=response,
                    )
                    logger.warning(
                        "Ollama returned retryable status %d (attempt %d/%d): POST %s",
                        response.status_code, attempt, _MAX_ATTEMPTS, path,
                    )
                elif response.status_code >= 400:
                    raise ProviderUnavailableError(
                        f"Ollama request to {path} failed with status {response.status_code}: "
                        f"{response.text[:500]}"
                    )
                else:
                    try:
                        return response.json()
                    except json_lib.JSONDecodeError as exc:
                        raise ProviderResponseError(
                            f"Ollama response from {path} was not valid JSON: {exc}"
                        ) from exc

            if attempt < _MAX_ATTEMPTS:
                await asyncio.sleep(_BACKOFF_BASE_SECONDS * (2 ** (attempt - 1)))

        raise ProviderUnavailableError(
            f"Ollama request to {path} failed after {_MAX_ATTEMPTS} attempts"
        ) from last_error

    async def stream_post(self, path: str, json: dict) -> AsyncIterator[dict]:
        """`POST {base_url}{path}` with streaming enabled; yield each
        newline-delimited JSON object as it arrives (Ollama's streaming
        protocol is one JSON object per line, not SSE).

        No retry once the stream has started: a failure mid-stream can't be
        safely replayed at this layer without risking duplicated output —
        see `providers.gateway.ModelGateway.stream`'s TODO on streaming
        failover, which owns that decision at a higher level. A failure
        before the first byte (connect/timeout) still surfaces as a plain
        `ProviderUnavailableError`, same as `post`.
        """

        try:
            async with self._client.stream("POST", path, json=json) as response:
                if response.status_code >= 400:
                    body = await response.aread()
                    raise ProviderUnavailableError(
                        f"Ollama streaming request to {path} failed with status "
                        f"{response.status_code}: {body.decode(errors='replace')[:500]}"
                    )
                async for line in response.aiter_lines():
                    if not line.strip():
                        continue
                    try:
                        yield json_lib.loads(line)
                    except json_lib.JSONDecodeError as exc:
                        raise ProviderResponseError(
                            f"Ollama stream line from {path} was not valid JSON: {exc}"
                        ) from exc
        except httpx.TimeoutException as exc:
            raise ProviderUnavailableError(f"Ollama streaming request to {path} timed out") from exc
        except httpx.TransportError as exc:
            raise ProviderUnavailableError(
                f"Ollama streaming request to {path} failed to connect: {exc}"
            ) from exc
