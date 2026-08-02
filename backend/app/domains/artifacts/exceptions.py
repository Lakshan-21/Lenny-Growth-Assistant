"""Artifacts-domain exceptions."""

from app.exceptions.base import NotFoundError


class ArtifactsError(NotFoundError):
    """Base class for artifacts-domain errors. Defaults to 404."""

    error_code = "artifacts_error"


class ArtifactNotFoundError(ArtifactsError):
    """No artifact exists with the given id within the given session."""

    error_code = "artifact_not_found"
