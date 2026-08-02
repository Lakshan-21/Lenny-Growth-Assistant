"""Smoke test: Research flow (PRD §6.4) — multi-query retrieval -> dedup ->
synthesis -> Artifact + ResearchBrief persistence."""

import uuid

from app.domains.artifacts.dependencies import get_artifact_repository
from app.domains.artifacts.models import ResearchBrief
from app.domains.artifacts.repository import ArtifactRepository
from app.domains.knowledge.dependencies import get_knowledge_repository
from app.domains.knowledge.repository import KnowledgeRepository
from app.domains.knowledge.schemas import EpisodeRead, TranscriptChunkRead
from app.domains.sessions.dependencies import get_session_repository
from app.domains.sessions.repository import SessionRepository
from app.domains.skills.dependencies import get_research_skill
from app.domains.skills.qa.citation_builder import CitationBuilder
from app.domains.skills.research.service import ResearchSkill
from app.domains.skills.research.synthesis import ResearchSynthesizer
from app.main import app
from tests.conftest import FakeAsyncSession

EP1, EP2 = uuid.uuid4(), uuid.uuid4()
SHARED_CHUNK_ID = uuid.uuid4()


def _chunk(cid, ep_id, ep_title, content):
    return TranscriptChunkRead(
        id=cid, episode_id=ep_id, content=content, start_offset=0, end_offset=len(content),
        start_timestamp_seconds=10, end_timestamp_seconds=20,
        episode=EpisodeRead(id=ep_id, title=ep_title, guest_name=None, published_at=None, source_url=None),
    )


CHUNK_A = _chunk(uuid.uuid4(), EP1, "Episode 1: Activation", "Ship fast, learn faster.")
CHUNK_SHARED = _chunk(SHARED_CHUNK_ID, EP2, "Episode 2: Retention", "Retention starts with onboarding.")


class _FakeRetrievalService:
    """Returns overlapping results across sub-queries so dedup is exercised."""

    async def search(self, *, query_text, top_k=8, episode_ids=None):
        return [CHUNK_A, CHUNK_SHARED]


class _FakeModelGateway:
    async def generate(self, *, prompt, system=None):
        if system and "search queries" in system.lower():
            return "activation strategy\nretention loops"
        return (
            "## Executive Summary\nGrowth needs both activation and retention.\n\n"
            "## Key Insights\n- Time to value predicts retention.\n\n"
            "## Supporting Evidence\nMultiple episodes converge on this.\n\n"
            "## Recommended Actions\n1. Define one activation metric.\n"
        )


def test_research_produces_brief_with_artifact_and_deduped_citations(client, current_user):
    shared_db = FakeAsyncSession()
    app.dependency_overrides[get_session_repository] = lambda: SessionRepository(shared_db)
    app.dependency_overrides[get_knowledge_repository] = lambda: KnowledgeRepository(shared_db)
    app.dependency_overrides[get_artifact_repository] = lambda: ArtifactRepository(shared_db)
    app.dependency_overrides[get_research_skill] = lambda: ResearchSkill(
        retrieval_service=_FakeRetrievalService(),
        model_gateway=_FakeModelGateway(),
        synthesizer=ResearchSynthesizer(),
        citation_builder=CitationBuilder(),
    )

    session_id = client.post("/sessions", json={"title": None}).json()["id"]
    response = client.post(
        f"/sessions/{session_id}/messages",
        json={"content": "What drives growth?", "mode": "manual", "skill": "research"},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["skill_used"] == "research"
    assert body["artifact_id"] is not None

    # Same chunk returned by multiple sub-queries -> cited exactly once.
    chunk_ids = [c["transcript_chunk_id"] for c in body["citations"]]
    assert len(chunk_ids) == len(set(chunk_ids))
    assert str(SHARED_CHUNK_ID) in chunk_ids

    # Same dedup reflected in the nested `message.citations` field.
    assert len(body["message"]["citations"]) == len(body["citations"])

    content = body["message"]["content"]
    for heading in ("## Executive Summary", "## Key Insights", "## Supporting Evidence", "## Recommended Actions", "## Citations"):
        assert heading in content

    # Both the Artifact and the ResearchBrief specialization row were persisted.
    briefs = [o for o in shared_db.store.values() if isinstance(o, ResearchBrief)]
    assert len(briefs) == 1
    assert briefs[0].artifact_id == uuid.UUID(body["artifact_id"])
    assert briefs[0].topic == "What drives growth?"


class _EmptyRetrievalService:
    async def search(self, *, query_text, top_k=8, episode_ids=None):
        return []


def test_research_no_grounding_returns_explicit_message_no_artifact(client, current_user):
    shared_db = FakeAsyncSession()
    app.dependency_overrides[get_session_repository] = lambda: SessionRepository(shared_db)
    app.dependency_overrides[get_knowledge_repository] = lambda: KnowledgeRepository(shared_db)
    app.dependency_overrides[get_research_skill] = lambda: ResearchSkill(
        retrieval_service=_EmptyRetrievalService(),
        model_gateway=_FakeModelGateway(),
        synthesizer=ResearchSynthesizer(),
        citation_builder=CitationBuilder(),
    )

    session_id = client.post("/sessions", json={"title": None}).json()["id"]
    response = client.post(
        f"/sessions/{session_id}/messages",
        json={"content": "unrelated topic", "mode": "manual", "skill": "research"},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["citations"] == []
    assert body["artifact_id"] is None
    assert "don't have enough information" in body["message"]["content"]
