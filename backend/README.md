# Lenny Growth Workspace — Backend

FastAPI backend, vertical slice architecture. See `../docs/` for the full
PRD/architecture/schema documentation — this file only covers running the
backend itself.

## Setup

```bash
cd backend
python -m venv .venv
. .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -e ".[test]"
cp .env.example .env        # then fill in the required values below
```

## Required environment variables

See `.env.example` for the full list with defaults. At minimum, these have
no default and must be set:

- `DATABASE_URL` — Supabase/Postgres connection string (`postgresql+asyncpg://...`)
- `SUPABASE_URL`, `SUPABASE_SERVICE_KEY`, `SUPABASE_JWT_SECRET`
- `ANTHROPIC_API_KEY`

For local development without a configured Supabase Auth project, set
`DEV_AUTH_BYPASS=true` — see `app/domains/auth/dependencies.py`.

## Database

```bash
alembic upgrade head          # applies migrations/versions/0001_initial_schema.py
python -m app.domains.knowledge.ingestion.cli   # ingest transcripts from TRANSCRIPT_INGESTION_DIR
```

## Run

```bash
uvicorn app.main:app --reload
```

## Test

```bash
pytest
```

Tests are HTTP-boundary smoke tests (`tests/integration/`) — they exercise
the real FastAPI app and real skill-orchestration logic via `TestClient`,
with fakes substituted only at the database/model-provider boundaries (no
live Postgres/Ollama/Anthropic required, and no Docker — see `CONTEXT.md`,
"No Docker for MVP"). See `tests/integration/conftest.py` for the exact
scope/rationale.
