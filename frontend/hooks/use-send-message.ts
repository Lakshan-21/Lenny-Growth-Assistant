import { useMutation, useQueryClient } from "@tanstack/react-query";

import { sendMessage } from "@/lib/api/skills";
import { artifactsQueryKey } from "@/hooks/use-artifacts";
import { sessionQueryKey } from "@/hooks/use-session";
import { sessionsQueryKey } from "@/hooks/use-sessions";
import type { SkillInvocationResponse } from "@/types/domain";

export interface SendMessageInput {
  content: string;
  /** Runs the Research skill (multi-query synthesis) instead of QA — see the composer's mode toggle. */
  researchMode?: boolean;
}

/**
 * On success, refetches the session detail (rather than hand-crafting an
 * optimistic cache update) — the response only carries the assistant's
 * message, not a server-assigned id/timestamp for the just-sent user
 * message, so a full refetch is the simplest way to end up with a
 * correct, server-truthful message list. Also invalidates the sidebar
 * list (a first message auto-titles the session and bumps recency) and
 * the artifacts list (Research runs always produce a research_brief
 * artifact — see backend `skills/router.py` step 7) so the Artifacts/
 * Research tabs auto-refresh without a manual reload.
 */
export function useSendMessage(sessionId: string) {
  const queryClient = useQueryClient();

  return useMutation<SkillInvocationResponse, unknown, SendMessageInput>({
    mutationFn: ({ content, researchMode }) =>
      sendMessage(sessionId, content, researchMode ? { mode: "manual", skill: "research" } : {}),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: sessionQueryKey(sessionId) });
      void queryClient.invalidateQueries({ queryKey: sessionsQueryKey });
      void queryClient.invalidateQueries({ queryKey: artifactsQueryKey(sessionId) });
    },
  });
}
