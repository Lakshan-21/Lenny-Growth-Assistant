"""Providers-domain exceptions."""

from app.exceptions.base import UpstreamServiceError


class ProvidersError(UpstreamServiceError):
    """Base class for providers-domain errors."""

    error_code = "providers_error"


class ProviderUnavailableError(ProvidersError):
    """A single provider (Ollama or Anthropic) failed, timed out, or failed
    its health check. Raised by individual provider clients; caught by
    `gateway.py` to trigger failover."""

    error_code = "provider_unavailable"


class ProviderResponseError(ProviderUnavailableError):
    """The provider responded, but with an unexpected/invalid payload —
    failed JSON decoding, failed schema validation, wrong embedding
    dimension, etc.

    Deliberately a subclass of `ProviderUnavailableError` (not a sibling):
    from the gateway's perspective, "responded with garbage" and "didn't
    respond at all" both mean this provider can't be used right now, so
    both must trigger the same failover path in `gateway.py` without that
    module needing to know about this subclass specifically.
    """

    error_code = "provider_response_error"


class AllProvidersUnavailableError(ProvidersError):
    """Both the primary and secondary providers failed — no graceful
    degradation possible. This is the only case that should surface as a
    hard failure to the end user (PRD §8, "Availability")."""

    error_code = "all_providers_unavailable"
