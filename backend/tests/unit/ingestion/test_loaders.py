"""Unit tests for `ingestion/loaders.py` against real corpus samples.

Covers: JSON ingestion still works unchanged; markdown frontmatter is
parsed and field-mapped correctly; both turn-marker timestamp
conventions found in the real corpus (`HH:MM:SS` and `MM:SS`) parse;
end-timestamps are inferred correctly, including the "frontmatter
duration_seconds describes a short promo clip, not this archived
full-length transcript" quirk found in several episodes; and the two
known-unsupported single-episode turn formats fail loudly rather than
silently mis-parsing.
"""

from datetime import date

import pytest

from app.domains.knowledge.exceptions import TranscriptLoadError
from app.domains.knowledge.ingestion.loaders import load_episode
from tests.unit.ingestion.conftest import EPISODES_DIR, TRANSCRIPTS_DIR


def test_json_loader_still_works():
    """Requirement 1: the original ASR-style JSON format must keep working
    unchanged after adding markdown support."""

    episode = load_episode(str(TRANSCRIPTS_DIR / "episode-142.json"))

    assert episode.title == "Episode 142: Activation and Onboarding"
    assert episode.guest_name == "Jane Doe"
    assert episode.published_at == date(2024, 3, 1)
    assert episode.source_url == "https://lennyspodcast.com/142"
    assert len(episode.segments) == 2
    assert episode.segments[0].start_timestamp_seconds == 754
    assert episode.segments[0].end_timestamp_seconds == 761
    assert episode.segments[1].end_timestamp_seconds == 768


def test_markdown_loader_parses_frontmatter_and_hhmmss_turns():
    path = EPISODES_DIR / "ada-chen-rekhi" / "transcript.md"
    episode = load_episode(str(path))

    assert episode.title == "Feeling stuck? Here's how to know when it's time to leave your job | Ada Chen Rekhi"
    assert episode.guest_name == "Ada Chen Rekhi"
    assert episode.published_at == date(2023, 4, 21)
    assert episode.source_url == "https://www.youtube.com/watch?v=l-T8sNRcWQk"

    assert len(episode.segments) > 100  # this is a ~78-minute interview

    first = episode.segments[0]
    assert first.start_timestamp_seconds == 0
    assert first.text.startswith("It's a terrible outcome")

    for earlier, later in zip(episode.segments, episode.segments[1:]):
        assert later.start_timestamp_seconds >= earlier.start_timestamp_seconds
        assert earlier.end_timestamp_seconds > earlier.start_timestamp_seconds


def test_markdown_loader_infers_end_from_next_turns_start():
    path = EPISODES_DIR / "ada-chen-rekhi" / "transcript.md"
    episode = load_episode(str(path))

    first, second = episode.segments[0], episode.segments[1]
    assert first.end_timestamp_seconds == second.start_timestamp_seconds


def test_markdown_loader_falls_back_when_duration_seconds_is_stale():
    """`ada-chen-rekhi`'s frontmatter says `duration_seconds: 230` (a 3:50
    promo clip -- see its `description`'s "Find the full episode here"
    line), but the archived transcript body is the full ~78-minute
    interview, whose last turn starts at 01:18:01 (4681s) -- well past the
    frontmatter's claimed duration. The loader must not trust a duration
    that's smaller than the final turn's own start time, and should fall
    back to a minimal +1s end instead of fabricating a nonsensical
    (end < start) or misleading timestamp.
    """

    path = EPISODES_DIR / "ada-chen-rekhi" / "transcript.md"
    episode = load_episode(str(path))

    last = episode.segments[-1]
    assert last.start_timestamp_seconds == 4681  # 01:18:01
    assert last.end_timestamp_seconds == 4682


def test_markdown_loader_supports_mmss_timestamps_without_hour_component():
    """`casey-winters` (and ~27 other short episodes) use `(MM:SS):`
    markers instead of `(HH:MM:SS):` -- confirm minutes aren't
    misinterpreted as hours."""

    path = EPISODES_DIR / "casey-winters" / "transcript.md"
    episode = load_episode(str(path))

    assert episode.segments[0].start_timestamp_seconds == 0
    assert episode.segments[1].start_timestamp_seconds == 12  # "(00:12):", not 12 minutes... i.e. not 720s

    last = episode.segments[-1]
    assert last.start_timestamp_seconds == 3290  # 54:50
    assert last.end_timestamp_seconds == 3291  # duration_seconds=99 <= start -> +1s fallback


@pytest.mark.parametrize(
    "guest_dir",
    [
        "adriel-frederick",  # turns are plain "Speaker:" lines, no timestamp at all
        "ryan-hoover",  # turns are inline "[HH:MM:SS] Speaker: text", not the supported marker-line format
    ],
)
def test_markdown_loader_fails_loudly_on_unsupported_turn_formats(guest_dir):
    """These are real, currently-unsupported formats in the corpus (found
    during adapter development, not synthetic edge cases) -- the loader
    must refuse to guess rather than silently produce zero/garbled
    segments."""

    path = EPISODES_DIR / guest_dir / "transcript.md"
    with pytest.raises(TranscriptLoadError, match="no speaker-timestamp turn markers"):
        load_episode(str(path))


def test_markdown_loader_fails_loudly_on_excluded_teaser():
    """`teaser_2021` is on the pipeline's exclusion list (not a real guest
    interview) *and* independently fails to parse (no `title` in its
    frontmatter) -- confirms it isn't silently ingestible even if the
    exclusion list were ever bypassed."""

    path = EPISODES_DIR / "teaser_2021" / "transcript.md"
    with pytest.raises(TranscriptLoadError, match="title"):
        load_episode(str(path))
