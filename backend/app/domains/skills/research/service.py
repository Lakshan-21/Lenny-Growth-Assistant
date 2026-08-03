"""Implements the Research `Skill`: multi-query retrieval -> dedup ->
synthesis (PRD §6.4)."""

import uuid
from typing import ClassVar

from app.domains.knowledge.retrieval_service import RetrievalService
from app.domains.knowledge.schemas import TranscriptChunkRead
from app.domains.providers.gateway import ModelGateway
from app.domains.skills.qa.citation_builder import CitationBuilder
from app.domains.skills.research.prompts import (
    INSUFFICIENT_EVIDENCE_MARKER,
    QUERY_EXPANSION_SYSTEM_PROMPT,
    RESEARCH_SYSTEM_PROMPT,
    build_query_expansion_prompt,
    build_research_prompt,
    parse_subqueries,
)
from app.domains.skills.research.schemas import ResearchBriefDraft
from app.domains.skills.research.synthesis import ResearchSynthesizer
from app.domains.skills.schemas import CitationRef, SkillContext, SkillResult

_NUM_SUBQUERIES = 4
_TOP_K_PER_QUERY = 5
_MAX_TOTAL_CHUNKS = 15
# Used for both "retrieval returned nothing at all" and "retrieval returned
# chunks, but the model itself judged them topically insufficient" (see
# `INSUFFICIENT_EVIDENCE_MARKER` check in `handle()` below) — from the
# user's perspective both are the same outcome, so they share one exact,
# specified message rather than two subtly different ones.
_INSUFFICIENT_EVIDENCE_MESSAGE = (
    "The available sources do not contain sufficient information to "
    "create a research brief on this topic."
)


