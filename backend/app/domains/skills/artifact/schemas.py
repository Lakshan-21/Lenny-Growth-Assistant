"""Artifact-skill-specific shapes."""

from pydantic import BaseModel


class ArtifactSkillRequest(BaseModel):
    """Explicit "turn this into a document"-style request.

    TODO: wire into `ArtifactSkill.handle` once the router/frontend pass
    this through structurally (currently inferred from raw message text).
    """

    source_message_id: str | None = None
