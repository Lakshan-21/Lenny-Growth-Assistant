"""Sessions domain schemas (Pydantic v2).

`MessageRole`/`SkillType` are local `Literal` aliases mirroring the DB CHECK
constraints in `models.py` exactly. Kept local (not imported from
`skills/schemas.py`) to avoid coupling between vertical slices — see
IMPLEMENTATION ASSUMPTIONS in the generation summary.
"""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

MessageRole = Literal["user", "assistant", "system"]
SkillType = Literal["qa", "research", "ship30", "artifact"]


class SessionCreate(BaseModel):
    """Body for POST /sessions. Title is optional — derived from the first
    message if omitted (see service.py)."""

    title: str | None = None


class SessionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    title: str
    created_at: datetime
    updated_at: datetime


class SessionListItem(BaseModel):
    """Slimmer projection of `SessionRead` for the session sidebar."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    title: str
    updated_at: datetime


class MessageCreate(BaseModel):
    """Body for posting a new user message into a session.

    Routing (auto vs. manual override) is handled by the skills domain —
    see `skills/schemas.py::SkillInvocationRequest`, which wraps this.
    """

    content: str = Field(min_length=1)


class CitationRead(BaseModel):
    """A citation as embedded in message history (`MessageRead.citations`).
    Deliberately smaller than `skills.schemas.CitationRef`: no
    `transcript_chunk_id` here, since this shape only ever appears nested
    inside a message a client already has an id for — it's a display
    payload, not something looked up independently.
    """

    model_config = ConfigDict(from_attributes=True)

    display_label: str
    excerpt: str


class MessageRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    session_id: UUID
    role: MessageRole
    content: str
    skill_used: SkillType | None = None
    created_at: datetime
    citations: list[CitationRead] = Field(default_factory=list)
    """Populated for both the live `POST /messages` response and
    historical messages returned by `GET /sessions/{id}` (see
    `sessions/repository.py`'s nested `selectinload` chain) — the same
    `Citation` rows, viewed two ways depending on the caller."""


class SessionDetailRead(SessionRead):
    """Full session view: metadata + ordered message history (PRD §6.2,
    "Continue previous sessions")."""

    messages: list[MessageRead] = Field(default_factory=list)
