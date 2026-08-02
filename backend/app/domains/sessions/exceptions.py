"""Sessions-domain exceptions."""

from app.exceptions.base import ForbiddenError, NotFoundError


class SessionsError(NotFoundError):
    """Base class for sessions-domain errors. Defaults to 404; subclasses may override."""

    error_code = "sessions_error"


class SessionNotFoundError(SessionsError):
    """No session exists with the given id (or it belongs to another user)."""

    error_code = "session_not_found"


class SessionNotOwnedError(ForbiddenError):
    """Session exists but does not belong to the current user."""

    error_code = "session_not_owned"


class MessageNotFoundError(SessionsError):
    """No message exists with the given id within the given session."""

    error_code = "message_not_found"
