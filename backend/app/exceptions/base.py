"""Root application exception type.

Every domain defines its own `exceptions.py` with a local base inheriting
from `AppError` (e.g. `class SessionsError(AppError): ...`), then concrete
`{Reason}Error` subclasses of that (e.g. `SessionNotFoundError`). This lets
`exceptions/handlers.py` map the whole hierarchy to HTTP responses in one
place without each domain touching FastAPI directly.
"""


class AppError(Exception):
    """Base class for all application-defined errors.

    Attributes:
        message: Human-readable error description (safe to return to clients).
        status_code: HTTP status code this error should map to.
        error_code: Stable, machine-readable identifier for API consumers
            (e.g. "session_not_found"), independent of the HTTP status code.
    """

    status_code: int = 500
    error_code: str = "internal_error"

    def __init__(self, message: str | None = None) -> None:
        self.message = message or self.__class__.__doc__ or self.error_code
        super().__init__(self.message)


class NotFoundError(AppError):
    """Requested resource does not exist (or is not visible to this caller)."""

    status_code = 404
    error_code = "not_found"


class ValidationError(AppError):
    """Request failed a domain-level validation rule."""

    status_code = 422
    error_code = "validation_error"


class UnauthorizedError(AppError):
    """Caller is not authenticated."""

    status_code = 401
    error_code = "unauthorized"


class ForbiddenError(AppError):
    """Caller is authenticated but does not own/cannot access this resource."""

    status_code = 403
    error_code = "forbidden"


class ConflictError(AppError):
    """Request conflicts with the current state of the resource."""

    status_code = 409
    error_code = "conflict"


class UpstreamServiceError(AppError):
    """A dependency (model provider, Supabase, etc.) failed or was unavailable."""

    status_code = 502
    error_code = "upstream_service_error"