class ResearchSkill:
    """Satisfies the `skills.base.Skill` protocol structurally (no inheritance
    required — see base.py docstring)."""

    name: ClassVar[str] = "research"

    def __init__(
        self,
        retrieval_service: RetrievalService,
        model_gateway: ModelGateway,
        synthesizer: ResearchSynthesizer,
        citation_builder: CitationBuilder,
    ) -> None:
        self._retrieval_service = retrieval_service
        self._model_gateway = model_gateway
        self._synthesizer = synthesizer
        self._citation_builder = citation_builder

    async def handle(self, context: SkillContext) -> SkillResult:
        topic = context.message

        # 1. Generate multiple retrieval queries from the user's question.
        subqueries = await self._generate_subqueries(topic)
        queries = _dedupe_queries([topic, *subqueries])

        # 2. Retrieve across episodes, 3. deduplicate by chunk id.
        all_chunks = await self._retrieve_and_dedupe(queries)

        if not all_chunks:
            # Same explicit "no grounding" pattern as qa/service.py — say
            # so rather than fabricate a brief (PRD §6.3/§6.4 acceptance
            # criteria apply equally here). This only catches a fully empty
            # retrieval result (e.g. an empty corpus) — vector similarity
            # search always returns *some* nearest neighbors when the
            # corpus is non-empty, even if none of them are actually on
            # topic, so a populated-but-irrelevant `all_chunks` still
            # reaches the model below; that case is caught after
            # generation instead (see `INSUFFICIENT_EVIDENCE_MARKER` check).
            return SkillResult(skill="research", content_markdown=_INSUFFICIENT_EVIDENCE_MESSAGE, citations=[])

        # 4. Build a synthesis prompt (excerpts grouped by episode).
        chunks_by_episode = self._group_by_episode(all_chunks)
        prompt = build_research_prompt(topic=topic, retrieved_chunks_by_episode=chunks_by_episode)

        # 5. Generate the structured research brief.
        raw_completion = await self._model_gateway.generate(prompt=prompt, system=RESEARCH_SYSTEM_PROMPT)

        # The model itself is the only thing that can judge whether the
        # retrieved excerpts substantively address the *requested* topic
        # (retrieval has no relevance/similarity threshold of its own — see
        # above) — `RESEARCH_SYSTEM_PROMPT`/`build_research_prompt` instruct
        # it to emit this exact marker instead of a brief when they don't.
        # Enforced here, not left to the model's discretion alone: this is
        # the one point where an off-topic completion (e.g. a "Career
        # Development" brief synthesized from personal-branding-adjacent
        # excerpts) gets caught before it's structured, cited, and
        # persisted as a real Artifact.
        if INSUFFICIENT_EVIDENCE_MARKER in raw_completion:
            return SkillResult(skill="research", content_markdown=_INSUFFICIENT_EVIDENCE_MESSAGE, citations=[])

        draft = self._synthesizer.structure(topic=topic, raw_completion=raw_completion, retrieved_chunks=all_chunks)

        # Citations are built from the retrieved chunks themselves — never
        # parsed out of the model's free text (DOMAIN_MODEL.md §4.8
        # invariant) — same rule QA follows, reusing the same builder.
        citations = self._citation_builder.build(retrieved_chunks=all_chunks)

        # UX redesign (Option B): the chat message gets title + executive
        # summary + a pointer to the Research tab, never the full brief —
        # the full multi-section brief (with citations) is reserved for
        # the persisted Artifact only, via `artifact_content_markdown`
        # (skills/schemas.py). Without this split, the entire brief was
        # duplicated verbatim into the chat conversation, making the
        # Research tab feel redundant since users had already read
        # everything in chat.
        full_brief_markdown = self._render_brief_markdown(draft=draft, citations=citations)
        chat_summary_markdown = self._render_chat_summary_markdown(draft=draft)

        return SkillResult(
            skill="research",
            content_markdown=chat_summary_markdown,
            citations=citations,
            artifact_type="research_brief",
            artifact_content_markdown=full_brief_markdown,
            research_topic=draft.topic,
            research_summary=draft.summary,
        )

    async def _generate_subqueries(self, topic: str) -> list[str]:
        prompt = build_query_expansion_prompt(question=topic, num_queries=_NUM_SUBQUERIES)
        raw_completion = await self._model_gateway.generate(prompt=prompt, system=QUERY_EXPANSION_SYSTEM_PROMPT)
        return parse_subqueries(raw_completion, max_queries=_NUM_SUBQUERIES)

    async def _retrieve_and_dedupe(self, queries: list[str]) -> list[TranscriptChunkRead]:
        all_chunks: list[TranscriptChunkRead] = []
        seen_ids: set[uuid.UUID] = set()
        for query in queries:
            results = await self._retrieval_service.search(query_text=query, top_k=_TOP_K_PER_QUERY)
            for chunk in results:
                if chunk.id not in seen_ids:
                    seen_ids.add(chunk.id)
                    all_chunks.append(chunk)
        return all_chunks[:_MAX_TOTAL_CHUNKS]

    @staticmethod
    def _group_by_episode(chunks: list[TranscriptChunkRead]) -> dict[str, list[str]]:
        grouped: dict[str, list[str]] = {}
        for chunk in chunks:
            label = chunk.episode.title if chunk.episode else "Unknown episode"
            grouped.setdefault(label, []).append(chunk.content)
        return grouped

    @staticmethod
    def _render_brief_markdown(*, draft: ResearchBriefDraft, citations: list[CitationRef]) -> str:
        """Render the final artifact Markdown: the model-generated sections
        plus a programmatically-appended Citations section built from the
        same structured `citations` list used for the DB `Citation` rows
        — never from model prose, so the document can't drift from what
        was actually retrieved.
        """

        parts = [f"# {draft.topic}"]
        for section in draft.sections:
            parts.append(f"## {section.heading}\n\n{section.body_markdown}")
        if citations:
            citation_lines = "\n".join(f"{index}. {c.display_label}" for index, c in enumerate(citations, start=1))
            parts.append(f"## Citations\n\n{citation_lines}")
        return "\n\n".join(parts)

    @staticmethod
    def _render_chat_summary_markdown(*, draft: ResearchBriefDraft) -> str:
        """Chat-facing content only (UX redesign, Option B): title +
        executive summary, plus a call-to-action pointing at the Research
        tab — deliberately *not* the Key Insights/Supporting Evidence/
        Recommended Actions sections or the citations list, which live
        exclusively in the Artifact (`_render_brief_markdown`, used for
        `artifact_content_markdown` instead of this)."""

        return (
            f"# {draft.topic}\n\n"
            f"{draft.summary}\n\n"
            f"_Full brief with sources and detailed findings available in the Research tab._"
        )


def _dedupe_queries(queries: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for query in queries:
        key = query.strip().lower()
        if key and key not in seen:
            seen.add(key)
            result.append(query.strip())
    return result
