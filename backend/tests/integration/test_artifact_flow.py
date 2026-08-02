"""Smoke test: artifact retrieval (PRD §6.6) — list / get / download, served
via `sessions/router.py` (artifacts has no router of its own, per
REPOSITORY_STRUCTURE.md's MVP simplification)."""

import uuid

from app.domains.artifacts.dependencies import get_artifact_repository
from app.domains.artifacts.repository import ArtifactRepository
from app.domains.sessions.dependencies import get_session_repository
from app.domains.sessions.repository import SessionRepository
from app.main import app
from tests.conftest import FakeAsyncSession


def _create_session_and_artifact(client, shared_db: FakeAsyncSession) -> tuple[str, str]:
    import asyncio

    session_id = client.post("/sessions", json={"title": None}).json()["id"]

    # Seed an artifact directly through the real repository (as a skill
    # would), rather than via HTTP -- there is no artifact-creation
    # endpoint (artifacts are only ever created as a skill side effect).
    repo = ArtifactRepository(shared_db)
    artifact = asyncio.run(
        repo.create(
            session_id=uuid.UUID(session_id),
            message_id=uuid.uuid4(),
            artifact_type="qa_answer",
            content_markdown="# Activation\n\nGetting users to value fast.",
        )
    )
    return session_id, str(artifact.id)


def test_list_session_artifacts(client, current_user):
    shared_db = FakeAsyncSession()
    app.dependency_overrides[get_session_repository] = lambda: SessionRepository(shared_db)
    app.dependency_overrides[get_artifact_repository] = lambda: ArtifactRepository(shared_db)

    session_id, artifact_id = _create_session_and_artifact(client, shared_db)

    response = client.get(f"/sessions/{session_id}/artifacts")

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["id"] == artifact_id
    assert body[0]["artifact_type"] == "qa_answer"


def test_get_single_artifact(client, current_user):
    shared_db = FakeAsyncSession()
    app.dependency_overrides[get_session_repository] = lambda: SessionRepository(shared_db)
    app.dependency_overrides[get_artifact_repository] = lambda: ArtifactRepository(shared_db)

    session_id, artifact_id = _create_session_and_artifact(client, shared_db)

    response = client.get(f"/sessions/{session_id}/artifacts/{artifact_id}")

    assert response.status_code == 200
    assert response.json()["content_markdown"] == "# Activation\n\nGetting users to value fast."


def test_download_artifact_returns_raw_markdown(client, current_user):
    shared_db = FakeAsyncSession()
    app.dependency_overrides[get_session_repository] = lambda: SessionRepository(shared_db)
    app.dependency_overrides[get_artifact_repository] = lambda: ArtifactRepository(shared_db)

    session_id, artifact_id = _create_session_and_artifact(client, shared_db)

    response = client.get(f"/sessions/{session_id}/artifacts/{artifact_id}/download")

    assert response.status_code == 200
    assert response.text == "# Activation\n\nGetting users to value fast."
    assert response.headers["content-type"].startswith("text/plain")


def test_get_nonexistent_artifact_returns_404_not_500(client, current_user):
    shared_db = FakeAsyncSession()
    app.dependency_overrides[get_session_repository] = lambda: SessionRepository(shared_db)
    app.dependency_overrides[get_artifact_repository] = lambda: ArtifactRepository(shared_db)

    session_id = client.post("/sessions", json={"title": None}).json()["id"]

    response = client.get(f"/sessions/{session_id}/artifacts/{uuid.uuid4()}")

    assert response.status_code == 404
    assert response.json()["error_code"] == "artifact_not_found"
