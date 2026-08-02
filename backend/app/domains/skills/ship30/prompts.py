"""Prompt templates for Ship30 content generation."""

SHIP30_SYSTEM_PROMPT = (
    "You are a skilled content writer who turns podcast-derived insights "
    "into ready-to-publish content. Base your output strictly on the "
    "provided source material — do not invent claims, statistics, or "
    "quotes that aren't supported by it. Match the tone, length, and "
    "structural conventions of the requested format exactly."
)

_FORMAT_GUIDANCE: dict[str, str] = {
    "linkedin_post": (
        "Write a single LinkedIn post. Professional but conversational tone. "
        "150-300 words. Short paragraphs (1-3 sentences each). Open with a "
        "hook line. End with a question or reflection prompt. At most 3 "
        "relevant hashtags, if any. Plain text — no Markdown headings."
    ),
    "x_thread": (
        "Write an X/Twitter thread. The first tweet is a strong, "
        "standalone hook. Each following tweet makes one self-contained "
        "point in plain text (no Markdown formatting inside a tweet). "
        "Separate each tweet with a blank line. Aim for 5-8 tweets total. "
        "Keep each tweet well under 280 characters."
    ),
    "article": (
        "Write a long-form article in Markdown. Start with a single "
        "'# Title' heading, a short introductory paragraph, 2-4 '## ' "
        "sections with substantive paragraphs, and a brief closing "
        "paragraph. No filler — every section should say something "
        "concrete drawn from the source material."
    ),
}


def build_ship30_prompt(*, content_type: str, instruction: str, source_markdown: str) -> str:
    """Assemble the generation prompt for the given content type.

    `instruction` is the user's own request text (e.g. "turn this into a
    LinkedIn post focused on onboarding") — kept separate from
    `source_markdown` (the prior QA/Research content being transformed) so
    the model can distinguish "what to write about" from "how the user
    wants it framed."
    """

    guidance = _FORMAT_GUIDANCE[content_type]
    label = content_type.replace("_", " ")
    return (
        f"{guidance}\n\n"
        f"Source material:\n{source_markdown}\n\n"
        f"User's request: {instruction}\n\n"
        f"Write the {label} now — output only the {label} itself, no preamble or explanation."
    )
