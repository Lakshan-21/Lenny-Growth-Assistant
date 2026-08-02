"""Transcript chunking strategy.

Greedy fixed-window accumulation: consecutive segments are grouped into a
chunk until the accumulated text reaches `_TARGET_CHUNK_CHARS`, then a new
chunk starts. Chosen over sentence/speaker-turn-aware chunking
(ARCHITECTURE.md §10 open question) for a simple, dependency-free first
implementation — segments (not raw characters) are always kept intact, so
a chunk boundary never splits mid-segment. ~1000 characters (~150-200
words, roughly 30-90s of spoken content) is a reasonable size for a single
retrievable "point" in a podcast conversation — large enough for context,
small enough to keep retrieval precise (DATABASE_SCHEMA.md §5: "keep k
modest... rely on the LLM's synthesis step rather than very large k").
"""

from dataclasses import dataclass

from app.domains.knowledge.ingestion.loaders import RawTranscriptSegment

_TARGET_CHUNK_CHARS = 1000


@dataclass(frozen=True, slots=True)
class TranscriptChunkDraft:
    """A chunk ready for embedding — carries both text offsets and
    timestamps, matching `knowledge.models.TranscriptChunk` exactly
    (DATABASE_SCHEMA.md CHANGE 2)."""

    content: str
    start_offset: int
    end_offset: int
    start_timestamp_seconds: int
    end_timestamp_seconds: int


def chunk_segments(segments: list[RawTranscriptSegment]) -> list[TranscriptChunkDraft]:
    """Group `segments` into `TranscriptChunkDraft`s.

    `start_offset`/`end_offset` index into the full transcript text as if
    every segment's (stripped) text were joined with single spaces, in
    order — consistent across chunks so offsets are meaningful relative to
    one another, even though nothing currently re-assembles the full text
    from them (they exist for text-level boundary bookkeeping per
    DATABASE_SCHEMA.md, not for display — display uses the timestamps).
    """

    chunks: list[TranscriptChunkDraft] = []
    buffer: list[RawTranscriptSegment] = []
    offset = 0

    def flush() -> None:
        nonlocal buffer, offset
        if not buffer:
            return
        content = " ".join(segment.text.strip() for segment in buffer)
        start_offset = offset
        end_offset = start_offset + len(content)
        chunks.append(
            TranscriptChunkDraft(
                content=content,
                start_offset=start_offset,
                end_offset=end_offset,
                start_timestamp_seconds=buffer[0].start_timestamp_seconds,
                end_timestamp_seconds=buffer[-1].end_timestamp_seconds,
            )
        )
        offset = end_offset + 1  # +1: the space that would join to the next chunk's text
        buffer = []

    for segment in segments:
        text = segment.text.strip()
        if not text:
            continue
        buffer.append(segment)
        buffered_chars = sum(len(s.text.strip()) for s in buffer) + (len(buffer) - 1)
        if buffered_chars >= _TARGET_CHUNK_CHARS:
            flush()

    flush()  # final, possibly-under-target chunk
    return chunks
