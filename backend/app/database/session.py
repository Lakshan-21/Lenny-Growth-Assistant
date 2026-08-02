"""Async database session/connection factory.

Backend connects using the Supabase `service_role` connection string
(RLS Option A — see DATABASE_SCHEMA.md §8 risk #2). RLS policies remain
enabled on every table as defense-in-depth; ownership is enforced in each
domain's service/repository layer using the authenticated user's id
resolved by `app.domains.auth.dependencies.get_current_user`.
"""

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

from app.config import get_settings

_settings = get_settings()

engine: AsyncEngine = create_async_engine(
    _settings.DATABASE_URL,
    echo=False,
    pool_pre_ping=True,
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
    expire_on_commit=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency yielding a request-scoped `AsyncSession`.

    Commits on clean exit, rolls back on exception, always closes. Domain
    `repository.py` modules receive this session via constructor injection
    (see each domain's `dependencies.py`), never import it directly.
    """

    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
