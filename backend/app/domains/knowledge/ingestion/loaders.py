"""Reads raw transcript/episode metadata from source files.

Two source formats are supported, dispatched by file extension:

1. **JSON** (`*.json`) — one file per episode, ASR/Whisper-style,
   time-aligned segments:

    {
      "title": "Episode title",
      "guest_name": "Guest Name",          // optional
      "published_at": "2024-01-15",        // optional, ISO date
      "source_url": "https://...",         // optional
      "segments": [
        {"text": "...", "start": 0.0, "end": 12.5},
        {"text": "...", "start": 12.5, "end": 30.2}
      ]
    }

   `segments` must be time-aligned — DATABASE_SCHEMA.md §8 risk #11
   explicitly assumes this; a source lacking timing data should fail
   ingestion loudly rather than fabricate timestamps, which is exactly
   what happens here (missing/invalid fields raise `TranscriptLoadError`,
   nothing defaults silently).

2. **Markdown** (`*.md`) — the real Lenny's Podcast transcript archive
   format: YAML frontmatter followed by timestamped speaker turns. See
   `_load_markdown_episode` below for the supported turn-marker
   conventions and known unsupported variants.

Both formats parse into the same `RawEpisode`/`RawTranscriptSegment`
shape, so `chunking.py`/`pipeline.py` are format-agnostic.
"""

import json
import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path

import yaml

from app.domains.knowledge.exceptions import TranscriptLoadError


@dataclass(frozen=True, slots=True)
class RawTranscriptSegment:
    """A single time-aligned segment as produced by the transcript source
    (e.g. ASR output, or a parsed markdown speaker turn) — the input to
    `chunking.py`.

    DATABASE_SCHEMA.md §8 risk #11: this shape assumes the source always
    carries timing data; if a future source lacks it, ingestion for that
    source should fail loudly rather than silently defaulting timestamps.
    """

    text: str
    start_timestamp_seconds: int
    end_timestamp_seconds: int


@dataclass(frozen=True, slots=True)
class RawEpisode:
    title: str
    guest_name: str | None
    published_at: date | None
    source_url: str | None
    segments: list[RawTranscriptSegment]


def load_episode(source_path: str) -> RawEpisode:
    """Parse a transcript source file (`.json` or `.md`) into a `RawEpisode`.

    Raises `TranscriptLoadError` on any missing file, invalid content, or
    missing/malformed required fields — ingestion should fail clearly
    rather than silently skip or fabricate data for a bad source file.
    """

    path = Path(source_path)
    if not path.is_file():
        raise TranscriptLoadError(f"Transcript file not found: {source_path}")

    try:
        raw_text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise TranscriptLoadError(f"Could not read {source_path}: {exc}") from exc

    if path.suffix == ".md":
        return _load_markdown_episode(source_path, raw_text)
    return _load_json_episode(source_path, raw_text)


