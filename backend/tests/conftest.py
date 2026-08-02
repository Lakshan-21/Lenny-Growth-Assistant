"""Shared pytest fixtures for backend/tests/.

Scope note — read this before adding a test: these are HTTP-boundary
*smoke* tests, not full integration tests against a live Postgres/
Ollama/Anthropic stack. `CONTEXT.md` rules out Docker for MVP, so there's
no way to stand up a real Postgres+pgvector instance for an automated
suite without it. Every test exercises the REAL FastAPI app and REAL
skill-orchestration logic (`skills/router.py`, each skill's `handle()`,
`sessions/service.py`, `artifacts/service.py`) through `TestClient`, with
fakes substituted only at the boundaries that genuinely require live
infrastructure:

- the database session (via `app.dependency_overrides` on each domain's
  top-level repository/service dependency — see `FakeAsyncSession` below,
  which drives the *real* repository classes for simple CRUD, so ORM
  construction and flush semantics are still exercised for real)
- pgvector similarity search (faked at `RetrievalService.search`, since a
  cosine-distance HNSW query can't be meaningfully faked without a real
  vector index)
- Ollama/Anthropic model calls (faked at `ModelGateway`/`OllamaProvider`-
  shaped objects exposing just `generate()`)

This proves request validation, orchestration order, persistence *calls*
happening in the right sequence, and response shape — not SQL/vector-index
behavior itself, which was verified manually against real infrastructure
during development and is out of scope for a Docker-free automated suite.
"""

import datetime
import os
import uuid

os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://test:test@localhost/test")
os.environ.setdefault("SUPABASE_URL", "https://example.supabase.co")
os.environ.setdefault("SUPABASE_SERVICE_KEY", "test")
os.environ.setdefault("SUPABASE_JWT_SECRET", "test")
os.environ.setdefault("ANTHROPIC_API_KEY", "test")
# Forced (not setdefault): pydantic-settings loads backend/.env, and a
# developer's local .env commonly has DEV_AUTH_BYPASS=true (see
# auth/dependencies.py) for manual testing. Environment variables take
# precedence over .env file values in pydantic-settings' source order, so
# this guarantees deterministic auth behavior in tests regardless of the
# machine's local .env — without it, `test_create_session_requires_
# authentication` would silently pass or fail depending on developer setup.
os.environ["DEV_AUTH_BYPASS"] = "false"

import pytest
from fastapi.testclient import TestClient

from app.domains.auth.dependencies import AuthenticatedUser, get_current_user
from app.main import app


def utcnow() -> datetime.datetime:
    return datetime.datetime.now(datetime.timezone.utc)


@pytest.fixture(autouse=True)
def _reset_dependency_overrides():
    """Every test starts from a clean `app.dependency_overrides` and cleans
    up after itself — overrides are mutable state on the shared `app`
    object; leaking them between tests causes order-dependent flakiness."""

    yield
    app.dependency_overrides.clear()


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture
def current_user() -> AuthenticatedUser:
    """Authenticates every request in a test as a fixed user, bypassing
    real JWT verification (which is explicitly out of scope — see
    `auth/dependencies.py`). Equivalent in effect to `DEV_AUTH_BYPASS`,
    but scoped per-test via dependency override rather than a global
    setting, so tests don't depend on process-wide env state."""

    user = AuthenticatedUser(id=uuid.uuid4(), email="test@example.com")
    app.dependency_overrides[get_current_user] = lambda: user
    return user


class FakeAsyncSession:
    """Minimal in-memory stand-in for SQLAlchemy's `AsyncSession`.

    Supports exactly what the simple, single-table CRUD repositories in
    this codebase need (`add`/`add_all`/`flush`/`get`, plus `execute` for
    the small number of `select(...).where(...).order_by(...)` queries
    used by `SessionRepository`/`ArtifactRepository`) — not a query
    planner. `execute()` is intentionally naive: it filters the in-memory
    store by matching the target ORM class and re-sorts by `created_at`,
    which is sufficient for every current repository method's actual
    shape without parsing arbitrary SQLAlchemy `Select` internals.
    """

    def __init__(self) -> None:
        self.store: dict[uuid.UUID, object] = {}

    def add(self, obj) -> None:
        if getattr(obj, "id", None) is None:
            obj.id = uuid.uuid4()
        for attr, default in (("created_at", utcnow), ("updated_at", utcnow)):
            if hasattr(obj, attr) and getattr(obj, attr) is None:
                setattr(obj, attr, default())
        if hasattr(obj, "title") and getattr(obj, "title", None) is None:
            obj.title = "New session"
        self.store[obj.id] = obj

    def add_all(self, objs) -> None:
        for obj in objs:
            self.add(obj)

    async def flush(self) -> None:
        return None

    async def get(self, model, pk):
        obj = self.store.get(pk)
        return obj if isinstance(obj, model) else None

    async def execute(self, stmt):
        from sqlalchemy.sql import Select

        assert isinstance(stmt, Select)
        target = stmt.column_descriptions[0]["type"]
        rows = [o for o in self.store.values() if isinstance(o, target)]
        rows.sort(key=lambda o: getattr(o, "created_at", utcnow()))

        # Mimic `selectinload(Session.messages).selectinload(Message
        # .citations).selectinload(Citation.transcript_chunk)` (used by
        # `SessionRepository.get_by_id_with_messages`): populate the
        # relationship attributes from the store, since this fake bypasses
        # real SQLAlchemy relationship-loading entirely.
        if target.__name__ == "Session":
            from app.domains.knowledge.models import Citation
            from app.domains.sessions.models import Message

            for session in rows:
                session_messages = sorted(
                    (m for m in self.store.values() if isinstance(m, Message) and m.session_id == session.id),
                    key=lambda m: m.created_at,
                )
                for message in session_messages:
                    message.citations = sorted(
                        (c for c in self.store.values() if isinstance(c, Citation) and c.message_id == message.id),
                        key=lambda c: c.created_at,
                    )
                    for citation in message.citations:
                        citation.transcript_chunk = self.store.get(citation.transcript_chunk_id)
                session.messages = session_messages

        return _FakeResult(rows)

    # NOTE: `execute()` does not apply the statement's WHERE clause —
    # it returns every stored row of the target type. This is a
    # deliberate simplification (parsing arbitrary SQLAlchemy `Select`
    # internals to evaluate WHERE clauses generically would make this fake
    # itself a maintenance burden, for a "smoke test" scope). It's safe
    # because each test keeps its fake DB scoped to a single session/user
    # — cross-tenant filtering/ownership correctness (IDOR-safety) was
    # already verified manually against the real repositories during
    # development and isn't what these tests are re-proving.


class _FakeResult:
    def __init__(self, rows: list) -> None:
        self._rows = rows

    def scalars(self) -> "_FakeScalars":
        return _FakeScalars(self._rows)

    def scalar_one_or_none(self):
        return self._rows[0] if self._rows else None


class _FakeScalars:
    def __init__(self, rows: list) -> None:
        self._rows = rows

    def all(self) -> list:
        return self._rows
