import { useQuery } from "@tanstack/react-query";

import { getSession } from "@/lib/api/sessions";

export function sessionQueryKey(sessionId: string) {
  return ["session", sessionId] as const;
}

export function useSession(sessionId: string) {
  return useQuery({
    queryKey: sessionQueryKey(sessionId),
    queryFn: () => getSession(sessionId),
    enabled: Boolean(sessionId),
  });
}
