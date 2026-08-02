"""Shared constants/fixtures for ingestion tests that exercise the *real*
Lenny's Podcast transcript corpus rather than synthetic fixtures.

The corpus lives at `../transcripts` relative to `backend/` (a sibling
directory, not part of this Python package) -- see repo layout in
`docs/REPOSITORY_STRUCTURE.md`. Tests under this directory are skipped
entirely if that corpus isn't present (e.g. a checkout that only has
`backend/`), rather than failing on a missing-path error.
"""

from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[4]
TRANSCRIPTS_DIR = REPO_ROOT / "transcripts"
EPISODES_DIR = TRANSCRIPTS_DIR / "episodes"


@pytest.fixture(autouse=True, scope="session")
def _require_real_corpus():
    if not EPISODES_DIR.is_dir():
        pytest.skip(f"real transcript corpus not found at {EPISODES_DIR}")
