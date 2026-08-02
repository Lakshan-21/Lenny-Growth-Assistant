"""Knowledge-domain exceptions."""

from app.exceptions.base import AppError, NotFoundError


class KnowledgeError(AppError):
    """Base class for knowledge-domain errors."""

    error_code = "knowledge_error"


class InsufficientGroundingError(KnowledgeError):
    """No transcript chunks sufficiently relevant to the query were found.

    Raised by `retrieval_service.py` / caught by `skills/qa/service.py` to
    return an explicit "cannot find sufficient grounding" response instead
    of fabricating an answer (PRD §6.3 acceptance criteria).
    """

    status_code = 200  # not an HTTP failure — a valid, explicit "no grounding" outcome
    error_code = "insufficient_grounding"


class EpisodeNotFoundError(NotFoundError):
    """No episode exists with the given id."""

    error_code = "episode_not_found"


class TranscriptLoadError(KnowledgeError):
    """A transcript source file could not be read or parsed during
    ingestion (missing/malformed file, missing required fields, etc.)."""

    status_code = 422
    error_code = "transcript_load_error"
