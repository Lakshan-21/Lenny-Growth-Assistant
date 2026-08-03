"""Smoke test: QA flow (PRD §6.3) — retrieval -> grounded generation -> citations."""

import uuid

from app.domains.knowledge.dependencies import get_knowledge_repository
from app.domains.knowledge.models import TranscriptChunk
from app.domains.knowledge.repository import KnowledgeRepository
from app.domains.knowledge.schemas import EpisodeRead, TranscriptChunkRead
from app.domains.sessions.dependencies import get_session_repository
from app.domains.sessions.repository import SessionRepository
from app.domains.skills.dependencies import get_qa_skill
from app.domains.skills.qa.citation_builder import CitationBuilder
from app.domains.skills.qa.prompts import INSUFFICIENT_EVIDENCE_MARKER
from app.domains.skills.qa.service import QASkill
from app.main import app
from tests.conftest import FakeAsyncSession

EPISODE_ID = uuid.uuid4()
CHUNK_ID = uuid.uuid4()
EXCERPT = "Activation is time to first value."


class _FakeRetrievalService:
    async def search(self, *, query_text, top_k=8, episode_ids=None):
        return [
            TranscriptChunkRead(
                id=CHUNK_ID, episode_id=EPISODE_ID, content=EXCERPT,
                start_offset=0, end_offset=len(EXCERPT), start_timestamp_seconds=100, end_timestamp_seconds=110,
                episode=EpisodeRead(id=EPISODE_ID, title="Episode 142", guest_name=None, published_at=None, source_url=None),
            )
        ]


class _EmptyRetrievalService:
    async def search(self, *, query_text, top_k=8, episode_ids=None):
        return []


class _FakeModelGateway:
    async def generate(self, *, prompt, system=None):
        assert EXCERPT in prompt, "the retrieved excerpt must reach the prompt"
        return "Activation means getting to value fast [1]."


def _wire_common(shared_db: FakeAsyncSession) -> None:
    app.dependency_overrides[get_session_repository] = lambda: SessionRepository(shared_db)
    app.dependency_overrides[get_knowledge_repository] = lambda: KnowledgeRepository(shared_db)


def test_qa_answers_with_citations_and_excerpt(client, current_user):
    shared_db = FakeAsyncSession()
    _wire_common(shared_db)
    app.dependency_overrides[get_qa_skill] = lambda: QASkill(
        retrieval_service=_FakeRetrievalService(),
        model_gateway=_FakeModelGateway(),
        citation_builder=CitationBuilder(),
    )

    session_id = client.post("/sessions", json={"title": None}).json()["id"]
    response = client.post(f"/sessions/{session_id}/messages", json={"content": "What is activation?"})

    assert response.status_code == 201
    body = response.json()
    assert body["skill_used"] == "qa"
    assert body["artifact_id"] is None  # QA never produces an artifact
    assert "[1]" in body["message"]["content"]

    assert len(body["citations"]) == 1
    citation = body["citations"][0]
    assert citation["transcript_chunk_id"] == str(CHUNK_ID)
    assert citation["excerpt"] == EXCERPT
    assert "Episode 142" in citation["display_label"]

    # The same citation also appears nested under `message.citations`
    # (a smaller shape — no transcript_chunk_id, see sessions/schemas.py
    # ::CitationRead) — this is what `GET /sessions/{id}` will later
    # reflect for historical messages too.
    assert len(body["message"]["citations"]) == 1
    assert body["message"]["citations"][0]["excerpt"] == EXCERPT
    assert "Episode 142" in body["message"]["citations"][0]["display_label"]

    # Citation actually persisted (Citation row created via KnowledgeRepository).
    from app.domains.knowledge.models import Citation

    persisted_citations = [o for o in shared_db.store.values() if isinstance(o, Citation)]
    assert len(persisted_citations) == 1
    assert persisted_citations[0].transcript_chunk_id == CHUNK_ID


