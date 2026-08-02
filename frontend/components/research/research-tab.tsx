import { Lightbulb } from "lucide-react";

import { ArtifactsList } from "@/components/artifacts/artifacts-list";
import { ResearchBriefListItem } from "@/components/research/research-brief-list-item";

interface ResearchTabProps {
  sessionId: string;
}

export function ResearchTab({ sessionId }: ResearchTabProps) {
  return (
    <ArtifactsList
      sessionId={sessionId}
      filterType="research_brief"
      emptyTitle="No research briefs yet."
      emptyDescription='Switch the composer to "Research" mode and ask a question to generate one.'
      emptyIcon={Lightbulb}
      headerNote="Your research workspace — briefs generated in Research mode, with sources and summaries."
      renderItem={(artifact, onOpen) => <ResearchBriefListItem artifact={artifact} onOpen={onOpen} />}
    />
  );
}
