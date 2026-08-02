"""FastAPI application entrypoint.

Instantiates the app, registers shared exception handlers, and includes
each domain's HTTP router. Per REPOSITORY_STRUCTURE.md's MVP simplification,
only `auth`, `sessions`, and `skills` expose routers — `artifacts` and
`knowledge` are internal-only in MVP (see each domain's module docstring).
"""

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.database.session import AsyncSessionLocal
from app.domains.auth.dependencies import ensure_dev_user_exists
from app.domains.auth.router import router as auth_router
from app.domains.sessions.router import router as sessions_router
from app.domains.skills.router import router as skills_router
from app.exceptions import register_exception_handlers

settings = get_settings()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Startup/shutdown hook. Currently only used for `DEV_AUTH_BYPASS`
    dev-user seeding — see `auth.dependencies.ensure_dev_user_exists`.
    """

    if settings.DEV_AUTH_BYPASS:
        try:
            async with AsyncSessionLocal() as db:
                await ensure_dev_user_exists(db)
        except Exception:
            # Best-effort: log clearly and keep booting rather than crash
            # the app over a schema mismatch in the dev-only seed SQL (see
            # that function's docstring for why this can't be guaranteed
            # to match every Supabase Postgres version). Session creation
            # will fail with a foreign-key error until this is resolved.
            logger.exception(
                "DEV_AUTH_BYPASS is enabled but seeding the dev user failed — "
                "requests using the bypass will likely fail with a foreign-key "
                "error on sessions.user_id until this is fixed."
            )

    yield


def create_app() -> FastAPI:
    """Application factory. Keeps app construction test-friendly/importable."""

    app = FastAPI(
        title="Lenny Growth Workspace API",
        version="0.1.0",
        description="Backend for the Lenny Growth Workspace AI workspace.",
        lifespan=lifespan,
    )

    if settings.CORS_ALLOWED_ORIGINS:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=settings.CORS_ALLOWED_ORIGINS,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    register_exception_handlers(app)

    app.include_router(auth_router)
    app.include_router(sessions_router)
    app.include_router(skills_router)

    @app.get("/health", tags=["health"])
    async def health_check() -> dict[str, str]:
        """Liveness probe. Deliberately has no dependencies (DB, providers)."""

        return {"status": "ok"}

    return app


app = create_app()
