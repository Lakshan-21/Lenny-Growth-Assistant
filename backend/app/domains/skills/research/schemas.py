"""Research-skill-specific shapes."""

from pydantic import BaseModel


class ResearchBriefSection(BaseModel):
    """One section of a synthesized research brief (DOMAIN_MODEL.md §4.9)."""

    heading: str
    body_markdown: str


class ResearchBriefDraft(BaseModel):
    """Intermediate synthesis output before it's wrapped into a `SkillResult`
    / persisted as an `Artifact` + `ResearchBrief` row."""

    topic: str
    summary: str
    sections: list[ResearchBriefSection]
