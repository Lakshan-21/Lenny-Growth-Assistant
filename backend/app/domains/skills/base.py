"""The `Skill` protocol every skill module implements.

Structural typing (`Protocol`) rather than an ABC — skill implementations
(`QASkill`, `ResearchSkill`, `Ship30Skill`, `ArtifactSkill`, per
REPOSITORY_STRUCTURE.md §4 naming conventions) don't need to inherit from
this class, only satisfy its shape, so each skill module stays fully
decoupled from the others.
"""

from typing import Protocol, runtime_checkable

from app.domains.skills.schemas import SkillContext, SkillResult, SkillType


@runtime_checkable
class Skill(Protocol):
    """Structural interface for a single skill (QA, Research, Ship30, Artifact)."""

    name: SkillType

    async def handle(self, context: SkillContext) -> SkillResult:
        """Execute this skill against the given context and return its result.

        Implementations are expected to be pure orchestration: retrieve
        context (if needed), call the model gateway, assemble citations,
        and return a `SkillResult` — persistence (messages/artifacts) is
        the router/session-service's responsibility, not the skill's.
        """
        ...
