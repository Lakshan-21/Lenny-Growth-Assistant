"""Auth domain service: orchestrates Supabase Auth calls.

Contains no password-handling logic of its own — Supabase Auth owns
credential storage (per CONTEXT.md / REPOSITORY_STRUCTURE.md §3).
"""

from app.domains.auth.schemas import (
    LoginRequest,
    PasswordResetConfirmRequest,
    PasswordResetRequest,
    RegisterRequest,
    TokenResponse,
    UserRead,
)
from app.domains.auth.supabase_client import SupabaseAuthClient


class AuthService:
    """Constructor-injected with its collaborators — no hidden global state."""

    def __init__(self, supabase_auth: SupabaseAuthClient) -> None:
        self._supabase_auth = supabase_auth

    async def register(self, data: RegisterRequest) -> UserRead:
        """Create a new account.

        TODO: call `self._supabase_auth.sign_up(...)`, map the resulting
        session's user to `UserRead`. The `profiles` row is created
        automatically by the DB trigger (see auth/models.py) — no explicit
        profile-creation call is needed here.
        """

        raise NotImplementedError

    async def login(self, data: LoginRequest) -> TokenResponse:
        """Authenticate and return session tokens.

        TODO: call `self._supabase_auth.sign_in_with_password(...)`, map to
        `TokenResponse`.
        """

        raise NotImplementedError

    async def logout(self, *, access_token: str) -> None:
        """Invalidate the current session.

        TODO: call `self._supabase_auth.sign_out(...)`.
        """

        raise NotImplementedError

    async def request_password_reset(self, data: PasswordResetRequest) -> None:
        """Kick off the emailed password-reset flow.

        TODO: call `self._supabase_auth.request_password_reset(...)`.
        Deliberately does not reveal whether the email exists (avoid
        account enumeration) — always returns success from the router.
        """

        raise NotImplementedError

    async def confirm_password_reset(self, data: PasswordResetConfirmRequest) -> None:
        """Complete a password reset.

        TODO: call `self._supabase_auth.confirm_password_reset(...)`.
        """

        raise NotImplementedError
