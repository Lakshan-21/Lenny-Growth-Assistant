import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { createSession, listSessions } from "@/lib/api/sessions";
import type { SessionDetail } from "@/types/domain";

export const sessionsQueryKey = ["sessions"] as const;

export function useSessions() {
  return useQuery({
    queryKey: sessionsQueryKey,
    queryFn: listSessions,
  });
}

export function useCreateSession() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (title: string | null = null) => createSession(title),
    onSuccess: (session: SessionDetail) => {
      // The sidebar list and this new session's own detail cache both
      // need to reflect it — invalidate the list (cheap, infrequent) and
      // seed the detail cache directly (avoids an immediate refetch of
      // data we already have in hand).
      void queryClient.invalidateQueries({ queryKey: sessionsQueryKey });
      queryClient.setQueryData(["session", session.id], session);
    },
  });
}
