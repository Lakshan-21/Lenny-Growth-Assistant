"""Text-generation calls against Ollama (primary path), via the
`POST /api/chat` chat-completion endpoint.
"""

from collections.abc import AsyncIterator
from dataclasses import dataclass

from pydantic import BaseModel, ValidationError

from app.config import Settings
from app.domains.providers.exceptions import ProviderResponseError
from app.domains.providers.ollama.client import OllamaClient


@dataclass(frozen=True, slots=True)
class ChatTurn:
    """A single turn in a multi-turn conversation, for `OllamaProvider.chat`.

    `role` should be one of "system" | "user" | "assistant" — conveniently
    the same three values as `sessions.models.MESSAGE_ROLES`, so callers
    (e.g. `skills/router.py`) can map persisted `Message` rows onto this
    type with a plain field-for-field conversion, no translation needed.
    """

    role: str
    content: str


class _ChatMessage(BaseModel):
    role: str
    content: str


class _ChatRequest(BaseModel):
    """Request body for Ollama's `POST /api/chat`."""

    model: str
    messages: list[_ChatMessage]
    stream: bool = False


class _ChatResponse(BaseModel):
    """Non-streaming (`stream: false`) response body from `POST /api/chat`."""

    model: str
    message: _ChatMessage
    done: bool = True


class _ChatStreamChunk(BaseModel):
    """One newline-delimited JSON object from a streaming (`stream: true`)
    `POST /api/chat` response. `message` is absent/empty on the final
    chunk in some Ollama versions, hence optional."""

    model: str
    message: _ChatMessage | None = None
    done: bool = False


def _single_turn(*, prompt: str, system: str | None) -> list[ChatTurn]:
    turns: list[ChatTurn] = []
    if system:
        turns.append(ChatTurn(role="system", content=system))
    turns.append(ChatTurn(role="user", content=prompt))
    return turns


def _to_wire_messages(turns: list[ChatTurn]) -> list[_ChatMessage]:
    return [_ChatMessage(role=turn.role, content=turn.content) for turn in turns]


class OllamaProvider:
    """Satisfies the `providers.base.ModelProvider` protocol structurally."""

    def __init__(self, client: OllamaClient, settings: Settings) -> None:
        self._client = client
        self._model = settings.OLLAMA_GENERATION_MODEL

    async def generate(self, *, prompt: str, system: str | None = None) -> str:
        """Single-turn, non-streaming chat completion — satisfies the shared
        `ModelProvider` protocol. For a real multi-turn conversation, use
        `chat()` instead; this is a thin convenience wrapper around it."""

        return await self.chat(messages=_single_turn(prompt=prompt, system=system))

    async def chat(self, *, messages: list[ChatTurn]) -> str:
        """Multi-turn, non-streaming chat completion — sends the full
        conversation history to Ollama's `/api/chat` in one call, giving the
        model real multi-turn context rather than only the latest message.
        Used by the conversational endpoint (`skills/router.py`).
        """

        request = _ChatRequest(model=self._model, messages=_to_wire_messages(messages), stream=False)
        raw = await self._client.post("/api/chat", request.model_dump())
        try:
            response = _ChatResponse.model_validate(raw)
        except ValidationError as exc:
            raise ProviderResponseError(
                f"Ollama /api/chat response did not match the expected shape: {exc}"
            ) from exc
        return response.message.content

    async def stream(self, *, prompt: str, system: str | None = None) -> AsyncIterator[str]:
        """Streaming chat completion — yields text deltas as they arrive.

        Single-turn only (matches `generate()`); multi-turn streaming isn't
        required by any current caller and isn't implemented here.
        """

        request = _ChatRequest(
            model=self._model,
            messages=_to_wire_messages(_single_turn(prompt=prompt, system=system)),
            stream=True,
        )
        async for raw_chunk in self._client.stream_post("/api/chat", request.model_dump()):
            try:
                chunk = _ChatStreamChunk.model_validate(raw_chunk)
            except ValidationError as exc:
                raise ProviderResponseError(
                    f"Ollama /api/chat stream chunk did not match the expected shape: {exc}"
                ) from exc
            if chunk.message and chunk.message.content:
                yield chunk.message.content
            if chunk.done:
                break

    async def embed(self, *, text: str) -> list[float]:
        """Not used via this class — see `ollama/embeddings.py::OllamaEmbeddingsClient`,
        called directly by `knowledge/embeddings/embedding_service.py`
        (bypassing `ModelGateway`, per `providers.base.ModelProvider` docstring)."""

        raise NotImplementedError(
            "OllamaProvider.embed is intentionally unused — use OllamaEmbeddingsClient "
            "(ollama/embeddings.py) directly instead."
        )