def _load_json_episode(source_path: str, raw_text: str) -> RawEpisode:
    try:
        data = json.loads(raw_text)
    except json.JSONDecodeError as exc:
        raise TranscriptLoadError(f"{source_path} is not valid JSON: {exc}") from exc

    try:
        title = data["title"]
        raw_segments = data["segments"]
    except KeyError as exc:
        raise TranscriptLoadError(f"{source_path} is missing required field {exc}") from exc

    if not isinstance(title, str) or not title.strip():
        raise TranscriptLoadError(f"{source_path}: 'title' must be a non-empty string")
    if not isinstance(raw_segments, list) or not raw_segments:
        raise TranscriptLoadError(f"{source_path}: 'segments' must be a non-empty array")

    published_at_raw = data.get("published_at")
    published_at: date | None = None
    if published_at_raw:
        try:
            published_at = date.fromisoformat(published_at_raw)
        except (TypeError, ValueError) as exc:
            raise TranscriptLoadError(
                f"{source_path}: 'published_at' must be an ISO date (YYYY-MM-DD), got {published_at_raw!r}"
            ) from exc

    segments: list[RawTranscriptSegment] = []
    for index, raw_segment in enumerate(raw_segments):
        try:
            text = raw_segment["text"]
            start = raw_segment["start"]
            end = raw_segment["end"]
        except (KeyError, TypeError) as exc:
            raise TranscriptLoadError(
                f"{source_path}: segment[{index}] is missing a required field {exc}"
            ) from exc
        if not isinstance(text, str) or not text.strip():
            continue  # skip empty segments (e.g. silence markers); not an error
        try:
            start_seconds = int(start)
            end_seconds = int(end)
        except (TypeError, ValueError) as exc:
            raise TranscriptLoadError(
                f"{source_path}: segment[{index}] has non-numeric start/end ({start!r}, {end!r})"
            ) from exc
        if end_seconds <= start_seconds:
            raise TranscriptLoadError(
                f"{source_path}: segment[{index}] has end <= start ({start_seconds} .. {end_seconds})"
            )
        segments.append(
            RawTranscriptSegment(text=text, start_timestamp_seconds=start_seconds, end_timestamp_seconds=end_seconds)
        )

    if not segments:
        raise TranscriptLoadError(f"{source_path}: no non-empty segments found")

    return RawEpisode(
        title=title,
        guest_name=data.get("guest_name"),
        published_at=published_at,
        source_url=data.get("source_url"),
        segments=segments,
    )


# Matches a transcript-turn marker line: an optional speaker name, then a
# parenthesized timestamp, then a colon, with nothing else on the line.
# Two timestamp conventions exist in the real corpus and are both
# supported here: `(HH:MM:SS):` (most episodes) and the shorter `(MM:SS):`
# used by episodes under an hour (confirmed against the corpus: MM never
# exceeds 59 in files using this form, i.e. they never actually cross the
# one-hour mark). A bare `(HH:MM:SS):` line with no speaker name is a
# continuation turn by the same speaker as the preceding marker.
#
# Two other single-episode formats exist in the corpus (`Speaker:` with no
# timestamp at all, and inline `[HH:MM:SS] Speaker: text`) and are
# deliberately NOT matched here -- a file using only those formats has zero
# matches below and fails loudly (see `_load_markdown_episode`), consistent
# with "fail loudly rather than fabricate timestamps" rather than silently
# mis-parsing or dropping content.
_TURN_MARKER_RE = re.compile(
    r"^(?P<prefix>.*?)\((?P<timestamp>\d{1,2}(?::\d{2}){1,2})\):[ \t]*$",
    re.MULTILINE,
)


def _parse_marker_timestamp(raw: str) -> int:
    """Convert a marker's `MM:SS` or `HH:MM:SS` capture to whole seconds."""

    parts = [int(p) for p in raw.split(":")]
    if len(parts) == 2:
        minutes, seconds = parts
        return minutes * 60 + seconds
    hours, minutes, seconds = parts
    return hours * 3600 + minutes * 60 + seconds


