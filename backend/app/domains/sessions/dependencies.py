"""FastAPI dependency wiring for the sessions domain."""

import uuid

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_db
from app.domains.auth.dependencies import AuthenticatedUser, get_current_user
from app.domains.sessions.models import Session
from app.domains.sessions.repository import SessionRepository
from app.domains.sessions.service import SessionService


def get_session_repository(db: AsyncSession = Depends(get_db)) -> SessionRepository:
    return SessionRepository(db)


def get_session_service(
    repository: SessionRepository = Depends(get_session_repository),
) -> SessionService:
    return SessionService(repository)


async def get_owned_session(
    session_id: uuid.UUID,
    current_user: AuthenticatedUser = Depends(get_current_user),
    session_service: SessionService = Depends(get_session_service),
) -> Session:
    """Path-level dependency: resolves `{session_id}` and enforces that it
    belongs to the current user. Raises `SessionNotFoundError` otherwise
    (see sessions/exceptions.py) — used by every session-scoped route,
    including the artifact-access routes added per the MVP simplification.
    """

    return await session_service.get_owned_session(session_id=session_id, user_id=current_user.id)
