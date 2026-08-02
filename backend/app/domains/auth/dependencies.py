"""FastAPI dependency wiring for the auth domain.

`get_current_user` is consumed by every other domain's `dependencies.py`
(sessions, skills, ...) to resolve "who is making this request" — this is
the application-layer identity check that RLS Option A (DATABASE_SCHEMA.md
§8 risk #2) relies on, since the backend's DB connection itself uses the
Supabase `service_role` key and does not carry per-request identity.
"""

import logging
import uuid
from dataclasses import dataclass

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.domains.auth.exceptions import TokenInvalidError
from app.domains.auth.service import AuthService
from app.domains.auth.supabase_client import SupabaseAuthClient

logger = logging.getLogger(__name__)

# auto_error=False (not the default True): DEV_AUTH_BYPASS must work with no
# Authorization header sent at all ("no JWT validation occurs"), which is
# only possible if the scheme itself doesn't fail the request before
# get_current_user's body ever runs. See get_current_user for the
# resulting, slightly different error shape on the disabled/no-header path.
_bearer_scheme = HTTPBearer(auto_error=False)

# Fixed identity returned by DEV_AUTH_BYPASS. Not a real Supabase Auth user
# in the "signed up through GoTrue" sense, but a real row in `auth.users`
# (see ensure_dev_user_exists) so FK constraints on sessions.user_id etc.
# are satisfied.
DEV_USER_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")
DEV_USER_EMAIL = "dev@localhost"


@dataclass(frozen=True, slots=True)
class AuthenticatedUser:
    """Resolved identity of the caller, derived from a verified Supabase JWT
    — or, when `DEV_AUTH_BYPASS` is enabled, the fixed dev identity above."""

    id: uuid.UUID
    email: str


def get_supabase_auth_client(settings: Settings = Depends(get_settings)) -> SupabaseAuthClient:
    return SupabaseAuthClient(settings=settings)


def get_auth_service(
    supabase_auth: SupabaseAuthClient = Depends(get_supabase_auth_client),
) -> AuthService:
    return AuthService(supabase_auth=supabase_auth)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
    settings: Settings = Depends(get_settings),
) -> AuthenticatedUser:
    """Resolve the calling user.

    When `settings.DEV_AUTH_BYPASS` is true, always returns the fixed dev
    user — no bearer token is required or inspected, regardless of what
    (if anything) was sent. This branch is checked first and returns
    unconditionally, so it can never fall through to the real path below.

    When disabled (the default), behavior is unchanged in substance from
    before this feature existed — a token is required and real JWT
    verification is still `NotImplementedError`-equivalent (raises
    `TokenInvalidError`; verification itself is explicitly out of scope
    here). One shape difference: a missing header now surfaces as this
    function's own `TokenInvalidError` (401) rather than `HTTPBearer`'s
    default `HTTPException` (403) — an unavoidable side effect of
    `auto_error=False`, needed so the bypass branch above can run without
    a header at all.
    """

    if settings.DEV_AUTH_BYPASS:
        return AuthenticatedUser(id=DEV_USER_ID, email=DEV_USER_EMAIL)

    if credentials is None:
        raise TokenInvalidError("Missing bearer token")

    # TODO: verify `credentials.credentials` against `settings.SUPABASE_JWT_SECRET`
    # (e.g. via `jwt.decode(..., algorithms=["HS256"])`), extract `sub` (user id)
    # and `email` claims, and construct `AuthenticatedUser`. Raise
    # `TokenInvalidError` on any verification failure (missing/expired/malformed).
    raise TokenInvalidError("JWT verification not yet implemented")


async def ensure_dev_user_exists(db: AsyncSession) -> None:
    """Idempotently seed the fixed `DEV_AUTH_BYPASS` user directly into
    Supabase's `auth.users` — and, transitively, `public.profiles` via the
    `handle_new_user` trigger (DATABASE_SCHEMA.md §2) — so that FK
    constraints on `sessions.user_id` etc. are satisfiable while bypass
    mode is on. Called once at startup from `main.py`, only when
    `DEV_AUTH_BYPASS=true`.

    Raw SQL, not the Supabase Admin API/SDK: `DEV_AUTH_BYPASS` is meant to
    let the backend run against a bare Postgres with migration `0001`
    applied, with no live Supabase Auth service required at all. This is
    the well-known "seed a Supabase auth user via SQL" pattern, using
    `pgcrypto`'s `crypt()`/`gen_salt()` (already enabled by migration
    0001) for a syntactically-valid password hash that is never actually
    used to log in. **Local/dev use only — never run against a real
    Supabase project.**

    Column set targets current Supabase Postgres `auth.users`; if your
    instance's schema differs, adjust the INSERT below (the caller in
    `main.py` catches and logs failures here rather than crashing startup).
    """

    await db.execute(
        text(
            """
            INSERT INTO auth.users (
                instance_id, id, aud, role, email, encrypted_password,
                email_confirmed_at, created_at, updated_at,
                raw_app_meta_data, raw_user_meta_data
            )
            VALUES (
                '00000000-0000-0000-0000-000000000000', :id, 'authenticated', 'authenticated',
                :email, crypt('dev-bypass-unused-password', gen_salt('bf')),
                now(), now(), now(),
                '{"provider": "dev-bypass", "providers": ["dev-bypass"]}'::jsonb, '{}'::jsonb
            )
            ON CONFLICT (id) DO NOTHING
            """
        ),
        {"id": str(DEV_USER_ID), "email": DEV_USER_EMAIL},
    )
    await db.commit()
    logger.info("DEV_AUTH_BYPASS: ensured dev user %s (%s) exists in auth.users", DEV_USER_ID, DEV_USER_EMAIL)
