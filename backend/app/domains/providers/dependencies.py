"""FastAPI dependency wiring for the providers domain.

NOTE — structural addition, flagged per task instructions: REPOSITORY_STRUCTURE.md's
`providers/` file listing predates this task's explicit "Dependency
Injection" requirement and does not list a `dependencies.py`. Added here so
`skills/dependencies.py` and `knowledge/dependencies.py` share a single
`ModelGateway`/`OllamaEmbeddingsClient` construction path. See generation
summary.
"""

from fastapi import Depends

from app.config import Settings, get_settings
from app.domains.providers.anthropic.client import AnthropicClient
from app.domains.providers.anthropic.generation import AnthropicProvider
from app.domains.providers.gateway import ModelGateway
from app.domains.providers.ollama.client import OllamaClient
from app.domains.providers.ollama.embeddings import OllamaEmbeddingsClient
from app.domains.providers.ollama.generation import OllamaProvider


def get_ollama_client(settings: Settings = Depends(get_settings)) -> OllamaClient:
    return OllamaClient(settings=settings)


def get_ollama_provider(
    client: OllamaClient = Depends(get_ollama_client),
    settings: Settings = Depends(get_settings),
) -> OllamaProvider:
    return OllamaProvider(client=client, settings=settings)


def get_ollama_embeddings_client(settings: Settings = Depends(get_settings)) -> OllamaEmbeddingsClient:
    return OllamaEmbeddingsClient(settings=settings)


def get_anthropic_client(settings: Settings = Depends(get_settings)) -> AnthropicClient:
    return AnthropicClient(settings=settings)


def get_anthropic_provider(client: AnthropicClient = Depends(get_anthropic_client)) -> AnthropicProvider:
    return AnthropicProvider(client=client)


def get_model_gateway(
    primary: OllamaProvider = Depends(get_ollama_provider),
    secondary: AnthropicProvider = Depends(get_anthropic_provider),
) -> ModelGateway:
    return ModelGateway(primary=primary, secondary=secondary)
