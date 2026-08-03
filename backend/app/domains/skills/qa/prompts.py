"""Prompt templates for grounded QA generation."""

from app.domains.skills.schemas import INSUFFICIENT_EVIDENCE_MARKER

QA_SYSTEM_PROMPT = (
    "You are the Lenny Growth Workspace assistant. You answer questions "
    "strictly using the numbered podcast excerpts provided in the user "
    "message — never from general/outside knowledge, prior turns, or "
    "training data.\n\n"
    "Before answering, check whether the excerpts substantively address "
    "the question as asked. Being topically nearby is not the same as "
    "being on-topic: excerpts about an adjacent or broader theme do not "
    "answer a narrower or different question just because retrieval "
    "returned them. If the excerpts are insufficient, respond with "
    "exactly this single line and nothing else — no partial answer, no "
    f"hedging, no guessing: {INSUFFICIENT_EVIDENCE_MARKER}\n\n"
    "If the excerpts are sufficient, cite the excerpt number(s) you rely "
    "on inline, like [1] or [2][3], and answer strictly from them — "
    "never stretch a partial or adjacent excerpt into a confident answer "
    "it doesn't actually support."
)


def build_qa_prompt(*, question: str, retrieved_chunks: list[str]) -> str:
    """Assemble the user-turn prompt: numbered excerpts followed by the
    question. System instructions (`QA_SYSTEM_PROMPT`) are passed
    separately to the model gateway, not concatenated in here.

    Excerpt numbering must match the order `retrieved_chunks` is passed
    in — `citation_builder.py` builds citations from the same
    `TranscriptChunkRead` list in the same order, so the model's [N]
    references line up with the citations returned alongside the answer.

    Restates the insufficient-evidence escape hatch immediately next to
    the excerpts and question themselves (not just in the system prompt)
    — the same proximity reasoning `research/prompts.py::build_research_prompt`
    uses: a constraint repeated right next to the content it governs is
    less likely to be drifted off.
    """

    excerpts = "\n\n".join(
        f"[{index + 1}] {chunk}" for index, chunk in enumerate(retrieved_chunks)
    )
    return (
        f"Podcast excerpts:\n\n{excerpts}\n\n"
        f"Question: {question}\n\n"
        f"First, confirm the excerpts above substantively answer this "
        f"exact question — not merely a related or broader theme. If "
        f"they don't, respond with exactly `{INSUFFICIENT_EVIDENCE_MARKER}` "
        f"and nothing else."
    )
