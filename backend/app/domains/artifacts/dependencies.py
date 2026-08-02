"""FastAPI dependency wiring for the artifacts domain.

NOTE — structural addition, flagged per task instructions: REPOSITORY_STRUCTURE.md's
`artifacts/` file listing predates this task's explicit "Dependency
Injection" requirement and does not list a `dependencies.py`. Added here
because `ArtifactService` is consumed by two different routers
(`sessions/router.py` and `skills/router.py`) and needs a single shared
wiring point rather than duplicated provider functions. See generation
summary.
"""

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_db
from app.domains.artifacts.repository import ArtifactRepository
from app.domains.artifacts.service import ArtifactService


def get_artifact_repository(db: AsyncSession = Depends(get_db)) -> ArtifactRepository:
    return ArtifactRepository(db)


def get_artifact_service(
    repository: ArtifactRepository = Depends(get_artifact_repository),
) -> ArtifactService:
    return ArtifactService(repository)
