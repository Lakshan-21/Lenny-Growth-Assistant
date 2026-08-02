"""Auth HTTP endpoints: register, login, logout, password reset.

Route bodies are placeholders — they wire the request into `AuthService`
and return its result; the actual Supabase Auth calls are TODO in
`service.py`/`supabase_client.py`.
"""

from fastapi import APIRouter, Depends, status

from app.domains.auth.dependencies import (
    AuthenticatedUser,
    get_auth_service,
    get_current_user,
)
from app.domains.auth.schemas import (
    LoginRequest,
    PasswordResetConfirmRequest,
    PasswordResetRequest,
    RegisterRequest,
    TokenResponse,
    UserRead,
)
from app.domains.auth.service import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
async def register(
    data: RegisterRequest,
    auth_service: AuthService = Depends(get_auth_service),
) -> UserRead:
    """Create a new account (PRD §6.1)."""

    return await auth_service.register(data)


@router.post("/login", response_model=TokenResponse)
async def login(
    data: LoginRequest,
    auth_service: AuthService = Depends(get_auth_service),
) -> TokenResponse:
    """Authenticate and receive session tokens (PRD §6.1)."""

    return await auth_service.login(data)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    current_user: AuthenticatedUser = Depends(get_current_user),
    auth_service: AuthService = Depends(get_auth_service),
) -> None:
    """Invalidate the current session (PRD §6.1)."""

    # TODO: the current access token (not just the user) is needed to call
    # sign_out — thread it through once get_current_user exposes the raw token.
    raise NotImplementedError


@router.post("/password-reset/request", status_code=status.HTTP_202_ACCEPTED)
async def request_password_reset(
    data: PasswordResetRequest,
    auth_service: AuthService = Depends(get_auth_service),
) -> None:
    """Send a password-reset email (PRD §6.1)."""

    await auth_service.request_password_reset(data)


@router.post("/password-reset/confirm", status_code=status.HTTP_204_NO_CONTENT)
async def confirm_password_reset(
    data: PasswordResetConfirmRequest,
    auth_service: AuthService = Depends(get_auth_service),
) -> None:
    """Complete a password reset using the emailed token (PRD §6.1)."""

    await auth_service.confirm_password_reset(data)
