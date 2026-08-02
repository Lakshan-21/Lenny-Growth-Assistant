"""Full-corpus smoke test: every real `transcript.md` the pipeline would
actually discover (i.e. post-exclusion-list) must parse without error and
produce sane segments, except the two known-unsupported turn formats
found during adapter development (tracked explicitly, not silently
skipped-and-forgotten).
"""

from app.domains.knowledge.ingestion.loaders import load_episode
from app.domains.knowledge.ingestion.pipeline import discover_transcript_files
from tests.unit.ingestion.conftest import EPISODES_DIR

# Real, currently-unsupported turn-marker formats (see test_loaders.py for
# per-file detail): "Speaker:" with no timestamp at all, and inline
# "[HH:MM:SS] Speaker: text". Follow-up work, not a bug in this adapter.
_KNOWN_UNSUPPORTED_FORMATS = frozenset({"adriel-frederick", "ryan-hoover"})


def test_entire_discoverable_corpus_parses_except_known_format_gaps():
    files = discover_transcript_files(str(EPISODES_DIR))
    assert len(files) > 250  # sanity: we're actually scanning the real corpus, not an empty dir

    failures: list[tuple[str, Exception]] = []
    parsed = 0

    for path in files:
        if path.parent.name in _KNOWN_UNSUPPORTED_FORMATS:
            continue
        try:
            episode = load_episode(str(path))
        except Exception as exc:  # noqa: BLE001 -- collect every failure, don't stop at the first
            failures.append((str(path), exc))
            continue

        parsed += 1
        assert episode.title.strip()
        assert episode.segments, f"{path}: parsed with zero segments"
        for segment in episode.segments:
            assert segment.text.strip(), f"{path}: blank segment text"
            assert segment.end_timestamp_seconds > segment.start_timestamp_seconds, f"{path}: non-positive duration"

    assert not failures, "unexpected parse failures:\n" + "\n".join(f"{p}: {e}" for p, e in failures)
    assert parsed == len(files) - len(_KNOWN_UNSUPPORTED_FORMATS)
