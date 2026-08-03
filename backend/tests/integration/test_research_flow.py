"""Smoke test: Research flow (PRD §6.4) — multi-query retrieval -> dedup ->
synthesis -> Artifact + ResearchBrief persistence."""

import re
import uuid

from app.domains.artifacts.dependencies import get_artifact_repository
from app.domains.artifacts.models import Artifact, ResearchBrief
from app.domains.artifacts.repository import ArtifactRepository
from app.domains.knowledge.dependencies import get_knowledge_repository
from app.domains.knowledge.repository import KnowledgeRepository
from app.domains.knowledge.schemas import EpisodeRead, TranscriptChunkRead
from app.domains.sessions.dependencies import get_session_repository
from app.domains.sessions.repository import SessionRepository
from app.domains.skills.dependencies import get_research_skill
from app.domains.skills.qa.citation_builder import CitationBuilder
from app.domains.skills.research.prompts import INSUFFICIENT_EVIDENCE_MARKER
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
            # A bullet, not a numbered list: the frontend's Research-tab
            # source-count parser (`parseResearchBriefPreview`) matches
            # `^\d+\.\s+\S` across the *entire* markdown, not scoped to the
            # `## Citations` section -- a numbered Recommended Actions list
            # would be miscounted as extra "sources". That's a real,
            # pre-existing latent bug in the frontend parser, out of scope
            # for this task; avoided here so this fixture doesn't trip over
            # it while testing something else. Flagged separately.
            "## Recommended Actions\n- Define one activation metric.\n"
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

    # UX redesign (Option B): the chat message carries only the title,
    # executive summary, and a pointer to the Research tab -- not the full
    # brief. See test_research_chat_message_shows_title_summary_and_cta_only
    # and test_research_artifact_persists_full_brief below for the detailed,
    # dedicated coverage of each half of this split.
    content = body["message"]["content"]
    assert "# What drives growth?" in content
    assert "Growth needs both activation and retention." in content
    assert "Research tab" in content
    for heading in ("## Key Insights", "## Supporting Evidence", "## Recommended Actions", "## Citations"):
        assert heading not in content

    # Both the Artifact and the ResearchBrief specialization row were persisted.
    briefs = [o for o in shared_db.store.values() if isinstance(o, ResearchBrief)]
    assert len(briefs) == 1
    assert briefs[0].artifact_id == uuid.UUID(body["artifact_id"])
    assert briefs[0].topic == "What drives growth?"

    # The Artifact -- not the chat message -- carries the full brief.
    artifacts = [o for o in shared_db.store.values() if isinstance(o, Artifact)]
    assert len(artifacts) == 1
    for heading in ("## Executive Summary", "## Key Insights", "## Supporting Evidence", "## Recommended Actions", "## Citations"):
        assert heading in artifacts[0].content_markdown


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
    assert body["message"]["content"] == (
        "The available sources do not contain sufficient information to create a research brief on this topic."
    )


class _OffTopicModelGateway:
    """Retrieval returned *something* (unlike `_EmptyRetrievalService`
    above), but none of it actually covers the requested topic — per the
    new `RESEARCH_SYSTEM_PROMPT`/`build_research_prompt` contract, a
    well-behaved model responds with the insufficient-evidence marker
    instead of broadening the topic to whatever the excerpts *do* cover."""

    async def generate(self, *, prompt, system=None):
        if system and "search queries" in system.lower():
            return "personal branding\npersonal brand strategy"
        return INSUFFICIENT_EVIDENCE_MARKER


