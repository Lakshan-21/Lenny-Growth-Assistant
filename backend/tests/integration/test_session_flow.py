"""Smoke test: session creation (PRD §6.2)."""

import uuid

from app.domains.sessions.dependencies import get_session_repository
from app.domains.sessions.repository import SessionRepository
from app.main import app
from tests.conftest import FakeAsyncSession


def test_create_session_returns_expected_shape(client, current_user):
    app.dependency_overrides[get_session_repository] = lambda: SessionRepository(FakeAsyncSession())

    response = client.post("/sessions", json={"title": None})

    assert response.status_code == 201
    body = response.json()
    assert body["user_id"] == str(current_user.id)
    assert body["title"] == "New session"
    assert body["messages"] == []
    assert uuid.UUID(body["id"])  # a real id was assigned


def test_create_session_with_explicit_title(client, current_user):
    app.dependency_overrides[get_session_repository] = lambda: SessionRepository(FakeAsyncSession())

    response = client.post("/sessions", json={"title": "My growth research"})

    assert response.status_code == 201
    assert response.json()["title"] == "My growth research"


def test_create_session_requires_authentication(client):
    # No `current_user` fixture applied -> get_current_user runs for real;
    # DEV_AUTH_BYPASS defaults to False, so a missing token is rejected.
    response = client.post("/sessions", json={"title": None})

    assert response.status_code == 401
