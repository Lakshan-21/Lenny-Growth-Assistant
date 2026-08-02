"""Artifact lifecycle logic; enforces Markdown as the canonical source of
truth (ADR-4, ARCHITECTURE.md). Invoked by skill modules (to create
artifacts) and by `sessions/router.py` (to read/download them).
"""

import uuid

from app.domains.artifacts.exceptions import ArtifactNotFoundError
from app.domains.artifacts.models import Artifact, ResearchBrief
from app.domains.artifacts.renderers.html_renderer import render_html
from app.domains.artifacts.renderers.markdown_renderer import render_markdown
from app.domains.artifacts.repository import ArtifactRepository


class ArtifactService:
    def __init__(self, repository: ArtifactRepository) -> None:
        self._repository = repository

    async def create(
        self,
        *,
        session_id: uuid.UUID,
        message_id: uuid.UUID,
        artifact_type: str,
        content_markdown: str,
    ) -> Artifact:
        """Persist a new artifact produced by a skill."""

        return await self._repository.create(
            session_id=session_id,
            message_id=message_id,
            artifact_type=artifact_type,
            content_markdown=content_markdown,
        )

    async def create_research_brief(
        self, *, artifact: Artifact, topic: str, summary: str
    ) -> ResearchBrief:
        """Persist the `ResearchBrief` specialization row for a
        `research_brief`-typed artifact (DOMAIN_MODEL.md §4.9).

        `artifact` must already be persisted with `artifact_type ==
        "research_brief"` — the DB trigger enforces this, not this method.
        """

        return await self._repository.create_research_brief(
            artifact_id=artifact.id, topic=topic, summary=summary
        )

    async def list_for_session(self, *, session_id: uuid.UUID) -> list[Artifact]:
        return await self._repository.list_for_session(session_id=session_id)

    async def get_for_session(self, *, session_id: uuid.UUID, artifact_id: uuid.UUID) -> Artifact:
        """Fetch an artifact and enforce it belongs to `session_id`.

        Raises `ArtifactNotFoundError` both when the artifact doesn't
        exist AND when it exists but belongs to a different session —
        deliberately not distinguished, matching the same IDOR-avoidance
        rationale as `sessions.service.SessionService.get_owned_session`.
        """

        artifact = await self._repository.get_by_id(artifact_id)
        if artifact is None or artifact.session_id != session_id:
            raise ArtifactNotFoundError(f"No artifact found with id {artifact_id} in session {session_id}")
        return artifact

    async def get_markdown_for_download(self, *, session_id: uuid.UUID, artifact_id: uuid.UUID) -> str:
        """Return the exact Markdown to serve for a download request
        (PRD §6.6 acceptance criteria: "Copy and download always reflect
        the currently rendered artifact content exactly").
        """

        artifact = await self.get_for_session(session_id=session_id, artifact_id=artifact_id)
        return render_markdown(content_markdown=artifact.content_markdown)

    async def get_html_for_session(self, *, session_id: uuid.UUID, artifact_id: uuid.UUID) -> str:
        """Return the sanitized HTML rendering for the HTML display mode (PRD §6.6)."""

        artifact = await self.get_for_session(session_id=session_id, artifact_id=artifact_id)
        return render_html(content_markdown=artifact.content_markdown)
