"""Shared exception types and FastAPI exception-handler registration."""

from app.exceptions.base import AppError
from app.exceptions.handlers import register_exception_handlers

__all__ = ["AppError", "register_exception_handlers"]
