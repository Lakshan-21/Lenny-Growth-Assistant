"""Command-line entrypoint to run the offline ingestion pipeline
(IMPLEMENTATION_PLAN.md Phase 2). Not part of the FastAPI app — invoked
directly, e.g.:

    python -m app.domains.knowledge.ingestion.cli
    python -m app.domains.knowledge.ingestion.cli ./transcripts
    python -m app.domains.knowledge.ingestion.cli ./transcripts/episode-142.json

With no argument, scans `settings.TRANSCRIPT_INGESTION_DIR`. A directory
argument scans that directory for `*.json` files; a file argument ingests
just that one file. See `ingestion/loaders.py` for the expected JSON shape.

Outside the request/response cycle there is no `Depends()` graph, so
dependencies are constructed manually here — still constructor-injected
into `IngestionPipeline`, just wired by hand instead of by FastAPI.

Like `migrations/env.py`, this entrypoint never imports `app.main` — so
none of the model registration that happens as a side effect of `main`'s
router chain (auth/sessions/skills routers transitively importing every
domain's `models.py`) happens here. `Citation` (knowledge/models.py) has a
string-based `relationship("Message", ...)` back to `sessions.models`,
which SQLAlchemy only resolves against classes already registered on
`Base`'s registry at mapper-configuration time — so `models_registry` must
be imported before any ORM operation runs, exactly as `migrations/env.py`
already does for the same reason.
"""

import argparse
import asyncio
import logging
from pathlib import Path

from app.config import get_settings
from app.database import models_registry  # noqa: F401 -- see module docstring
from app.database.session import AsyncSessionLocal
from app.domains.knowledge.embeddings.embedding_service import EmbeddingService
from app.domains.knowledge.ingestion.pipeline import IngestionPipeline
from app.domains.knowledge.repository import KnowledgeRepository
from app.domains.providers.ollama.embeddings import OllamaEmbeddingsClient

logging.basicConfig(level=logging.INFO, format="%(levelname)-5s %(name)s: %(message)s")


async def main(source_path: str | None) -> None:
    settings = get_settings()
    target = source_path or settings.TRANSCRIPT_INGESTION_DIR

    async with AsyncSessionLocal() as db:
        repository = KnowledgeRepository(db)
        embedding_service = EmbeddingService(ollama_embeddings=OllamaEmbeddingsClient(settings=settings))
        pipeline = IngestionPipeline(repository=repository, embedding_service=embedding_service)

        if Path(target).is_dir():
            episodes = await pipeline.ingest_directory(target)
            await db.commit()
            print(f"Ingested {len(episodes)} episode(s) from {target}:")
            for episode in episodes:
                print(f"  - {episode.title} ({episode.id})")
        else:
            episode = await pipeline.ingest_episode(target)
            await db.commit()
            print(f"Ingested episode: {episode.title} ({episode.id})")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Ingest transcript(s) from a file or directory.")
    parser.add_argument(
        "source_path",
        nargs="?",
        default=None,
        help="Path to a transcript JSON file or a directory of them. "
        "Defaults to settings.TRANSCRIPT_INGESTION_DIR.",
    )
    args = parser.parse_args()
    asyncio.run(main(args.source_path))
