"""Prompt templates for cross-episode synthesis."""

RESEARCH_SYSTEM_PROMPT = (
    "You are a research analyst synthesizing insights from multiple "
    "Lenny's Podcast episodes. Base your synthesis strictly on the "
    "provided excerpts — never introduce claims, statistics, or "
    "perspectives that aren't supported by them. When guests disagree or "
    "offer different angles, surface that explicitly rather than "
    "flattening it into one view. Structure your response using exactly "
    "these four Markdown headings, in this order: '## Executive Summary', "
    "'## Key Insights', '## Supporting Evidence', '## Recommended "
    "Actions'. Do not add a citations/sources section yourself — that is "
    "appended separately from the actual retrieved sources."
)

QUERY_EXPANSION_SYSTEM_PROMPT = (
    "You turn a single research question into several distinct search "
    "queries covering different angles of it, to retrieve broader source "
    "material than a single query would. Output exactly one query per "
    "line, plain text, no numbering, no bullets, no commentary."
)


def build_query_expansion_prompt(*, question: str, num_queries: int) -> str:
    """Ask the model to decompose one research question into several
    retrieval queries covering different angles/sub-topics (requirement:
    "Generate multiple retrieval queries from the user's question")."""

    return (
        f"Generate {num_queries} distinct search queries covering different "
        f"angles, sub-topics, or related considerations of this research "
        f"question:\n\n{question}"
    )


def parse_subqueries(raw_completion: str, *, max_queries: int) -> list[str]:
    """Parse one query per line from a query-expansion completion,
    stripping any numbering/bullet formatting the model added despite
    being asked not to."""

    queries: list[str] = []
    for line in raw_completion.splitlines():
        cleaned = line.strip().lstrip("-*•0123456789.() ").strip()
        if cleaned:
            queries.append(cleaned)
    return queries[:max_queries]


def build_research_prompt(*, topic: str, retrieved_chunks_by_episode: dict[str, list[str]]) -> str:
    """Assemble the synthesis prompt, with excerpts grouped by episode so
    the model can reason about per-episode/per-guest perspectives (PRD
    §6.4: "key perspectives by guest, areas of agreement/disagreement").
    """

    episode_blocks = []
    for episode_title, excerpts in retrieved_chunks_by_episode.items():
        excerpt_text = "\n\n".join(f"  - {excerpt}" for excerpt in excerpts)
        episode_blocks.append(f"### {episode_title}\n{excerpt_text}")
    excerpts_section = "\n\n".join(episode_blocks)

    return (
        f"Research question: {topic}\n\n"
        f"Excerpts by episode:\n\n{excerpts_section}\n\n"
        f"Synthesize a research brief answering the question above, using "
        f"exactly the four headings specified."
    )
