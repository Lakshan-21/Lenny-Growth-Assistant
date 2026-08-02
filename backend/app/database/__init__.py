"""Shared database package: declarative base, async session/engine factory.

Every domain's `models.py` imports `Base` from here; every domain's
`repository.py` receives an `AsyncSession` via `get_db` (FastAPI dependency).
"""

from app.database.base import Base
from app.database.session import get_db

__all__ = ["Base", "get_db"]
