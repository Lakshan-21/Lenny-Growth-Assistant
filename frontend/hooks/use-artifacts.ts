import { useQuery } from "@tanstack/react-query";

import { listArtifacts } from "@/lib/api/artifacts";

export function artifactsQueryKey(sessionId: string) {
  return ["artifacts", sessionId] as const;
}

export function useArtifacts(sessionId: string) {
  return useQuery({
    queryKey: artifactsQueryKey(sessionId),
    queryFn: () => listArtifacts(sessionId),
    enabled: Boolean(sessionId),
  });
}
