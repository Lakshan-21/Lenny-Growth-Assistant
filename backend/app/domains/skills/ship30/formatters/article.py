"""Long-form article formatting (PRD §6.5)."""


def format_article(*, raw_completion: str) -> str:
    """Ensure the article has a top-level Markdown heading.

    The prompt (`ship30/prompts.py`) already asks for a `# Title` opening
    line; this is a light safety net for when the model omits it — treats
    the first line as the title and promotes it, rather than rejecting or
    re-prompting (keeps this a pure, cheap post-processing step).
    """

    text = raw_completion.strip()
    if text.startswith("#"):
        return text

    first_line, _, rest = text.partition("\n")
    title = first_line.strip().rstrip(":")
    rest = rest.strip()
    return f"# {title}\n\n{rest}".rstrip()
