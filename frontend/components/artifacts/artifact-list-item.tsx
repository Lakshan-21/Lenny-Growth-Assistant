import { Badge } from "@/components/ui/badge";
import { ARTIFACT_TYPE_LABEL } from "@/lib/artifact-labels";
import { formatRelativeTime } from "@/lib/utils";
import type { Artifact } from "@/types/domain";

interface ArtifactListItemProps {
  artifact: Artifact;
  onOpen: () => void;
}

/** First non-empty line of the Markdown, stripped of leading `#`s, as a title-ish preview. */
function previewLine(markdown: string): string {
  const line = markdown.split("\n").find((candidate) => candidate.trim().length > 0) ?? "";
  return line.replace(/^#+\s*/, "").slice(0, 80);
}

// Returns the `<button>` only, no wrapping `<li>` — `ArtifactsList` (the
// only caller) supplies exactly one `<li>` per row for both this and
// `ResearchBriefListItem`, so nesting one here too would be invalid HTML
// (`<li>` inside `<li>`).
export function ArtifactListItem({ artifact, onOpen }: ArtifactListItemProps) {
  return (
    <button
      type="button"
      onClick={onOpen}
      className="flex min-w-0 w-full flex-col gap-1 rounded-md border border-border bg-card p-3 text-left transition-colors hover:bg-muted"
    >
      <div className="flex items-center justify-between gap-2">
        <Badge variant="soft">{ARTIFACT_TYPE_LABEL[artifact.artifact_type]}</Badge>
        <span className="text-xs text-muted-foreground">{formatRelativeTime(artifact.created_at)}</span>
      </div>
      {/* `line-clamp-1`, not `truncate`: this list lives inside the shared
          `ScrollArea`, whose Viewport renders as `display: table`
          internally — `truncate`'s `white-space: nowrap` forces this
          button's intrinsic width to the full unwrapped preview text,
          overflowing the sidebar (see citation-card.tsx for the full
          writeup of this same bug). `line-clamp-1` clips without `nowrap`. */}
      <p className="line-clamp-1 min-w-0 text-sm text-foreground">{previewLine(artifact.content_markdown)}</p>
    </button>
  );
}
