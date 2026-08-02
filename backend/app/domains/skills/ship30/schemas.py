"""Ship30-skill-specific shapes.

`content_type`/`source_artifact_id` request fields live on the shared
`skills.schemas.SkillInvocationRequest`/`SkillContext` (not a Ship30-only
request type) — see `skills/router.py`. Keeping only the genuinely
Ship30-specific shapes here.
"""

from typing import Literal

from pydantic import BaseModel

Ship30ContentType = Literal["linkedin_post", "x_thread", "article"]


class XThreadSegment(BaseModel):
    index: int
    text: str
