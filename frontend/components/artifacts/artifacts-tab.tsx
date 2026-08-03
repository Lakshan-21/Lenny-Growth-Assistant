import { ArtifactsList } from "@/components/artifacts/artifacts-list";

interface ArtifactsTabProps {
  sessionId: string;
}

export function ArtifactsTab({ sessionId }: ArtifactsTabProps) {
  return (
    <ArtifactsList
      sessionId={sessionId}
      excludeType="research_brief"
      emptyTitle="No artifacts yet."
      emptyDescription="Ship30 posts (LinkedIn, X threads, articles) you generate will show up here."
      headerNote="Generated deliverables from this session — open any to read, download, or repurpose it."
    />
  );
}
