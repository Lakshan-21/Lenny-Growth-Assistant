"""Session lifecycle logic: title derivation, recency ordering, message
history assembly (DOMAIN_MODEL.md §4.2–4.3).

Deliberately has no dependency on the `skills` domain — a message is
persisted here as a plain row; deciding *which skill* handles it and
generating the assistant's reply is the `skills` domain's concern
(see `skills/router.py`, which calls back into this service to persist
both the user's message and the resulting assistant message).
"""

import uuid

from app.domains.sessions.exceptions import SessionNotFoundError
from app.domains.sessions.models import DEFAULT_SESSION_TITLE, Message, Session
from app.domains.sessions.repository import SessionRepository
from app.domains.sessions.schemas import SessionCreate

_TITLE_MAX_LENGTH = 60
_TITLE_TRUNCATION_SUFFIX = "…"


class SessionService:
    def __init__(self, repository: SessionRepository) -> None:
        self._repository = repository

    async def create_session(self, *, user_id: uuid.UUID, data: SessionCreate) -> Session:
        """Create a new session. Uses `data.title` if provided, otherwise
        leaves it unset so the DB default applies — the real title is
        derived from the first message via `derive_title_from_first_message`
        once one is posted (PRD §6.2), in `append_message` below.
        """

        return await self._repository.create(user_id=user_id, title=data.title)

    async def get_owned_session(self, *, session_id: uuid.UUID, user_id: uuid.UUID) -> Session:
        """Fetch a session and enforce ownership.

        Raises `SessionNotFoundError` both when the session doesn't exist
        AND when it exists but belongs to another user — deliberately not
        distinguished, so the response can't be used to enumerate other
        users' session ids (IDOR-style information disclosure via a 403
        vs. 404 distinction).
        """

        session = await self._repository.get_by_id(session_id)
        if session is None or session.user_id != user_id:
            raise SessionNotFoundError(f"No session found with id {session_id}")
        return session

    async def list_sessions_for_user(self, *, user_id: uuid.UUID) -> list[Session]:
        """List a user's sessions, most-recently-updated first (PRD §6.2)."""

        return await self._repository.list_for_user(user_id=user_id)

    async def get_session_with_history(self, *, session_id: uuid.UUID, user_id: uuid.UUID) -> Session:
        """Resolve a session plus its full ordered message history, for the
        "continue previous session" flow (PRD §6.2 acceptance criteria).

        Re-checks ownership independently of `get_owned_session` (this
        method may be called directly, not only via the FastAPI dependency
        chain) rather than trusting a caller-supplied `session_id` alone.
        """

        session = await self._repository.get_by_id_with_messages(session_id)
        if session is None or session.user_id != user_id:
            raise SessionNotFoundError(f"No session found with id {session_id}")
        return session

    async def append_message(
        self,
        *,
        session_id: uuid.UUID,
        role: str,
        content: str,
        skill_used: str | None = None,
    ) -> Message:
        """Persist a single message (user or assistant/system) into a
        session.

        Called by `skills/skill_router.py` for both the inbound user
        message and the resulting assistant reply (and any `system`
        breadcrumbs it chooses to record — see DATABASE_SCHEMA.md CHANGE 1).

        Ownership is assumed already-verified by the caller (the
        `POST /sessions/{session_id}/messages` route depends on
        `get_owned_session` before this ever runs) — this method only
        checks that the session still exists, to fail with a clear domain
        error rather than a raw FK-violation if it was removed mid-request.
        """

        session = await self._repository.get_by_id(session_id)
        if session is None:
            raise SessionNotFoundError(f"No session found with id {session_id}")

        if role == "user" and session.title == DEFAULT_SESSION_TITLE:
            session.title = self.derive_title_from_first_message(content)

        return await self._repository.add_message(
            session_id=session_id, role=role, content=content, skill_used=skill_used
        )

    @staticmethod
    def derive_title_from_first_message(content: str) -> str:
        """Derive a session title from the first user message (PRD §6.2).

        Collapses whitespace/newlines (chat input is often multi-line) and
        truncates to `_TITLE_MAX_LENGTH`, matching the sidebar's need for a
        short, single-line label.
        """

        collapsed = " ".join(content.split())
        if not collapsed:
            return DEFAULT_SESSION_TITLE
        if len(collapsed) <= _TITLE_MAX_LENGTH:
            return collapsed
        cutoff = _TITLE_MAX_LENGTH - len(_TITLE_TRUNCATION_SUFFIX)
        return collapsed[:cutoff].rstrip() + _TITLE_TRUNCATION_SUFFIX
