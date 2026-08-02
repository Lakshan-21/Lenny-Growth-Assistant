"""Prompt templates for grounded QA generation."""

QA_SYSTEM_PROMPT = (
    "You are the Lenny Growth Workspace assistant. You answer questions "
    "strictly using the numbered podcast excerpts provided in the user "
    "message — never from general/outside knowledge. Cite the excerpt "
    "number(s) you rely on inline, like [1] or [2][3]. If the excerpts do "
    "not contain enough information to answer the question, say so "
    "directly instead of guessing or filling gaps from general knowledge."
)


def build_qa_prompt(*, question: str, retrieved_chunks: list[str]) -> str:
    """Assemble the user-turn prompt: numbered excerpts followed by the
    question. System instructions (`QA_SYSTEM_PROMPT`) are passed
    separately to the model gateway, not concatenated in here.

    Excerpt numbering must match the order `retrieved_chunks` is passed
    in — `citation_builder.py` builds citations from the same
    `TranscriptChunkRead` list in the same order, so the model's [N]
    references line up with the citations returned alongside the answer.
    """

    excerpts = "\n\n".join(
        f"[{index + 1}] {chunk}" for index, chunk in enumerate(retrieved_chunks)
    )
    return f"Podcast excerpts:\n\n{excerpts}\n\nQuestion: {question}"
