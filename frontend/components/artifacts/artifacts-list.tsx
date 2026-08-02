"use client";

import { useState, type ReactNode } from "react";
import { FileText, type LucideIcon } from "lucide-react";

import { ArtifactDetail } from "@/components/artifacts/artifact-detail";
import { ArtifactListItem } from "@/components/artifacts/artifact-list-item";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Skeleton } from "@/components/ui/skeleton";
import { useArtifacts } from "@/hooks/use-artifacts";
import type { Artifact, ArtifactType } from "@/types/domain";

interface ArtifactsListProps {
  sessionId: string;
  filterType?: ArtifactType;
  emptyTitle: string;
  emptyDescription: string;
  /** One-line framing shown above the list — lets a first-time user tell
   * this tab apart from its sibling at a glance, since both currently read
   * the exact same underlying data (see each tab's wrapper component). */
  headerNote?: string;
  emptyIcon?: LucideIcon;
  /** Row presentation override. Defaults to the generic `ArtifactListItem`
   * (file-preview row) — the Research tab supplies its own to present the
   * same `Artifact` record as a title/summary brief instead. */
  renderItem?: (artifact: Artifact, onOpen: () => void) => ReactNode;
}

/**
 * Shared fetch/sort/select/open state machine for the Artifacts and
 * Research tabs — Research is just this same underlying data, filtered to
 * `artifact_type === "research_brief"`, so the two tabs share this
 * machinery rather than duplicating it. `renderItem`/`emptyIcon`/
 * `headerNote` are what let the two tabs *look* different despite sharing
 * a data source and fetch/select logic.
 */
export function ArtifactsList({
  sessionId,
  filterType,
  emptyTitle,
  emptyDescription,
  headerNote,
  emptyIcon: EmptyIcon = FileText,
  renderItem,
}: ArtifactsListProps) {
  const { data: artifacts, isLoading, isError } = useArtifacts(sessionId);
  const [selectedId, setSelectedId] = useState<string | null>(null);

  const filtered = (artifacts ?? []).filter((artifact) => !filterType || artifact.artifact_type === filterType);
  const sorted = [...filtered].sort((a, b) => b.created_at.localeCompare(a.created_at));
  const selected: Artifact | undefined = sorted.find((artifact) => artifact.id === selectedId);

  if (selected) {
    return <ArtifactDetail sessionId={sessionId} artifact={selected} onBack={() => setSelectedId(null)} />;
  }

  if (isLoading) {
    return (
      <div className="flex flex-col gap-2 px-4 pt-4">
        <Skeleton className="h-16 w-full" />
        <Skeleton className="h-16 w-full" />
      </div>
    );
  }

  if (isError) {
    return (
      <p className="px-4 pt-4 text-xs text-destructive" role="alert">
        Couldn&apos;t load artifacts. Try reloading the page.
      </p>
    );
  }

  if (sorted.length === 0) {
    return (
      <div className="flex flex-col items-start gap-2 px-4 pt-4 text-sm text-muted-foreground">
        <EmptyIcon className="size-5 text-muted-foreground" aria-hidden="true" />
        <p>{emptyTitle}</p>
        <p className="text-xs">{emptyDescription}</p>
      </div>
    );
  }

  return (
    <ScrollArea className="h-full px-4 pb-4 pt-4">
      {headerNote && <p className="pb-3 text-xs text-muted-foreground">{headerNote}</p>}
      <ul className="flex flex-col gap-2">
        {sorted.map((artifact) => (
          <li key={artifact.id}>
            {renderItem ? (
              renderItem(artifact, () => setSelectedId(artifact.id))
            ) : (
              <ArtifactListItem artifact={artifact} onOpen={() => setSelectedId(artifact.id)} />
            )}
          </li>
        ))}
      </ul>
    </ScrollArea>
  );
}