def _load_markdown_episode(source_path: str, raw_text: str) -> RawEpisode:
    """Parse a `transcript.md` file: YAML frontmatter + timestamped speaker
    turns (the real Lenny's Podcast transcript archive format).

    Frontmatter field mapping (archive key -> `RawEpisode` field): `title`
    is unchanged; `guest` -> `guest_name`; `youtube_url` -> `source_url`;
    `publish_date` -> `published_at`. `duration_seconds`, if present, is
    used only as the end-timestamp anchor for the episode's final turn
    (see below) -- it is not part of `RawEpisode`.
    """

    # Every real transcript.md in the corpus contains the substring "---"
    # exactly twice (the two frontmatter delimiters), confirmed corpus-wide
    # before relying on this -- so a plain maxsplit=2 is safe and doesn't
    # need to special-case "---" appearing inside the transcript body.
    parts = raw_text.split("---", 2)
    if len(parts) < 3 or parts[0].strip():
        raise TranscriptLoadError(
            f"{source_path}: expected YAML frontmatter delimited by '---' at the start of the file"
        )
    frontmatter_text, body = parts[1], parts[2]

    try:
        frontmatter = yaml.safe_load(frontmatter_text)
    except yaml.YAMLError as exc:
        raise TranscriptLoadError(f"{source_path}: invalid YAML frontmatter: {exc}") from exc

    if not isinstance(frontmatter, dict):
        raise TranscriptLoadError(f"{source_path}: frontmatter did not parse to a mapping")

    title = frontmatter.get("title")
    if not isinstance(title, str) or not title.strip():
        raise TranscriptLoadError(f"{source_path}: frontmatter is missing a non-empty 'title'")

    guest_name = frontmatter.get("guest")
    if guest_name is not None and not isinstance(guest_name, str):
        raise TranscriptLoadError(
            f"{source_path}: frontmatter 'guest' must be a string if present, got {guest_name!r}"
        )

    source_url = frontmatter.get("youtube_url")
    if source_url is not None and not isinstance(source_url, str):
        raise TranscriptLoadError(
            f"{source_path}: frontmatter 'youtube_url' must be a string if present, got {source_url!r}"
        )

    # PyYAML parses an unquoted `YYYY-MM-DD` scalar straight into a
    # `datetime.date`, not a string -- both shapes are handled.
    published_at: date | None = None
    publish_date_raw = frontmatter.get("publish_date")
    if isinstance(publish_date_raw, date):
        published_at = publish_date_raw
    elif isinstance(publish_date_raw, str) and publish_date_raw.strip():
        try:
            published_at = date.fromisoformat(publish_date_raw)
        except ValueError as exc:
            raise TranscriptLoadError(
                f"{source_path}: 'publish_date' must be an ISO date (YYYY-MM-DD), got {publish_date_raw!r}"
            ) from exc
    elif publish_date_raw is not None:
        raise TranscriptLoadError(
            f"{source_path}: 'publish_date' must be a date or ISO date string, got {publish_date_raw!r}"
        )

    duration_seconds: int | None = None
    duration_seconds_raw = frontmatter.get("duration_seconds")
    if isinstance(duration_seconds_raw, (int, float)):
        duration_seconds = int(duration_seconds_raw)

    matches = list(_TURN_MARKER_RE.finditer(body))
    if not matches:
        raise TranscriptLoadError(
            f"{source_path}: no speaker-timestamp turn markers found in the transcript body "
            "(unsupported transcript format for this file -- see _TURN_MARKER_RE docstring)"
        )

    segments: list[RawTranscriptSegment] = []
    for index, match in enumerate(matches):
        start_seconds = _parse_marker_timestamp(match.group("timestamp"))
        text_start = match.end() + 1  # skip the newline ending the marker line
        text_end = matches[index + 1].start() if index + 1 < len(matches) else len(body)
        text = body[text_start:text_end].strip()
        if not text:
            continue  # e.g. a marker immediately followed by another marker

        if index + 1 < len(matches):
            # Inferred end = next turn's start. Markdown turns (unlike the
            # JSON format) carry no explicit end time; guard against two
            # markers landing on the same second (end must be > start per
            # DATABASE_SCHEMA.md's check constraint).
            next_start_seconds = _parse_marker_timestamp(matches[index + 1].group("timestamp"))
            end_seconds = next_start_seconds if next_start_seconds > start_seconds else start_seconds + 1
        elif duration_seconds is not None and duration_seconds > start_seconds:
            # Last turn: anchor to the episode's total duration if known.
            end_seconds = duration_seconds
        else:
            # No duration to anchor to (or it's inconsistent with the
            # transcript) -- a rough one-second fallback rather than
            # fabricating a plausible-looking duration.
            end_seconds = start_seconds + 1

        segments.append(
            RawTranscriptSegment(text=text, start_timestamp_seconds=start_seconds, end_timestamp_seconds=end_seconds)
        )

    if not segments:
        raise TranscriptLoadError(f"{source_path}: no non-empty transcript segments found")

    return RawEpisode(
        title=title,
        guest_name=guest_name,
        published_at=published_at,
        source_url=source_url,
        segments=segments,
    )
