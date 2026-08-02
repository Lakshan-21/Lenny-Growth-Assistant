"""FastAPI exception-handler registration.

Maps the `AppError` hierarchy (app/exceptions/base.py + each domain's
exceptions.py) to consistent JSON error responses, so individual routers
never need their own try/except-to-HTTPException boilerplate.
"""

import logging

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from app.exceptions.base import AppError

logger = logging.getLogger(__name__)


async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    """Convert any `AppError` subclass into a structured JSON response."""

    return JSONResponse(
        status_code=exc.status_code,
        content={"error_code": exc.error_code, "message": exc.message},
    )


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Last-resort handler for exceptions not modeled as `AppError`.

    Logs the full exception server-side but returns a generic message to
    the client — never leak internals (stack traces, query text, etc.).
    """

    logger.exception("Unhandled exception on %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"error_code": "internal_error", "message": "An unexpected error occurred."},
    )


def register_exception_handlers(app: FastAPI) -> None:
    """Wire the handlers above into the FastAPI app. Called once from main.py."""

    app.add_exception_handler(AppError, app_error_handler)
    app.add_exception_handler(Exception, unhandled_exception_handler)
