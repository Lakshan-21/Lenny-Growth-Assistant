"""Typed, environment-driven application settings.

Single source of configuration for every domain (per REPOSITORY_STRUCTURE.md
§3, "the single place configuration is read from"). No domain should call
`os.environ` directly — inject `Settings` (via `get_settings`) instead.

Env var naming follows REPOSITORY_STRUCTURE.md §4: UPPER_SNAKE_CASE,
prefixed by concern (SUPABASE_*, OLLAMA_*, ANTHROPIC_*).
"""

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration, populated from environment variables / `.env`.

    Field values below are placeholders only — real values are supplied via
    the environment at deploy/run time (see backend/.env.example).
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # --- App -----------------------------------------------------------
    APP_ENV: str = Field(default="development")
    LOG_LEVEL: str = Field(default="INFO")
    CORS_ALLOWED_ORIGINS: list[str] = Field(default_factory=list)
    # Dev-only escape hatch: when true, auth.dependencies.get_current_user
    # returns a fixed development user with no JWT validation at all — see
    # that module's docstring. Defaults to False so it can never be
    # accidentally left on; do not set true outside local development.
    DEV_AUTH_BYPASS: bool = Field(default=False)

    # --- Database (Supabase PostgreSQL + pgvector) ----------------------
    # Direct Postgres connection string (asyncpg), used by database/session.py.
    DATABASE_URL: str

    # --- Supabase Auth ---------------------------------------------------
    SUPABASE_URL: str
    # RLS strategy: Option A per DATABASE_SCHEMA.md §8 risk #2 — backend
    # connects with the service_role key; ownership is enforced in each
    # domain's service/repository layer, not by RLS for backend-issued
    # queries. RLS policies remain enabled as defense-in-depth.
    SUPABASE_SERVICE_KEY: str
    # Used by auth/dependencies.py to verify the bearer JWT on incoming
    # requests (identity check), independent of which DB role is used.
    SUPABASE_JWT_SECRET: str

    # --- Providers: Ollama (primary) -------------------------------------
    OLLAMA_BASE_URL: str = Field(default="http://localhost:11434")
    OLLAMA_GENERATION_MODEL: str = Field(default="llama3.1")
    OLLAMA_EMBEDDING_MODEL: str = Field(default="bge-m3")
    OLLAMA_REQUEST_TIMEOUT_SECONDS: float = Field(default=30.0)
    # Ollama configuration review: on GPUs too small to hold both the
    # generation and embedding models resident at once (e.g. a 4GB card
    # with an 8B generation model), every switch between them evicts
    # whichever model isn't currently needed, forcing a full reload on the
    # next call of either -- confirmed empirically (~2.5s warm vs ~14s
    # reload for bge-m3; ~3.3s warm vs ~22s reload for llama3.1). Since QA
    # and Research always call embed-then-generate in the same request,
    # this thrashes on every single request. Forcing the small embedding
    # model (bge-m3, 566M) onto CPU via Ollama's `options.num_gpu=0`
    # request parameter leaves the GPU exclusively for the generation
    # model, which is what actually needs it. Defaults to true (the
    # recommended posture); set false to let Ollama place embeddings on
    # GPU as before (e.g. on hardware with enough VRAM for both models).
    OLLAMA_EMBEDDING_FORCE_CPU: bool = Field(default=True)

    # --- Knowledge: transcript ingestion ----------------------------------
    # Directory scanned by knowledge/ingestion/cli.py for transcript JSON
    # files (see that module's docstring for the expected file format).
    TRANSCRIPT_INGESTION_DIR: str = Field(default="./transcripts")

    # --- Providers: Anthropic (secondary / fallback) ----------------------
    ANTHROPIC_API_KEY: str
    ANTHROPIC_MODEL: str = Field(default="claude-sonnet-4-5")
    ANTHROPIC_REQUEST_TIMEOUT_SECONDS: float = Field(default=30.0)


@lru_cache
def get_settings() -> Settings:
    """FastAPI-dependency-friendly cached settings accessor.

    `lru_cache` ensures `Settings()` (which reads the environment) runs once
    per process; use this via `Depends(get_settings)` in routers/dependencies
    rather than importing the module-level `settings` singleton directly,
    so tests can override it with `app.dependency_overrides`.
    """

    return Settings()


# Module-level singleton for non-FastAPI-dependency contexts (e.g. the
# ingestion CLI in knowledge/ingestion/cli.py).
settings = get_settings()
