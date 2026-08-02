"""Auth-domain exceptions. All inherit from the shared `AppError` hierarchy."""

from app.exceptions.base import ConflictError, UnauthorizedError, ValidationError


class AuthError(UnauthorizedError):
    """Base class for auth-domain errors. Defaults to 401; subclasses may override."""

    error_code = "auth_error"


class InvalidCredentialsError(AuthError):
    """Email/password combination is invalid."""

    error_code = "invalid_credentials"


class TokenInvalidError(AuthError):
    """Bearer token is missing, malformed, expired, or fails signature verification."""

    error_code = "token_invalid"


class UserAlreadyExistsError(ConflictError):
    """Registration attempted with an email that already has an account."""

    error_code = "user_already_exists"


class ResetTokenExpiredError(ValidationError):
    """Password reset token is expired or already used."""

    error_code = "reset_token_expired"
