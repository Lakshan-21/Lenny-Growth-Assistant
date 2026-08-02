import { Lightbulb } from "lucide-react";

import { parseResearchBriefPreview } from "@/lib/research-brief-preview";
import { formatRelativeTime } from "@/lib/utils";
import type { Artifact } from "@/types/domain";

interface ResearchBriefListItemProps {
  artifact: Artifact;
  onOpen: () => void;
}

/**
 * Research's own row presentation — title, summary, and source count —
 * distinct from Artifacts' generic file-preview row
 * (`artifact-list-item.tsx`), even though both read the same underlying
 * `Artifact` record. This is the visual half of the Research/Artifacts
 * distinction; `research-tab.tsx` supplies this as `ArtifactsList`'s
 * `renderItem`.
 */
export function ResearchBriefListItem({ artifact, onOpen }: ResearchBriefListItemProps) {
  const { title, summary, sourceCount } = parseResearchBriefPreview(artifact.content_markdown);

  return (
    <button
      type="button"
      onClick={onOpen}
      className="flex min-w-0 w-full flex-col gap-1.5 rounded-md border border-border bg-card p-3 text-left transition-colors hover:bg-muted"
    >
      <div className="flex min-w-0 items-start gap-2">
        <Lightbulb className="mt-0.5 size-4 shrink-0 text-accent" aria-hidden="true" />
        <p className="line-clamp-2 min-w-0 text-sm font-medium text-foreground">{title}</p>
      </div>
      {summary && <p className="line-clamp-2 text-xs text-muted-foreground">{summary}</p>}
      <div className="flex items-center justify-between gap-2 pt-0.5">
        <span className="text-xs text-muted-foreground">
          {sourceCount > 0 ? `${sourceCount} source${sourceCount === 1 ? "" : "s"}` : "No sources"}
        </span>
        <span className="text-xs text-muted-foreground">{formatRelativeTime(artifact.created_at)}</span>
      </div>
    </button>
  );
}
