"""Shared configuration package.

Exposes a single module-level `settings` instance (see `settings.py`)
that every domain imports rather than reading environment variables
directly.
"""

from app.config.settings import Settings, get_settings, settings

__all__ = ["Settings", "get_settings", "settings"]
