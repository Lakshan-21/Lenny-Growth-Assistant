"""Artifacts domain schemas (Pydantic v2)."""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict

ArtifactType = Literal["qa_answer", "research_brief", "linkedin_post", "x_thread", "article"]


class ArtifactCreate(BaseModel):
    """Internal creation payload — used by `skills/skill_router.py` when
    persisting a `SkillResult` that carries an `artifact_type`, not exposed
    directly over HTTP (artifacts have no router of their own in MVP)."""

    session_id: UUID
    message_id: UUID
    artifact_type: ArtifactType
    content_markdown: str


class ArtifactRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    session_id: UUID
    message_id: UUID
    artifact_type: ArtifactType
    content_markdown: str
    created_at: datetime


class ArtifactHtmlRead(BaseModel):
    """Rendered view for the HTML display mode (PRD §6.6). Derived, not stored."""

    id: UUID
    content_html: str


class ResearchBriefCreate(BaseModel):
    artifact_id: UUID
    topic: str
    summary: str


class ResearchBriefRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    artifact_id: UUID
    topic: str
    summary: str
    created_at: datetime
