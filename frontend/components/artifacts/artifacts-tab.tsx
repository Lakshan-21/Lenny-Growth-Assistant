import { ArtifactsList } from "@/components/artifacts/artifacts-list";

interface ArtifactsTabProps {
  sessionId: string;
}

export function ArtifactsTab({ sessionId }: ArtifactsTabProps) {
  return (
    <ArtifactsList
      sessionId={sessionId}
      emptyTitle="No artifacts yet."
      emptyDescription="Research briefs and Ship30 posts you generate will show up here."
      headerNote="Deliverables from this session — open any to read, download, or repurpose it."
    />
  );
}
