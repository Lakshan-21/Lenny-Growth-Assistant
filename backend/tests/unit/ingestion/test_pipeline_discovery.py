"""Unit tests for `discover_transcript_files` (ingestion/pipeline.py):
recursive `transcript.md` discovery under `transcripts/episodes`, combined
with the original flat `*.json` discovery, plus the exclusion list.
"""

import pytest

from app.domains.knowledge.exceptions import TranscriptLoadError
from app.domains.knowledge.ingestion.pipeline import _EXCLUDED_EPISODE_DIR_NAMES, discover_transcript_files
from tests.unit.ingestion.conftest import EPISODES_DIR, TRANSCRIPTS_DIR


def test_discover_raises_for_missing_directory(tmp_path):
    with pytest.raises(TranscriptLoadError):
        discover_transcript_files(str(tmp_path / "does-not-exist"))


def test_discover_combines_flat_json_and_recursive_markdown_and_applies_exclusions(tmp_path):
    flat_json = tmp_path / "flat-episode.json"
    flat_json.write_text("{}", encoding="utf-8")

    included = tmp_path / "episodes" / "some-guest" / "transcript.md"
    included.parent.mkdir(parents=True)
    included.write_text("---\ntitle: x\n---\nbody", encoding="utf-8")

    excluded = tmp_path / "episodes" / "andy-raskin_" / "transcript.md"
    excluded.parent.mkdir(parents=True)
    excluded.write_text("---\ntitle: dup\n---\nbody", encoding="utf-8")

    found = discover_transcript_files(str(tmp_path))

    assert found == sorted([flat_json, included])
    assert excluded not in found


def test_real_corpus_excludes_known_bad_episodes_but_keeps_lookalikes():
    found_names = {path.parent.name for path in discover_transcript_files(str(EPISODES_DIR))}

    assert "andy-raskin_" not in found_names  # confirmed content duplicate of andy-raskin
    assert "teaser_2021" not in found_names  # promotional clip, not a guest interview

    # Neither exclusion should over-match by folder-name similarity: the
    # kept duplicate, and a *different* real episode that happens to share
    # a guest name with a trailing underscore, must both still be found.
    assert "andy-raskin" in found_names
    assert "casey-winters_" in found_names


def test_real_corpus_discovery_count_matches_known_exclusions():
    all_transcript_md = list(EPISODES_DIR.rglob("transcript.md"))
    found = discover_transcript_files(str(EPISODES_DIR))

    assert len(found) == len(all_transcript_md) - len(_EXCLUDED_EPISODE_DIR_NAMES)


def test_discover_over_transcripts_root_finds_json_and_markdown_together():
    """`discover_transcript_files` must handle a directory containing both
    the flat JSON fixture and the nested real markdown corpus in one call
    -- this is what a bulk `ingest_directory(TRANSCRIPTS_DIR)` call would
    see."""

    found = discover_transcript_files(str(TRANSCRIPTS_DIR))

    assert (TRANSCRIPTS_DIR / "episode-142.json") in found
    assert any(path.parent.name == "ada-chen-rekhi" for path in found)
    assert not any(path.parent.name in _EXCLUDED_EPISODE_DIR_NAMES for path in found)
