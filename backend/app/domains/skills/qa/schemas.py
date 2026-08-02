"""QA-skill-specific shapes.

Most of the QA skill's I/O is already covered by the shared
`skills.schemas.SkillContext`/`SkillResult`. This module is a placeholder
for QA-specific refinements (e.g. retrieval filters, top-k overrides) that
aren't yet part of the shared contract — kept separate so adding them
doesn't widen `SkillContext` for every other skill.
"""

from pydantic import BaseModel


class QARetrievalOptions(BaseModel):
    """Optional retrieval tuning for a QA request.

    TODO: wire into `QASkill.handle` once the router passes structured
    options through (currently `SkillContext` carries only raw message text).
    """

    top_k: int = 8
    episode_ids: list[str] | None = None
