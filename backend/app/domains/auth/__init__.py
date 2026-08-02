"""Auth domain: register, login, logout, password reset.

Thin orchestration layer in front of Supabase Auth (source of truth for
credentials — see CONTEXT.md). This domain does not implement its own
password hashing/storage.
"""

# Ensures `Profile` registers on `Base.metadata` whenever this package is
# imported (main.py imports `auth.router`, which triggers this __init__),
# so Alembic autogenerate sees it even though no other domain's models.py
# holds a foreign key into `profiles`.
from app.domains.auth.models import Profile  # noqa: F401