def test_research_topic_drift_returns_explicit_message_no_artifact(client, current_user):
    """Guards the exact bug this was built to fix: retrieved chunks are
    non-empty but topically off-target (e.g. career-coaching content
    returned for a "personal branding" request) -- the response must be
    the exact insufficient-evidence message, with no artifact/citations,
    not a brief synthesized from off-topic excerpts."""

    shared_db = FakeAsyncSession()
    app.dependency_overrides[get_session_repository] = lambda: SessionRepository(shared_db)
    app.dependency_overrides[get_knowledge_repository] = lambda: KnowledgeRepository(shared_db)
    app.dependency_overrides[get_research_skill] = lambda: ResearchSkill(
        retrieval_service=_FakeRetrievalService(),  # returns CHUNK_A/CHUNK_SHARED -- non-empty, off-topic
        model_gateway=_OffTopicModelGateway(),
        synthesizer=ResearchSynthesizer(),
        citation_builder=CitationBuilder(),
    )

    session_id = client.post("/sessions", json={"title": None}).json()["id"]
    response = client.post(
        f"/sessions/{session_id}/messages",
        json={"content": "Create a research brief on personal branding strategies", "mode": "manual", "skill": "research"},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["citations"] == []
    assert body["artifact_id"] is None
    assert body["message"]["content"] == (
        "The available sources do not contain sufficient information to create a research brief on this topic."
    )


def _post_research_message(client, content: str = "What drives growth?"):
    session_id = client.post("/sessions", json={"title": None}).json()["id"]
    return client.post(
        f"/sessions/{session_id}/messages",
        json={"content": content, "mode": "manual", "skill": "research"},
    )


def _wire_grounded_research(shared_db: FakeAsyncSession) -> None:
    app.dependency_overrides[get_session_repository] = lambda: SessionRepository(shared_db)
    app.dependency_overrides[get_knowledge_repository] = lambda: KnowledgeRepository(shared_db)
    app.dependency_overrides[get_artifact_repository] = lambda: ArtifactRepository(shared_db)
    app.dependency_overrides[get_research_skill] = lambda: ResearchSkill(
        retrieval_service=_FakeRetrievalService(),
        model_gateway=_FakeModelGateway(),
        synthesizer=ResearchSynthesizer(),
        citation_builder=CitationBuilder(),
    )


def test_research_chat_message_shows_title_summary_and_cta_only(client, current_user):
    """Requirement: chat displays research title, executive summary only,
    and a clear call-to-action pointing at the Research tab -- never the
    full brief (Key Insights/Supporting Evidence/Recommended Actions/
    Citations are Artifact-only, per test_research_artifact_persists_full_brief)."""

    shared_db = FakeAsyncSession()
    _wire_grounded_research(shared_db)

    response = _post_research_message(client)
    content = response.json()["message"]["content"]

    assert content.startswith("# What drives growth?")
    assert "Growth needs both activation and retention." in content
    assert "Research tab" in content
    for heading in ("## Key Insights", "## Supporting Evidence", "## Recommended Actions", "## Citations"):
        assert heading not in content


def test_research_artifact_persists_full_brief(client, current_user):
    """Requirement: the full brief -- all four sections plus the citations
    list -- lives in the persisted Artifact regardless of what the chat
    message shows. The chat-only call-to-action text must not leak into
    the artifact either."""

    shared_db = FakeAsyncSession()
    _wire_grounded_research(shared_db)

    response = _post_research_message(client)
    artifact_id = uuid.UUID(response.json()["artifact_id"])

    artifacts = [o for o in shared_db.store.values() if isinstance(o, Artifact) and o.id == artifact_id]
    assert len(artifacts) == 1
    artifact_content = artifacts[0].content_markdown

    assert artifact_content.startswith("# What drives growth?")
    for heading in ("## Executive Summary", "## Key Insights", "## Supporting Evidence", "## Recommended Actions", "## Citations"):
        assert heading in artifact_content
    assert "Research tab" not in artifact_content


def test_research_artifact_content_matches_research_tab_parsing_contract(client, current_user):
    """The frontend Research tab (`lib/research-brief-preview.ts`::
    parseResearchBriefPreview) has no dedicated test suite -- this project
    has no frontend test runner configured (checked: no "test" script,
    no vitest/jest in package.json). This test protects that rendering
    contract from the backend side instead: the persisted artifact's
    content_markdown must keep the exact shape the frontend parser reads
    -- a leading `# {title}` line, a plain-text paragraph immediately
    after it (the parser's "summary" teaser), and a `## Citations` section
    of `N. label` lines (the parser's source count)."""

    shared_db = FakeAsyncSession()
    _wire_grounded_research(shared_db)

    response = _post_research_message(client)
    body = response.json()
    artifact_id = uuid.UUID(body["artifact_id"])

    artifacts = [o for o in shared_db.store.values() if isinstance(o, Artifact) and o.id == artifact_id]
    lines = artifacts[0].content_markdown.split("\n")

    title_line = next(line for line in lines if line.strip().startswith("# "))
    assert title_line == "# What drives growth?"

    title_index = lines.index(title_line)
    summary_line = next(line for line in lines[title_index + 1 :] if line.strip() and not line.strip().startswith("#"))
    assert summary_line.strip() == "Growth needs both activation and retention."

    citation_lines = [line for line in lines if re.match(r"^\d+\.\s+\S", line.strip())]
    assert len(citation_lines) == len(body["citations"])
