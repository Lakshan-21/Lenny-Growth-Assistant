"""X/Twitter thread segmentation logic (per-tweet splitting) (PRD §6.5)."""

from app.domains.skills.ship30.schemas import XThreadSegment

X_THREAD_MAX_CHARS_PER_SEGMENT = 280


def format_x_thread(*, raw_completion: str) -> list[XThreadSegment]:
    """Split `raw_completion` into `XThreadSegment`s, each respecting
    `X_THREAD_MAX_CHARS_PER_SEGMENT`.

    Primary split is on blank lines — the prompt (`ship30/prompts.py`)
    explicitly instructs the model to separate tweets with a blank line,
    so this is normally a clean 1:1 mapping. Any resulting paragraph that
    still exceeds the per-tweet limit (model didn't fully comply) is
    further word-wrapped as a safety net, never mid-word.
    """

    paragraphs = [p.strip() for p in raw_completion.split("\n\n") if p.strip()]
    if not paragraphs:
        paragraphs = [raw_completion.strip()] if raw_completion.strip() else []

    texts: list[str] = []
    for paragraph in paragraphs:
        texts.extend(_wrap_to_limit(paragraph, limit=X_THREAD_MAX_CHARS_PER_SEGMENT))

    return [XThreadSegment(index=index, text=text) for index, text in enumerate(texts, start=1)]


def render_x_thread_markdown(segments: list[XThreadSegment]) -> str:
    """Render a thread's segments into a single Markdown document for
    artifact storage (`Artifact.content_markdown` must be one string —
    ADR-4, ARCHITECTURE.md). The `X_THREAD_MAX_CHARS_PER_SEGMENT`
    constraint applies to `XThreadSegment.text` itself (the actual tweet
    content), not to this decorated, numbered representation.
    """

    total = len(segments)
    return "\n\n---\n\n".join(f"**{segment.index}/{total}**\n\n{segment.text}" for segment in segments)


def _wrap_to_limit(text: str, *, limit: int) -> list[str]:
    if len(text) <= limit:
        return [text]

    words = text.split()
    chunks: list[str] = []
    current: list[str] = []
    current_len = 0
    for word in words:
        added_len = len(word) + (1 if current else 0)
        if current and current_len + added_len > limit:
            chunks.append(" ".join(current))
            current = [word]
            current_len = len(word)
        else:
            current.append(word)
            current_len += added_len
    if current:
        chunks.append(" ".join(current))
    return chunks
