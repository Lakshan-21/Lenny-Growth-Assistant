"""The routing engine: auto-classification, manual override handling, and
skill chaining (CONTEXT.md's "Router" — Auto / QA / Research / Ship30 modes).

Distinct from `router.py` (the FastAPI HTTP layer), which calls into this
module. Per REPOSITORY_STRUCTURE.md's MVP simplification, routing decisions
are recorded to application logs only — there is no `RoutingDecision`
database table/model in this codebase.
"""

import logging
import uuid

from app.domains.skills.base import Skill
from app.domains.skills.exceptions import UnroutableMessageError
from app.domains.skills.schemas import RoutingMode, SkillContext, SkillResult, SkillType

logger = logging.getLogger(__name__)


class SkillRouter:
    """Dispatches a `SkillContext` to the appropriate `Skill` implementation.

    Constructor-injected with the full skill registry (one instance per
    skill type) — see `skills/dependencies.py` for how this is wired from
    FastAPI `Depends`.
    """

    def __init__(self, skills: dict[SkillType, Skill]) -> None:
        self._skills = skills

    async def route(
        self,
        *,
        context: SkillContext,
        mode: RoutingMode,
        manual_skill: SkillType | None,
    ) -> SkillResult:
        """Resolve which skill should handle `context`, invoke it, and return
        its result. Logs the routing decision (skill, mode, confidence)
        per-message — see `_log_routing_decision`.

        TODO (skill chaining, CONTEXT.md "Router > Features"): a skill's
        result may indicate that another skill should run next (e.g. QA
        answer -> offer to escalate to Research). Chaining orchestration is
        intentionally not implemented in this skeleton.
        """

        selected_skill_type, confidence = self._resolve_skill_type(
            context=context, mode=mode, manual_skill=manual_skill
        )
        self._log_routing_decision(
            session_id=context.session_id,
            selected_skill=selected_skill_type,
            mode=mode,
            confidence=confidence,
        )

        skill = self._skills[selected_skill_type]
        return await skill.handle(context)

    def _resolve_skill_type(
        self,
        *,
        context: SkillContext,
        mode: RoutingMode,
        manual_skill: SkillType | None,
    ) -> tuple[SkillType, float | None]:
        """Return `(skill_type, confidence)`. Confidence is `None` for
        manual overrides (there is nothing to be confident about — the
        user chose explicitly)."""

        if mode == "manual":
            if manual_skill is None:
                raise UnroutableMessageError("mode='manual' requires a 'skill' value")
            return manual_skill, None

        return self._classify(context)

    def _classify(self, context: SkillContext) -> tuple[SkillType, float]:
        """Auto-classification heuristic (CONTEXT.md "Router > Auto Routing").

        TODO: implement intent classification over `context.message` (and
        optionally `context.history`) to select one of qa/research/ship30/
        artifact. Raise `UnroutableMessageError` if no skill can be
        confidently selected (PRD §6.7 acceptance criteria).
        """

        raise NotImplementedError

    @staticmethod
    def _log_routing_decision(
        *,
        session_id: uuid.UUID,
        selected_skill: SkillType,
        mode: RoutingMode,
        confidence: float | None,
    ) -> None:
        """Structured application-log entry — the MVP substitute for a
        `RoutingDecision` DB table (REPOSITORY_STRUCTURE.md, DATABASE_SCHEMA.md
        §8 risk #6)."""

        logger.info(
            "routing_decision",
            extra={
                "session_id": str(session_id),
                "selected_skill": selected_skill,
                "routing_mode": mode,
                "confidence": confidence,
            },
        )
