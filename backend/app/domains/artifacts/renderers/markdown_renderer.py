"""Passthrough/formatting for the canonical Markdown view (PRD §6.6)."""


def render_markdown(*, content_markdown: str) -> str:
    """Canonical view is `content_markdown` verbatim — no transformation
    (ADR-4, ARCHITECTURE.md: Markdown is the single source of truth).

    Present as a function (not a no-op passthrough inline in the caller) so
    future light formatting (e.g. trailing-whitespace normalization) has an
    obvious, single place to live without touching callers.
    """

    return content_markdown
