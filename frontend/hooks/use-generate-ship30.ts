import { useMutation, useQueryClient } from "@tanstack/react-query";

import { sendMessage } from "@/lib/api/skills";
import { artifactsQueryKey } from "@/hooks/use-artifacts";
import { sessionQueryKey } from "@/hooks/use-session";
import { sessionsQueryKey } from "@/hooks/use-sessions";
import type { Ship30ContentType, SkillInvocationResponse } from "@/types/domain";

export interface GenerateShip30Input {
  instruction: string;
  contentType: Ship30ContentType;
  sourceArtifactId: string;
}

/**
 * Ship30 runs through the same `POST /messages` endpoint as QA/Research
 * (manual mode, skill="ship30") — it also appends an assistant chat
 * message on the backend (`skills/router.py` step 6), so a successful
 * generation shows up both as a new Artifact and as a new chat turn.
 */
export function useGenerateShip30(sessionId: string) {
  const queryClient = useQueryClient();

  return useMutation<SkillInvocationResponse, unknown, GenerateShip30Input>({
    mutationFn: ({ instruction, contentType, sourceArtifactId }) =>
      sendMessage(sessionId, instruction, {
        mode: "manual",
        skill: "ship30",
        contentType,
        sourceArtifactId,
      }),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: artifactsQueryKey(sessionId) });
      void queryClient.invalidateQueries({ queryKey: sessionQueryKey(sessionId) });
      void queryClient.invalidateQueries({ queryKey: sessionsQueryKey });
    },
  });
}
