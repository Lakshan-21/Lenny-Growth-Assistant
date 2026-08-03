"""Unit tests for `KnowledgeRepository.similarity_search`'s cosine-distance
threshold (retrieval pipeline review, recommendation #1).

No live Postgres/pgvector connection is available in this test suite (see
`tests/conftest.py`'s documented constraint — Docker is ruled out for MVP,
so there's no way to stand up a real vector index for an automated suite).
`cosine_distance` is a real SQL expression evaluated by Postgres itself, so
"irrelevant chunks actually get scored and rejected" can't be exercised
end-to-end here without one.

What *is* verifiable without a live DB, and what these tests check:
  1. The statement `similarity_search` builds actually contains a WHERE
     predicate enforcing `_MAX_COSINE_DISTANCE` — proves the filter is
     really wired into the real query the method sends, not just described
     in a comment. Compiled with `literal_binds=True` so no live connection
     is needed to inspect it.
  2. The method's own row-unpacking is correct given a scripted result set
     standing in for "Postgres already applied the WHERE clause" — i.e.
     everything on the Python side of the SQL boundary: passing rows come
     back as `list[TranscriptChunk]`, and zero passing rows come back as
     `[]` (requirement 4: all-filtered-out -> empty result, not an error).

The real distance numbers behind the chosen threshold were captured by
actually running queries against the live corpus with the retrieval
pipeline's temporary logging (see the review) — that manual verification,
not an automated test, is what confirmed genuinely irrelevant queries
score above 0.48 in practice.
"""

import asyncio
import uuid

from app.domains.knowledge.models import TranscriptChunk
from app.domains.knowledge.repository import KnowledgeRepository, _MAX_COSINE_DISTANCE


class _ScriptedResult:
    def __init__(self, rows):
        self._rows = rows

    def all(self):
        return self._rows


class _CapturingSession:
    """Stands in for a real `AsyncSession`/Postgres connection: records the
    statement passed to `execute()` (so the test can inspect the real query
    `similarity_search` builds) and returns a scripted result in its place.
    """

    def __init__(self, rows):
        self.captured_stmt = None
        self._rows = rows

    async def execute(self, stmt):
        self.captured_stmt = stmt
        return _ScriptedResult(self._rows)


def _make_chunk() -> TranscriptChunk:
    chunk = TranscriptChunk(
        id=uuid.uuid4(),
        episode_id=uuid.uuid4(),
        content="a transcript chunk",
        embedding=[0.1] * 1024,
        start_offset=0,
        end_offset=19,
        start_timestamp_seconds=0,
        end_timestamp_seconds=10,
    )
    chunk.episode = None
    return chunk


def test_query_where_clause_enforces_the_chosen_threshold():
    """Proves the filter is really wired into the query `similarity_search`
    sends — not just documented — by compiling the actual statement with
    literal binds and checking for both the threshold value and pgvector's
    cosine-distance operator."""

    session = _CapturingSession(rows=[])
    repo = KnowledgeRepository(session)

    asyncio.run(repo.similarity_search(query_embedding=[0.1] * 1024, top_k=6))

    assert session.captured_stmt is not None
    compiled = str(session.captured_stmt.compile(compile_kwargs={"literal_binds": True}))
    assert "<=>" in compiled, "expected pgvector's cosine-distance operator in the compiled query"
    assert f"<= {_MAX_COSINE_DISTANCE}" in compiled, "expected the WHERE clause to compare distance against the threshold"


def test_relevant_results_within_threshold_are_returned():
    """Rows Postgres's WHERE clause would already have kept (distance <=
    threshold, e.g. the ~0.41 seen for a genuinely on-topic query during
    the pipeline investigation) must come back as `TranscriptChunk`s, in
    the same order, with the distance column dropped."""

    chunk_a, chunk_b = _make_chunk(), _make_chunk()
    session = _CapturingSession(rows=[(chunk_a, 0.41), (chunk_b, 0.4776)])  # both <= 0.48
    repo = KnowledgeRepository(session)

    result = asyncio.run(repo.similarity_search(query_embedding=[0.1] * 1024, top_k=6))

    assert result == [chunk_a, chunk_b]


def test_irrelevant_results_beyond_threshold_never_reach_python():
    """Simulates what the real query does for an off-topic request (e.g.
    "personal branding strategies" against a corpus with none — observed
    distances ~0.49-0.54): Postgres's WHERE clause excludes them before
    `LIMIT`/return, so the scripted result set the repository receives
    simply doesn't contain them — the method must not need any extra
    Python-side filtering to keep them out."""

    chunk_relevant = _make_chunk()
    session = _CapturingSession(rows=[(chunk_relevant, 0.41)])  # the off-topic candidates never made it past WHERE
    repo = KnowledgeRepository(session)

    result = asyncio.run(repo.similarity_search(query_embedding=[0.1] * 1024, top_k=6))

    assert result == [chunk_relevant]


def test_empty_result_when_everything_is_filtered_out():
    """Requirement 4: if every candidate is farther than the threshold
    (fully off-topic query, nothing in the corpus qualifies), the method
    returns an empty list rather than raising — QA's and Research's
    existing `if not ...chunks:` no-grounding paths already handle this."""

    session = _CapturingSession(rows=[])
    repo = KnowledgeRepository(session)

    result = asyncio.run(repo.similarity_search(query_embedding=[0.1] * 1024, top_k=6))

    assert result == []


def test_episode_filter_is_still_applied_alongside_the_threshold():
    """The pre-existing `episode_ids` filter must still combine (AND) with
    the new threshold clause, not replace it."""

    session = _CapturingSession(rows=[])
    repo = KnowledgeRepository(session)
    episode_id = uuid.uuid4()

    asyncio.run(repo.similarity_search(query_embedding=[0.1] * 1024, top_k=6, episode_ids=[episode_id]))

    compiled = str(session.captured_stmt.compile(compile_kwargs={"literal_binds": True}))
    assert f"<= {_MAX_COSINE_DISTANCE}" in compiled
    assert episode_id.hex in compiled  # UUID columns render as bare hex in a literal-bound IN (...)
