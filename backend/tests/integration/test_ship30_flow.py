"""Smoke test: Ship30 flow (PRD §6.5) — transforms session content into a
LinkedIn post / X thread / article, persisted as an Artifact."""

from app.domains.artifacts.dependencies import get_artifact_repository
from app.domains.artifacts.models import Artifact
from app.domains.artifacts.repository import ArtifactRepository
from app.domains.sessions.dependencies import get_session_repository
from app.domains.sessions.repository import SessionRepository
from app.domains.skills.dependencies import get_ship30_skill
from app.domains.skills.ship30.service import Ship30Skill
from app.main import app
from tests.conftest import FakeAsyncSession


class _FakeGateway:
    def __init__(self, completion: str) -> None:
        self._completion = completion

    async def generate(self, *, prompt, system=None):
        return self._completion


def _wire_ship30(shared_db: FakeAsyncSession, completion: str) -> None:
    from app.domains.artifacts.service import ArtifactService

    app.dependency_overrides[get_session_repository] = lambda: SessionRepository(shared_db)
    app.dependency_overrides[get_artifact_repository] = lambda: ArtifactRepository(shared_db)
    artifact_service = ArtifactService(ArtifactRepository(shared_db))
    app.dependency_overrides[get_ship30_skill] = lambda: Ship30Skill(
        model_gateway=_FakeGateway(completion), artifact_service=artifact_service
    )


def test_ship30_linkedin_post_persists_artifact(client, current_user):
    shared_db = FakeAsyncSession()
    _wire_ship30(shared_db, "Activation is everything.\n\nWhat's your take?")

    session_id = client.post("/sessions", json={"title": None}).json()["id"]
    response = client.post(
        f"/sessions/{session_id}/messages",
        json={"content": "turn this into a post", "mode": "manual", "skill": "ship30", "content_type": "linkedin_post"},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["skill_used"] == "ship30"
    assert body["artifact_id"] is not None

    artifacts = [o for o in shared_db.store.values() if isinstance(o, Artifact)]
    assert len(artifacts) == 1
    assert artifacts[0].artifact_type == "linkedin_post"
    assert artifacts[0].content_markdown == body["message"]["content"]


def test_ship30_x_thread_segments_and_persists(client, current_user):
    shared_db = FakeAsyncSession()
    _wire_ship30(shared_db, "Hook tweet.\n\nSecond point.\n\nThird point.")

    session_id = client.post("/sessions", json={"title": None}).json()["id"]
    response = client.post(
        f"/sessions/{session_id}/messages",
        json={"content": "make it a thread", "mode": "manual", "skill": "ship30", "content_type": "x_thread"},
    )

    assert response.status_code == 201
    artifacts = [o for o in shared_db.store.values() if isinstance(o, Artifact)]
    assert artifacts[0].artifact_type == "x_thread"
    assert "**1/3**" in artifacts[0].content_markdown


def test_ship30_requires_content_type(client, current_user):
    shared_db = FakeAsyncSession()
    app.dependency_overrides[get_session_repository] = lambda: SessionRepository(shared_db)

    session_id = client.post("/sessions", json={"title": None}).json()["id"]
    response = client.post(
        f"/sessions/{session_id}/messages",
        json={"content": "turn this into a post", "mode": "manual", "skill": "ship30"},
    )

    assert response.status_code == 422
