"use client";

import { BookOpen } from "lucide-react";

import { CitationCard } from "@/components/citations/citation-card";
import { ScrollArea } from "@/components/ui/scroll-area";
import { useRightPanel } from "@/hooks/use-right-panel";

export function SourcesTab() {
  const { activeCitations } = useRightPanel();

  if (activeCitations.citations.length === 0) {
    return (
      <div className="flex flex-col items-start gap-2 px-4 pt-4 text-sm text-muted-foreground">
        <BookOpen className="size-5 text-muted-foreground" aria-hidden="true" />
        <p>Sources will appear here once an answer cites the podcast.</p>
      </div>
    );
  }

  return (
    <ScrollArea className="h-full px-4 pb-4 pt-4">
      <ol className="flex flex-col gap-3">
        {activeCitations.citations.map((citation, index) => (
          // `CitationRead` has no stable id (see types/domain.ts) — this
          // list is fetched once per active message and never reordered,
          // so an index key is safe here.
          <CitationCard key={index} index={index + 1} citation={citation} />
        ))}
      </ol>
    </ScrollArea>
  );
}
