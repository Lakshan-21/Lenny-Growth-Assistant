export interface ResearchBriefPreview {
  title: string;
  summary: string;
  sourceCount: number;
}

/**
 * `research_briefs.topic`/`summary` exist in the database
 * (DATABASE_SCHEMA.md §2) but aren't exposed by `GET /sessions/{id}
 * /artifacts` today — `ArtifactRead` has no join to that table. Deriving a
 * title/summary/source-count from the already-fetched `content_markdown`
 * gives the Research tab its own presentation without a backend change.
 *
 * Relies on the shape `research/service.py::_render_brief_markdown`
 * guarantees: a leading `# {topic}` line, `## `-headed sections, and a
 * trailing `## Citations` section of `N. {label}` lines.
 */
export function parseResearchBriefPreview(markdown: string): ResearchBriefPreview {
  const lines = markdown.split("\n");
  const titleLine = lines.find((line) => line.trim().startsWith("# "));
  const title = titleLine?.replace(/^#\s*/, "").trim() || "Untitled research brief";

  const titleIndex = titleLine ? lines.indexOf(titleLine) : -1;
  const summary =
    lines
      .slice(titleIndex + 1)
      .find((line) => line.trim() && !line.trim().startsWith("#"))
      ?.trim() ?? "";

  const sourceCount = (markdown.match(/^\d+\.\s+\S/gm) ?? []).length;

  return { title, summary, sourceCount };
}
