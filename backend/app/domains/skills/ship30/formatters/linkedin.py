"""LinkedIn post formatting/constraints (PRD §6.5)."""

_LINKEDIN_MAX_CHARS = 3000  # LinkedIn's actual post character limit
_TRUNCATION_SUFFIX = "…"


def format_linkedin_post(*, raw_completion: str) -> str:
    """Enforce LinkedIn's hard length constraint. The prompt already asks
    the model for ~150-300 words (well under this), so this is a safety
    net, not the primary length control — mirrors how `format_x_thread`
    enforces its own hard per-tweet limit independent of prompt wording.
    """

    text = raw_completion.strip()
    if len(text) <= _LINKEDIN_MAX_CHARS:
        return text
    cutoff = _LINKEDIN_MAX_CHARS - len(_TRUNCATION_SUFFIX)
    return text[:cutoff].rstrip() + _TRUNCATION_SUFFIX
