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
  /** Show only this artifact type — used by the Research tab (`"research_brief"`). */
  filterType?: ArtifactType;
  /** Show every type *except* this one — used by the Artifacts tab
   * (`"research_brief"`), so research briefs stay exclusive to the
   * Research tab instead of also appearing here. Deliberately an
   * exclusion rather than an allowlist of ship30 types: any future
   * artifact type (e.g. the currently-unused `"qa_answer"`) is a
   * "generated output" that belongs in Artifacts by default, without
   * needing this list updated for it.
   */
  excludeType?: ArtifactType;
  emptyTitle: string;
  emptyDescription: string;
  /** One-line framing shown above the list — lets a first-time user tell
   * this tab apart from its sibling at a glance, since both read from the
   * same underlying data source (see each tab's wrapper component) even
   * though `filterType`/`excludeType` now make their contents disjoint. */
  headerNote?: string;
  emptyIcon?: LucideIcon;
  /** Row presentation override. Defaults to the generic `ArtifactListItem`
   * (file-preview row) — the Research tab supplies its own to present the
   * same `Artifact` record as a title/summary brief instead. */
  renderItem?: (artifact: Artifact, onOpen: () => void) => ReactNode;
}

/**
 * Shared fetch/sort/select/open state machine for the Artifacts and
 * Research tabs — both read the same underlying `GET /sessions/{id}
 * /artifacts` data, so they share this machinery rather than duplicating
 * it. `filterType`/`excludeType` make the two tabs' *contents* disjoint
 * (Research: only `research_brief`; Artifacts: everything else), and
 * `renderItem`/`emptyIcon`/`headerNote` make them *look* different too.
 */
export function ArtifactsList({
  sessionId,
  filterType,
  excludeType,
  emptyTitle,
  emptyDescription,
  headerNote,
  emptyIcon: EmptyIcon = FileText,
  renderItem,
}: ArtifactsListProps) {
  const { data: artifacts, isLoading, isError } = useArtifacts(sessionId);
  const [selectedId, setSelectedId] = useState<string | null>(null);

  const filtered = (artifacts ?? []).filter(
    (artifact) =>
      (!filterType || artifact.artifact_type === filterType) &&
      (!excludeType || artifact.artifact_type !== excludeType),
  );
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
