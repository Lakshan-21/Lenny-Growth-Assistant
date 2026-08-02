"""Session HTTP endpoints: create, list, get-with-history — plus, per the
MVP simplification (REPOSITORY_STRUCTURE.md), the artifact-access surface
for a session's artifacts (list/retrieve/download), since `artifacts/`
has no router of its own.

Note on route ownership (implementation assumption — see generation
summary): the message-posting/skill-invocation endpoint
(`POST /sessions/{session_id}/messages`) is implemented in
`skills/router.py`, not here, because it requires the skill-dispatch
stack that domain owns. This router covers session CRUD and artifact
read access only.
"""

import uuid

from fastapi import APIRouter, Depends, status
from fastapi.responses import PlainTextResponse

from app.domains.artifacts.dependencies import get_artifact_service
from app.domains.artifacts.schemas import ArtifactRead
from app.domains.artifacts.service import ArtifactService
from app.domains.auth.dependencies import AuthenticatedUser, get_current_user
from app.domains.sessions.dependencies import get_owned_session, get_session_service
from app.domains.sessions.models import Session
from app.domains.sessions.schemas import SessionCreate, SessionDetailRead, SessionListItem
from app.domains.sessions.service import SessionService

router = APIRouter(prefix="/sessions", tags=["sessions"])


@router.post("", response_model=SessionDetailRead, status_code=status.HTTP_201_CREATED)
async def create_session(
    data: SessionCreate,
    current_user: AuthenticatedUser = Depends(get_current_user),
    session_service: SessionService = Depends(get_session_service),
) -> SessionDetailRead:
    """Start a new chat-based session (PRD §6.2)."""

    session = await session_service.create_session(user_id=current_user.id, data=data)

    # Explicit DTO construction, not response_model auto-conversion from the
    # raw ORM object: `session.messages` is never eagerly loaded by
    # SessionRepository.create() (there's nothing to load — session.id is a
    # server-generated id that cannot have any Message rows referencing it
    # yet). Letting Pydantic's `from_attributes` touch `session.messages`
    # here would trigger SQLAlchemy's lazy loader on an already-persistent
    # object outside of a greenlet context (MissingGreenlet) — see
    # module docstring / bugfix notes. `messages=[]` is asserted directly
    # from that invariant instead of read off the ORM object.
    return SessionDetailRead(
        id=session.id,
        user_id=session.user_id,
        title=session.title,
        created_at=session.created_at,
        updated_at=session.updated_at,
        messages=[],
    )


@router.get("", response_model=list[SessionListItem])
async def list_sessions(
    current_user: AuthenticatedUser = Depends(get_current_user),
    session_service: SessionService = Depends(get_session_service),
) -> list[Session]:
    """List the current user's sessions, most-recent first (session sidebar, PRD §6.2)."""

    return await session_service.list_sessions_for_user(user_id=current_user.id)


@router.get("/{session_id}", response_model=SessionDetailRead)
async def get_session(
    session: Session = Depends(get_owned_session),
    session_service: SessionService = Depends(get_session_service),
) -> Session:
    """Resume a session with full message history (PRD §6.2, "continue previous sessions")."""

    return await session_service.get_session_with_history(session_id=session.id, user_id=session.user_id)


@router.get("/{session_id}/artifacts", response_model=list[ArtifactRead])
async def list_session_artifacts(
    session: Session = Depends(get_owned_session),
    artifact_service: ArtifactService = Depends(get_artifact_service),
) -> list[ArtifactRead]:
    """List artifacts attached to a session (PRD §6.6). Delegates to
    `artifacts/service.py` — this domain has no router of its own (MVP
    simplification)."""

    return await artifact_service.list_for_session(session_id=session.id)


@router.get("/{session_id}/artifacts/{artifact_id}", response_model=ArtifactRead)
async def get_session_artifact(
    artifact_id: uuid.UUID,
    session: Session = Depends(get_owned_session),
    artifact_service: ArtifactService = Depends(get_artifact_service),
) -> ArtifactRead:
    """Retrieve a single artifact (rendered per PRD §6.6 — Markdown/HTML)."""

    return await artifact_service.get_for_session(session_id=session.id, artifact_id=artifact_id)


@router.get("/{session_id}/artifacts/{artifact_id}/download", response_class=PlainTextResponse)
async def download_session_artifact(
    artifact_id: uuid.UUID,
    session: Session = Depends(get_owned_session),
    artifact_service: ArtifactService = Depends(get_artifact_service),
) -> str:
    """Download an artifact as raw Markdown (PRD §6.6, "Download markdown").

    Returns `content_markdown` verbatim — no transformation (see ADR-4,
    ARCHITECTURE.md).
    """

    return await artifact_service.get_markdown_for_download(session_id=session.id, artifact_id=artifact_id)
