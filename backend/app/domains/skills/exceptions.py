"""Skills-domain exceptions."""

from app.exceptions.base import AppError, ValidationError


class SkillsError(AppError):
    """Base class for skills-domain errors."""

    error_code = "skills_error"


class UnroutableMessageError(ValidationError):
    """The router could not resolve a message to any skill (auto-classification
    failed and no manual override was supplied)."""

    error_code = "unroutable_message"


class SkillExecutionError(SkillsError):
    """A skill was invoked successfully but failed while producing its result."""

    status_code = 502
    error_code = "skill_execution_error"
