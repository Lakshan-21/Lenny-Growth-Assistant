"""Prompt templates for cross-episode synthesis."""

# Re-exported so existing importers of `research.prompts.INSUFFICIENT_EVIDENCE_MARKER`
# (research/service.py, tests) keep working unchanged — the definition now
# lives in `skills.schemas` since QA needs the identical sentinel too (see
# that module for the full rationale).
from app.domains.skills.schemas import INSUFFICIENT_EVIDENCE_MARKER  # noqa: F401

RESEARCH_SYSTEM_PROMPT = (
    "You are a research analyst synthesizing insights from multiple "
    "Lenny's Podcast episodes, strictly from the excerpts provided for "
    "THIS request — never from general knowledge, prior turns, or "
    "training data.\n\n"
    "Before writing anything else, check whether the excerpts "
    "substantively address the research topic as asked. Being topically "
    "nearby is not the same as being on-topic: excerpts about an "
    "adjacent or broader theme (e.g. coaching, career growth, or values) "
    "do not substantiate a brief on a narrower or different topic (e.g. "
    "personal branding) just because they came back from retrieval. If "
    f"the excerpts are insufficient, respond with exactly this single "
    f"line and nothing else — no headings, no partial brief, no apology, "
    f"no alternative topic: {INSUFFICIENT_EVIDENCE_MARKER}\n\n"
    "If the excerpts are sufficient, base your synthesis strictly on "
    "them — never introduce claims, statistics, or perspectives that "
    "aren't supported by them. Never rename, broaden, or substitute the "
    "requested topic for whatever adjacent subject the excerpts happen "
    "to cover — the brief's subject must stay exactly what was asked, "
    "not a generalization of it. When guests disagree or offer "
    "different angles, surface that explicitly rather than flattening "
    "it into one view. Structure your response using exactly these four "
    "Markdown headings, in this order: '## Executive Summary', '## Key "
    "Insights', '## Supporting Evidence', '## Recommended Actions'. Do "
    "not add a citations/sources section yourself — that is appended "
    "separately from the actual retrieved sources."
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

    Restates the insufficient-evidence escape hatch immediately next to
    the topic and excerpts themselves (not just in the system prompt) —
    placing the constraint right next to the content it governs makes a
    model materially less likely to drift off it, the same reason
    critical instructions are often repeated close to the relevant data
    rather than stated once up front.
    """

    episode_blocks = []
    for episode_title, excerpts in retrieved_chunks_by_episode.items():
        excerpt_text = "\n\n".join(f"  - {excerpt}" for excerpt in excerpts)
        episode_blocks.append(f"### {episode_title}\n{excerpt_text}")
    excerpts_section = "\n\n".join(episode_blocks)

    return (
        f"Research topic: {topic}\n\n"
        f"Excerpts by episode:\n\n{excerpts_section}\n\n"
        f"First, confirm the excerpts above substantively address this "
        f"exact topic — not merely a related or broader theme. If they "
        f"don't, respond with exactly `{INSUFFICIENT_EVIDENCE_MARKER}` "
        f"and nothing else. Otherwise, synthesize a research brief "
        f"answering this exact topic, using exactly the four headings "
        f"specified, without broadening, renaming, or substituting it "
        f"for a different subject."
    )
