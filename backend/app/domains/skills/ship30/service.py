"""Implements the Ship30 `Skill`: dispatches to the correct formatter based
on requested content type (PRD §6.5)."""

from typing import ClassVar

from app.domains.artifacts.service import ArtifactService
from app.domains.providers.gateway import ModelGateway
from app.domains.skills.exceptions import SkillExecutionError
from app.domains.skills.schemas import SkillContext, SkillResult
from app.domains.skills.ship30.formatters.article import format_article
from app.domains.skills.ship30.formatters.linkedin import format_linkedin_post
from app.domains.skills.ship30.formatters.x_thread import format_x_thread, render_x_thread_markdown
from app.domains.skills.ship30.prompts import SHIP30_SYSTEM_PROMPT, build_ship30_prompt
from app.domains.skills.ship30.schemas import Ship30ContentType

_VALID_CONTENT_TYPES: tuple[Ship30ContentType, ...] = ("linkedin_post", "x_thread", "article")


class Ship30Skill:
    """Satisfies the `skills.base.Skill` protocol structurally (no inheritance
    required — see base.py docstring)."""

    name: ClassVar[str] = "ship30"

    def __init__(self, model_gateway: ModelGateway, artifact_service: ArtifactService) -> None:
        self._model_gateway = model_gateway
        self._artifact_service = artifact_service

    async def handle(self, context: SkillContext) -> SkillResult:
        content_type = self._resolve_content_type(context)
        source_markdown = await self._resolve_source_markdown(context)

        prompt = build_ship30_prompt(
            content_type=content_type, instruction=context.message, source_markdown=source_markdown
        )
        raw_completion = await self._model_gateway.generate(prompt=prompt, system=SHIP30_SYSTEM_PROMPT)

        content_markdown = self._format(content_type=content_type, raw_completion=raw_completion)

        # artifact_type mirrors content_type exactly (both are one of
        # DATABASE_SCHEMA.md's artifacts.artifact_type CHECK values) —
        # the router persists this as an Artifact whenever it's set.
        return SkillResult(skill="ship30", content_markdown=content_markdown, artifact_type=content_type)

    def _resolve_content_type(self, context: SkillContext) -> Ship30ContentType:
        """Router-level validation (`skills/router.py`) already rejects a
        missing/invalid `content_type` before this skill is ever invoked —
        this is a defense-in-depth check for direct/programmatic callers of
        `handle()` that bypass the router.
        """

        if context.content_type not in _VALID_CONTENT_TYPES:
            raise SkillExecutionError(
                f"Ship30 requires a valid content_type (one of {_VALID_CONTENT_TYPES}), "
                f"got {context.content_type!r}"
            )
        return context.content_type  # type: ignore[return-value]

    @staticmethod
    def _format(*, content_type: Ship30ContentType, raw_completion: str) -> str:
        if content_type == "linkedin_post":
            return format_linkedin_post(raw_completion=raw_completion)
        if content_type == "x_thread":
            return render_x_thread_markdown(format_x_thread(raw_completion=raw_completion))
        return format_article(raw_completion=raw_completion)

    async def _resolve_source_markdown(self, context: SkillContext) -> str:
        """Resolve the content Ship30 should transform.

        Priority: (1) an explicit `source_artifact_id`, if given; (2) the
        most recent assistant message in the session (typically a prior QA
        answer); (3) the user's own instruction, if there's no session
        history yet to derive from (first message in a session).
        """

        if context.source_artifact_id is not None:
            artifact = await self._artifact_service.get_for_session(
                session_id=context.session_id, artifact_id=context.source_artifact_id
            )
            return artifact.content_markdown

        for turn in reversed(context.history):
            if turn.role == "assistant":
                return turn.content

        return context.message
