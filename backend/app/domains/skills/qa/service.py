"""Implements the QA `Skill`: retrieval call -> grounded generation ->
citation assembly (PRD §6.3)."""

from typing import ClassVar

from app.domains.knowledge.retrieval_service import RetrievalService
from app.domains.providers.gateway import ModelGateway
from app.domains.skills.qa.citation_builder import CitationBuilder
from app.domains.skills.qa.prompts import QA_SYSTEM_PROMPT, build_qa_prompt
from app.domains.skills.schemas import INSUFFICIENT_EVIDENCE_MARKER, SkillContext, SkillResult

_TOP_K = 6
_NO_GROUNDING_MESSAGE = (
    "I don't have enough information in the ingested Lenny's Podcast "
    "transcripts to answer that confidently. Try rephrasing, or ask about "
    "a topic covered in an episode that's been ingested."
)


class QASkill:
    """Satisfies the `skills.base.Skill` protocol structurally (no inheritance
    required — see base.py docstring)."""

    name: ClassVar[str] = "qa"

    def __init__(
        self,
        retrieval_service: RetrievalService,
        model_gateway: ModelGateway,
        citation_builder: CitationBuilder,
    ) -> None:
        self._retrieval_service = retrieval_service
        self._model_gateway = model_gateway
        self._citation_builder = citation_builder

    async def handle(self, context: SkillContext) -> SkillResult:
        retrieved_chunks = await self._retrieval_service.search(query_text=context.message, top_k=_TOP_K)

        if not retrieved_chunks:
            # Explicit "no grounding" outcome, not an error (PRD §6.3
            # acceptance criteria: say so rather than fabricate an answer).
            # No citations, since nothing was retrieved to cite. This only
            # catches a fully empty retrieval result -- the similarity
            # threshold in `KnowledgeRepository.similarity_search` (retrieval
            # pipeline review, recommendation #1) already filters out
            # clearly off-topic chunks, but a topically-*adjacent* retrieval
            # (passes the corpus-wide distance threshold, yet still doesn't
            # actually answer this specific question) can still reach here
            # non-empty; that case is caught after generation instead (see
            # `INSUFFICIENT_EVIDENCE_MARKER` check below).
            return SkillResult(skill="qa", content_markdown=_NO_GROUNDING_MESSAGE, citations=[])

        prompt = build_qa_prompt(
            question=context.message,
            retrieved_chunks=[chunk.content for chunk in retrieved_chunks],
        )
        answer = await self._model_gateway.generate(prompt=prompt, system=QA_SYSTEM_PROMPT)

        # Same enforcement Research uses (research/service.py): the model is
        # instructed (qa/prompts.py) to emit this exact marker instead of an
        # answer when the retrieved excerpts don't substantively address the
        # question -- checked here, not left to the model's discretion alone,
        # so a weakly-grounded retrieval can't still produce a confidently-
        # worded answer with citations attached. Checked *before* building
        # citations: an insufficient-evidence answer must never carry
        # citations implying stronger grounding than actually exists.
        if INSUFFICIENT_EVIDENCE_MARKER in answer:
            return SkillResult(skill="qa", content_markdown=_NO_GROUNDING_MESSAGE, citations=[])

        # Citations are built from the retrieved chunks themselves, never
        # parsed out of the model's free-text answer (DOMAIN_MODEL.md §4.8
        # invariant) — every retrieved chunk that was actually shown to the
        # model gets a citation, regardless of which [N] markers the model
        # chose to reference in its answer text.
        citations = self._citation_builder.build(retrieved_chunks=retrieved_chunks)

        return SkillResult(skill="qa", content_markdown=answer, citations=citations)
