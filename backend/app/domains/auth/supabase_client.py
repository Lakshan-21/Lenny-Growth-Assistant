"""Thin wrapper around the Supabase Auth SDK client.

Isolates the third-party `supabase-py` client behind a narrow interface so
`service.py` depends on this module's typed methods, not the SDK directly.
No business logic here — pure pass-through to Supabase Auth.
"""

from dataclasses import dataclass

from app.config import Settings


@dataclass(frozen=True, slots=True)
class SupabaseAuthSession:
    """Minimal shape of a Supabase Auth session response."""

    access_token: str
    refresh_token: str
    expires_in: int
    user_id: str
    email: str


class SupabaseAuthClient:
    """Wraps Supabase Auth operations used by `auth/service.py`.

    Constructor-injected with `Settings` rather than reading env vars
    directly, per the project's constructor-based DI convention.
    """

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        # TODO: instantiate the real `supabase-py` client, e.g.
        #   from supabase import create_client
        #   self._client = create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_KEY)

    async def sign_up(self, *, email: str, password: str) -> SupabaseAuthSession:
        """Create a new Supabase Auth user.

        TODO: call `self._client.auth.sign_up(...)`; translate SDK errors
        (e.g. duplicate email) into `auth.exceptions.UserAlreadyExistsError`.
        """

        raise NotImplementedError

    async def sign_in_with_password(self, *, email: str, password: str) -> SupabaseAuthSession:
        """Authenticate an existing user.

        TODO: call `self._client.auth.sign_in_with_password(...)`; translate
        invalid-credential SDK errors into `auth.exceptions.InvalidCredentialsError`.
        """

        raise NotImplementedError

    async def sign_out(self, *, access_token: str) -> None:
        """Invalidate the given session.

        TODO: call `self._client.auth.sign_out(...)` (or admin sign-out by token).
        """

        raise NotImplementedError

    async def request_password_reset(self, *, email: str) -> None:
        """Trigger Supabase's password-reset email flow.

        TODO: call `self._client.auth.reset_password_for_email(...)`.
        """

        raise NotImplementedError

    async def confirm_password_reset(self, *, reset_token: str, new_password: str) -> None:
        """Complete a password reset using the token from the emailed link.

        TODO: exchange/verify `reset_token` and update the password via the
        Supabase Auth SDK; translate an expired/used token into
        `auth.exceptions.ResetTokenExpiredError`.
        """

        raise NotImplementedError
