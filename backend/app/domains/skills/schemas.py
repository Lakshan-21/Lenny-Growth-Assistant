"""Shared skill I/O contracts (Pydantic v2 / dataclasses).

`SkillContext` is the input every `Skill` implementation receives;
`SkillResult` is the common output shape the router persists back onto the
session (as an assistant message, and optionally an artifact).
"""

import uuid
from dataclasses import dataclass, field
from typing import Literal

from pydantic import BaseModel, Field

from app.domains.sessions.schemas import MessageRead

SkillType = Literal["qa", "research", "ship30", "artifact"]
RoutingMode = Literal["auto", "manual"]


@dataclass(frozen=True, slots=True)
class ConversationTurn:
    """A prior message in the session, for prompt construction context."""

    role: str
    content: str


@dataclass(frozen=True, slots=True)
class SkillContext:
    """Everything a `Skill.handle()` implementation needs to do its work.

    Constructed by `skill_router.py` from the persisted session/message
    state (via `sessions.service.SessionService`) before dispatch.
    """

    session_id: uuid.UUID
    user_id: uuid.UUID
    message: str
    history: list[ConversationTurn] = field(default_factory=list)
    # Ship30-only fields (ignored by qa/research/artifact) — see
    # skills/ship30/service.py. Kept on the shared context rather than a
    # per-skill request type so every `Skill.handle(context)` keeps the
    # same polymorphic signature (skills/base.py).
    content_type: str | None = None
    source_artifact_id: uuid.UUID | None = None


class CitationRef(BaseModel):
    """A citation attached to a `SkillResult` (DOMAIN_MODEL.md §4.8)."""

    transcript_chunk_id: uuid.UUID
    display_label: str
    excerpt: str
    """The actual transcript excerpt text this citation grounds its claim
    in (CONTEXT.md "Citations": episode name, timestamp, and transcript
    excerpt) — lets a client render the source passage directly, without a
    second lookup by `transcript_chunk_id`."""


@dataclass(frozen=True, slots=True)
class SkillResult:
    """Common output shape returned by every `Skill.handle()` implementation."""

    skill: SkillType
    content_markdown: str
    citations: list[CitationRef] = field(default_factory=list)
    # When set, the router persists this as an Artifact (artifacts/service.py)
    # attached to the producing message. artifact_type must match one of
    # DATABASE_SCHEMA.md's artifacts.artifact_type CHECK values.
    artifact_type: str | None = None
    # Research-only (ignored by qa/ship30/artifact): set together whenever
    # artifact_type == "research_brief", so the router can also persist the
    # ResearchBrief specialization row (DOMAIN_MODEL.md §4.9) alongside the
    # Artifact — see skills/research/service.py and skills/router.py.
    research_topic: str | None = None
    research_summary: str | None = None


class SkillInvocationRequest(BaseModel):
    """Body for `POST /sessions/{session_id}/messages` (skills/router.py)."""

    content: str = Field(min_length=1)
    mode: RoutingMode = "auto"
    skill: SkillType | None = None
    """Required when mode == 'manual'; ignored (should be None) when 'auto'."""
    content_type: Literal["linkedin_post", "x_thread", "article"] | None = None
    """Required when skill == 'ship30' (PRD §6.5); ignored otherwise."""
    source_artifact_id: uuid.UUID | None = None
    """Optional, ship30-only: an explicit source artifact to transform.
    Falls back to the most recent assistant message in the session if
    omitted (see `skills/ship30/service.py`)."""


class SkillInvocationResponse(BaseModel):
    """Response for `POST /sessions/{session_id}/messages`.

    NOTE: this is the non-streaming shape. ARCHITECTURE.md specifies a
    streamed response in production (SSE) — see skills/router.py docstring
    for why streaming wiring is left as a follow-up in this skeleton.
    """

    skill_used: SkillType | None
    """Which skill actually produced `message` — "qa" or "ship30" today
    (Research/Artifact are not yet wired into this endpoint). `None` only
    if a future skill returns no attribution."""
    routing_mode: RoutingMode
    message: MessageRead
    citations: list[CitationRef] = Field(default_factory=list)
    """Same citations as `SkillResult.citations` — the source chunks the
    answer was grounded in (DOMAIN_MODEL.md §4.8). Empty when the QA skill
    found no relevant chunks (see `qa/service.py`'s no-grounding path)."""
    artifact_id: uuid.UUID | None = None