def test_qa_citations_persist_and_reappear_in_session_history(client, current_user):
    """A prior manual DB check confirmed the `Citation` row was already
    being persisted correctly — the gap was that `GET /sessions/{id}`
    never serialized it. This proves the fix end-to-end: POST once, then
    GET the session fresh (simulating a page reload, no reliance on
    anything held in memory from the POST) and confirm the citation is
    still there, attached to the right historical message.
    """

    shared_db = FakeAsyncSession()
    _wire_common(shared_db)
    # `Citation.excerpt` reads `transcript_chunk.content` (see
    # knowledge/models.py) — unlike the top-level POST response (built
    # straight from `result.citations`, no DB round trip needed), this
    # path requires a real TranscriptChunk row for the eager-loaded
    # relationship to resolve.
    shared_db.store[CHUNK_ID] = TranscriptChunk(
        id=CHUNK_ID,
        episode_id=EPISODE_ID,
        content=EXCERPT,
        start_offset=0,
        end_offset=len(EXCERPT),
        start_timestamp_seconds=100,
        end_timestamp_seconds=110,
    )
    app.dependency_overrides[get_qa_skill] = lambda: QASkill(
        retrieval_service=_FakeRetrievalService(),
        model_gateway=_FakeModelGateway(),
        citation_builder=CitationBuilder(),
    )

    session_id = client.post("/sessions", json={"title": None}).json()["id"]
    post_body = client.post(f"/sessions/{session_id}/messages", json={"content": "What is activation?"}).json()

    get_response = client.get(f"/sessions/{session_id}")
    assert get_response.status_code == 200
    messages = get_response.json()["messages"]
    assistant_message = next(m for m in messages if m["role"] == "assistant")

    assert len(assistant_message["citations"]) == 1
    citation = assistant_message["citations"][0]
    assert citation["excerpt"] == EXCERPT
    assert citation["display_label"] == post_body["message"]["citations"][0]["display_label"]


def test_qa_no_grounding_returns_explicit_message_not_error(client, current_user):
    shared_db = FakeAsyncSession()
    _wire_common(shared_db)
    app.dependency_overrides[get_qa_skill] = lambda: QASkill(
        retrieval_service=_EmptyRetrievalService(),
        model_gateway=_FakeModelGateway(),
        citation_builder=CitationBuilder(),
    )

    session_id = client.post("/sessions", json={"title": None}).json()["id"]
    response = client.post(f"/sessions/{session_id}/messages", json={"content": "unrelated question"})

    assert response.status_code == 201
    assert response.json()["citations"] == []
    assert "don't have enough information" in response.json()["message"]["content"]


class _WeaklyGroundedModelGateway:
    """Retrieval returned *something* (unlike `_EmptyRetrievalService`
    above) — non-empty, but not actually sufficient to answer the
    question. Per the new `QA_SYSTEM_PROMPT`/`build_qa_prompt` contract, a
    well-behaved model responds with the insufficient-evidence marker
    instead of stretching a partial/adjacent excerpt into a confident
    answer (the same enforcement `research/service.py` already has)."""

    async def generate(self, *, prompt, system=None):
        assert EXCERPT in prompt, "the retrieved excerpt must still reach the prompt"
        return INSUFFICIENT_EVIDENCE_MARKER


def test_qa_insufficient_grounding_returns_explicit_message_and_no_citations(client, current_user):
    """Guards the exact gap this was built to close: retrieval returns a
    non-empty, passes-the-similarity-threshold chunk that still doesn't
    substantively answer the question -- the response must be the
    standard no-grounding message with zero citations, not a confidently-
    worded answer with citations implying stronger grounding than
    actually exists."""

    shared_db = FakeAsyncSession()
    _wire_common(shared_db)
    app.dependency_overrides[get_qa_skill] = lambda: QASkill(
        retrieval_service=_FakeRetrievalService(),  # returns a real (non-empty) chunk
        model_gateway=_WeaklyGroundedModelGateway(),
        citation_builder=CitationBuilder(),
    )

    session_id = client.post("/sessions", json={"title": None}).json()["id"]
    response = client.post(f"/sessions/{session_id}/messages", json={"content": "What is personal branding?"})

    assert response.status_code == 201
    body = response.json()
    assert body["citations"] == []
    assert "don't have enough information" in body["message"]["content"]

    # Same guarantee reflected in the nested `message.citations` field
    # (what `GET /sessions/{id}` would later show for this historical message).
    assert body["message"]["citations"] == []

    # No `Citation` row was ever persisted for this message.
    from app.domains.knowledge.models import Citation

    persisted_citations = [o for o in shared_db.store.values() if isinstance(o, Citation)]
    assert persisted_citations == []
