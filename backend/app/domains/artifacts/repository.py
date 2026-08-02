"""Data-access layer for `Artifact`/`ResearchBrief` rows.

Transaction ownership matches every other repository in this codebase
(sessions, knowledge): only `add()`/`flush()` here, never
`commit()`/`rollback()` — that's `app.database.session.get_db`'s job for
request-scoped calls.
"""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.artifacts.models import Artifact, ResearchBrief


class ArtifactRepository:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def create(
        self,
        *,
        session_id: uuid.UUID,
        message_id: uuid.UUID,
        artifact_type: str,
        content_markdown: str,
    ) -> Artifact:
        """Insert a new `Artifact` row. Flushed immediately so the
        generated `id`/`created_at` are populated on the returned object
        (needed by callers that persist a `ResearchBrief` against it in
        the same request)."""

        artifact = Artifact(
            session_id=session_id,
            message_id=message_id,
            artifact_type=artifact_type,
            content_markdown=content_markdown,
        )
        self._db.add(artifact)
        await self._db.flush()
        return artifact

    async def get_by_id(self, artifact_id: uuid.UUID) -> Artifact | None:
        return await self._db.get(Artifact, artifact_id)

    async def list_for_session(self, *, session_id: uuid.UUID) -> list[Artifact]:
        """`SELECT ... WHERE session_id = :session_id ORDER BY created_at`
        (matches `idx_artifacts_session_created`, DATABASE_SCHEMA.md §4)."""

        stmt = select(Artifact).where(Artifact.session_id == session_id).order_by(Artifact.created_at)
        result = await self._db.execute(stmt)
        return list(result.scalars().all())

    async def create_research_brief(
        self, *, artifact_id: uuid.UUID, topic: str, summary: str
    ) -> ResearchBrief:
        """Insert a new `ResearchBrief` row.

        Note: the DB-level `research_briefs_check_artifact_type` trigger
        (DATABASE_SCHEMA.md §2) rejects this if the referenced artifact's
        `artifact_type` isn't `'research_brief'` — not duplicated here.
        """

        brief = ResearchBrief(artifact_id=artifact_id, topic=topic, summary=summary)
        self._db.add(brief)
        await self._db.flush()
        return brief
