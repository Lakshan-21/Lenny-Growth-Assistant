"""Data-access layer for `Session`/`Message` rows.

Constructor-injected with an `AsyncSession` (per the project's DI
convention) — never imports `database.session` directly.

Transaction ownership: `app.database.session.get_db` commits once per
request (and rolls back on any unhandled exception) — see that module's
docstring. Methods here therefore only `add()`/`flush()`; they never call
`commit()` or `rollback()` themselves. `flush()` is still used after every
insert because Postgres populates several columns server-side (`id` via
`gen_random_uuid()`, `created_at`/`updated_at` via `now()`, `title` via its
column default) — flushing lets SQLAlchemy's `RETURNING`-based population
fill those in on the ORM instance immediately, so the object is fully
populated for response serialization before the request's final commit.
"""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.domains.knowledge.models import Citation
from app.domains.sessions.models import Message, Session


class SessionRepository:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def create(self, *, user_id: uuid.UUID, title: str | None) -> Session:
        """Insert a new `Session` row.

        `title=None` omits the column from the INSERT entirely so
        Postgres's `server_default('New session')` applies
        (DATABASE_SCHEMA.md §2) — passing `title=None` explicitly would
        instead try to insert a literal NULL into a NOT NULL column.
        """

        session = Session(user_id=user_id) if title is None else Session(user_id=user_id, title=title)
        self._db.add(session)
        await self._db.flush()
        return session

    async def get_by_id(self, session_id: uuid.UUID) -> Session | None:
        """Fetch a session by id, no ownership filter — callers that need
        ownership enforcement do it themselves (see
        `service.get_owned_session`); this method is also used internally
        for existence checks that don't require an ownership decision.
        """

        return await self._db.get(Session, session_id)

    async def get_by_id_with_messages(self, session_id: uuid.UUID) -> Session | None:
        """Fetch a session with its messages — and each message's
        citations, and each citation's transcript chunk (needed for
        `Citation.excerpt`, see `knowledge/models.py`) — eagerly loaded,
        ordered by `created_at` ascending (matches
        `idx_messages_session_created`, DATABASE_SCHEMA.md §4).

        Eager loading (`selectinload`) is required, not just an
        optimization: under async SQLAlchemy, accessing an unloaded
        `relationship()` outside this call would raise `MissingGreenlet`
        rather than lazily querying — messages, citations, and transcript
        chunks must all be loaded here, in-session, up front.
        """

        stmt = (
            select(Session)
            .where(Session.id == session_id)
            .options(
                selectinload(Session.messages)
                .selectinload(Message.citations)
                .selectinload(Citation.transcript_chunk)
            )
        )
        result = await self._db.execute(stmt)
        return result.scalar_one_or_none()

    async def list_for_user(self, *, user_id: uuid.UUID) -> list[Session]:
        """`SELECT ... WHERE user_id = :user_id ORDER BY updated_at DESC`
        (matches `idx_sessions_user_recency`, DATABASE_SCHEMA.md §4)."""

        stmt = select(Session).where(Session.user_id == user_id).order_by(Session.updated_at.desc())
        result = await self._db.execute(stmt)
        return list(result.scalars().all())

    async def list_messages(self, *, session_id: uuid.UUID) -> list[Message]:
        """`SELECT ... WHERE session_id = :session_id ORDER BY created_at`
        (matches `idx_messages_session_created`, DATABASE_SCHEMA.md §4)."""

        stmt = (
            select(Message)
            .where(Message.session_id == session_id)
            .order_by(Message.created_at.asc())
        )
        result = await self._db.execute(stmt)
        return list(result.scalars().all())

    async def add_message(
        self,
        *,
        session_id: uuid.UUID,
        role: str,
        content: str,
        skill_used: str | None = None,
    ) -> Message:
        """Insert a new `Message` row.

        Note: `sessions.updated_at` is kept current by the DB trigger
        `touch_session_updated_at` (DATABASE_SCHEMA.md §2) — not touched
        here explicitly, and any in-memory `Session.updated_at` already
        loaded elsewhere in this transaction will not reflect it without
        a re-fetch (the trigger runs server-side, outside the ORM's view).
        """

        message = Message(session_id=session_id, role=role, content=content, skill_used=skill_used)
        self._db.add(message)
        await self._db.flush()
        return message
