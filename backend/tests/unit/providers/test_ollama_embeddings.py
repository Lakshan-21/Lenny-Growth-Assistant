"""Unit tests for the embedding-placement toggle (Ollama configuration
review): `OLLAMA_EMBEDDING_FORCE_CPU` should add/omit `options.num_gpu=0`
on the request `OllamaEmbeddingsClient` sends, without touching anything
else about the request or response handling. No live Ollama server
needed -- a fake client captures the JSON payload instead.
"""

import asyncio

from app.domains.providers.ollama.embeddings import OllamaEmbeddingsClient


class _CapturingOllamaClient:
    def __init__(self, embeddings: list[list[float]]) -> None:
        self.captured_path = None
        self.captured_json = None
        self._embeddings = embeddings

    async def post(self, path: str, json: dict) -> dict:
        self.captured_path = path
        self.captured_json = json
        return {"model": "bge-m3", "embeddings": self._embeddings}


class _FakeSettings:
    OLLAMA_EMBEDDING_MODEL = "bge-m3"

    def __init__(self, force_cpu: bool) -> None:
        self.OLLAMA_EMBEDDING_FORCE_CPU = force_cpu


def test_force_cpu_true_sets_num_gpu_zero():
    fake_client = _CapturingOllamaClient(embeddings=[[0.0] * 1024])
    client = OllamaEmbeddingsClient(settings=_FakeSettings(force_cpu=True), client=fake_client)

    asyncio.run(client.embed_batch(texts=["hello"]))

    assert fake_client.captured_path == "/api/embed"
    assert fake_client.captured_json["options"] == {"num_gpu": 0}


def test_force_cpu_false_omits_options_entirely():
    """Must be genuinely absent from the request body, not sent as
    `"options": null` -- some servers treat an explicit null differently
    from a missing key."""

    fake_client = _CapturingOllamaClient(embeddings=[[0.0] * 1024])
    client = OllamaEmbeddingsClient(settings=_FakeSettings(force_cpu=False), client=fake_client)

    asyncio.run(client.embed_batch(texts=["hello"]))

    assert "options" not in fake_client.captured_json


def test_generation_request_shape_is_unaffected():
    """This toggle must only ever touch the embedding request -- confirms
    `_EmbedRequest`'s new `options` field doesn't leak into anything the
    generation path (`ollama/generation.py`) builds, which has no
    `options`/`num_gpu` concept at all."""

    from app.domains.providers.ollama.generation import _ChatRequest

    assert "options" not in _ChatRequest.model_fields
