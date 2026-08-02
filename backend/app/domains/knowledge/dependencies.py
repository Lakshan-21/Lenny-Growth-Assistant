"""FastAPI dependency wiring for the knowledge domain.

NOTE — structural addition, flagged per task instructions: REPOSITORY_STRUCTURE.md's
`knowledge/` file listing predates this task's explicit "Dependency
Injection" requirement and does not list a `dependencies.py`. Added here so
`skills/dependencies.py` (consumer: both `qa` and `research` skill wiring)
has a single shared provider rather than duplicated construction. See
generation summary.
"""

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_db
from app.domains.knowledge.embeddings.embedding_service import EmbeddingService
from app.domains.knowledge.repository import KnowledgeRepository
from app.domains.knowledge.retrieval_service import RetrievalService
from app.domains.providers.dependencies import get_ollama_embeddings_client
from app.domains.providers.ollama.embeddings import OllamaEmbeddingsClient


def get_knowledge_repository(db: AsyncSession = Depends(get_db)) -> KnowledgeRepository:
    return KnowledgeRepository(db)


def get_embedding_service(
    ollama_embeddings: OllamaEmbeddingsClient = Depends(get_ollama_embeddings_client),
) -> EmbeddingService:
    return EmbeddingService(ollama_embeddings=ollama_embeddings)


def get_retrieval_service(
    repository: KnowledgeRepository = Depends(get_knowledge_repository),
    embedding_service: EmbeddingService = Depends(get_embedding_service),
) -> RetrievalService:
    return RetrievalService(repository=repository, embedding_service=embedding_service)
