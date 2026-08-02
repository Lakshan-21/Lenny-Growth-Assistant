"""Implements the Artifact `Skill`: direct artifact-producing operations
invoked via the router (distinct from `artifacts/service.py`'s
persistence/CRUD, which this skill calls into)."""

from typing import ClassVar

from app.domains.artifacts.service import ArtifactService
from app.domains.skills.schemas import SkillContext, SkillResult


class ArtifactSkill:
    name: ClassVar[str] = "artifact"

    def __init__(self, artifact_service: ArtifactService) -> None:
        self._artifact_service = artifact_service

    async def handle(self, context: SkillContext) -> SkillResult:
        """TODO: interpret `context.message` as an explicit artifact
        operation (e.g. "turn this into a document") against prior session
        content, and return a `SkillResult` carrying the resulting
        Markdown for the router to persist via `artifacts/service.py`."""

        raise NotImplementedError
