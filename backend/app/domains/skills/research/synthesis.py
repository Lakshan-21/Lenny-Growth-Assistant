"""Structuring logic for the research brief: summary, per-guest
perspectives, agreement/disagreement (PRD §6.4)."""

from app.domains.knowledge.schemas import TranscriptChunkRead
from app.domains.skills.research.schemas import ResearchBriefDraft, ResearchBriefSection

_EXECUTIVE_SUMMARY_HEADING = "executive summary"
_FALLBACK_HEADING = "Findings"
_FALLBACK_SUMMARY = "No summary available."


class ResearchSynthesizer:
    """Turns a raw model completion + the chunks that grounded it into a
    structured `ResearchBriefDraft`.

    Kept as a separate class from `ResearchSkill` (rather than inline logic)
    so the structuring rules can be tested independently of retrieval/model
    concerns — mirrors why `citation_builder.py` is separate from
    `qa/service.py`.
    """

    def structure(
        self,
        *,
        topic: str,
        raw_completion: str,
        retrieved_chunks: list[TranscriptChunkRead],
    ) -> ResearchBriefDraft:
        """Parse `raw_completion` into sections by its `## ` Markdown
        headings (the model is prompted for exactly four — Executive
        Summary, Key Insights, Supporting Evidence, Recommended Actions —
        `research/prompts.py::RESEARCH_SYSTEM_PROMPT`). Falls back to a
        single catch-all section if the model didn't use headings at all,
        rather than losing the content.

        `retrieved_chunks` isn't used to alter the parsed structure (multi-
        episode coverage is a property of retrieval/dedup, already handled
        upstream in `ResearchSkill._retrieve_and_dedupe` — not something
        this parsing step can create after the fact); kept in the
        signature since it's part of this method's documented contract
        and may inform future validation (e.g. warning if a brief cites
        only one episode despite broader coverage being available).
        """

        sections = _parse_sections(raw_completion)
        summary = _extract_summary(sections)
        return ResearchBriefDraft(topic=topic, summary=summary, sections=sections)


def _parse_sections(raw_completion: str) -> list[ResearchBriefSection]:
    sections: list[ResearchBriefSection] = []
    current_heading: str | None = None
    current_body_lines: list[str] = []

    def flush() -> None:
        if current_heading is None:
            return
        body = "\n".join(current_body_lines).strip()
        if body:
            sections.append(ResearchBriefSection(heading=current_heading, body_markdown=body))

    for line in raw_completion.splitlines():
        if line.strip().startswith("## "):
            flush()
            current_heading = line.strip().removeprefix("##").strip()
            current_body_lines = []
        else:
            current_body_lines.append(line)
    flush()

    if not sections:
        fallback_body = raw_completion.strip()
        if fallback_body:
            sections.append(ResearchBriefSection(heading=_FALLBACK_HEADING, body_markdown=fallback_body))

    return sections


def _extract_summary(sections: list[ResearchBriefSection]) -> str:
    for section in sections:
        if section.heading.strip().lower() == _EXECUTIVE_SUMMARY_HEADING:
            return section.body_markdown
    return sections[0].body_markdown if sections else _FALLBACK_SUMMARY
