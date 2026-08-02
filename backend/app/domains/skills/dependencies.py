"""FastAPI dependency wiring for the skills domain: builds each skill
instance and the `SkillRouter` registry.

NOTE — structural addition, flagged per task instructions: REPOSITORY_STRUCTURE.md's
`skills/` file listing predates this task's explicit "Dependency Injection"
requirement and does not list a `dependencies.py`. Added here for
consistency with `auth/dependencies.py` and `sessions/dependencies.py`
(both already in the original tree) rather than scattering `Depends()`
provider functions inside `router.py`. See generation summary.
"""

from fastapi import Depends

from app.domains.artifacts.dependencies import get_artifact_service
from app.domains.artifacts.service import ArtifactService
from app.domains.knowledge.dependencies import get_retrieval_service
from app.domains.knowledge.retrieval_service import RetrievalService
from app.domains.providers.dependencies import get_model_gateway
from app.domains.providers.gateway import ModelGateway
from app.domains.skills.artifact.service import ArtifactSkill
from app.domains.skills.qa.citation_builder import CitationBuilder
from app.domains.skills.qa.service import QASkill
from app.domains.skills.research.service import ResearchSkill
from app.domains.skills.research.synthesis import ResearchSynthesizer
from app.domains.skills.schemas import SkillType
from app.domains.skills.ship30.service import Ship30Skill
from app.domains.skills.skill_router import SkillRouter


def get_qa_skill(
    retrieval_service: RetrievalService = Depends(get_retrieval_service),
    model_gateway: ModelGateway = Depends(get_model_gateway),
) -> QASkill:
    return QASkill(
        retrieval_service=retrieval_service,
        model_gateway=model_gateway,
        citation_builder=CitationBuilder(),
    )


def get_research_skill(
    retrieval_service: RetrievalService = Depends(get_retrieval_service),
    model_gateway: ModelGateway = Depends(get_model_gateway),
) -> ResearchSkill:
    return ResearchSkill(
        retrieval_service=retrieval_service,
        model_gateway=model_gateway,
        synthesizer=ResearchSynthesizer(),
        citation_builder=CitationBuilder(),
    )


def get_ship30_skill(
    model_gateway: ModelGateway = Depends(get_model_gateway),
    artifact_service: ArtifactService = Depends(get_artifact_service),
) -> Ship30Skill:
    return Ship30Skill(model_gateway=model_gateway, artifact_service=artifact_service)


def get_artifact_skill(artifact_service: ArtifactService = Depends(get_artifact_service)) -> ArtifactSkill:
    return ArtifactSkill(artifact_service=artifact_service)


def get_skill_router(
    qa_skill: QASkill = Depends(get_qa_skill),
    research_skill: ResearchSkill = Depends(get_research_skill),
    ship30_skill: Ship30Skill = Depends(get_ship30_skill),
    artifact_skill: ArtifactSkill = Depends(get_artifact_skill),
) -> SkillRouter:
    registry: dict[SkillType, object] = {
        "qa": qa_skill,
        "research": research_skill,
        "ship30": ship30_skill,
        "artifact": artifact_skill,
    }
    return SkillRouter(skills=registry)
