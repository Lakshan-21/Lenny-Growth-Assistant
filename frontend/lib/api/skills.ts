import { apiClient } from "@/lib/api/client";
import type { RoutingMode, Ship30ContentType, SkillInvocationResponse, SkillType } from "@/types/domain";

export interface SendMessageOptions {
  /** Defaults to "auto" (QA), matching the backend default — Phase 1 behavior. */
  mode?: RoutingMode;
  /** Required when `mode: "manual"`. */
  skill?: SkillType;
  /** Required when `skill: "ship30"`. */
  contentType?: Ship30ContentType;
  /** Optional, ship30-only — falls back to the session's last assistant message. */
  sourceArtifactId?: string;
}

/**
 * `content` doubles as the QA/Research question or the Ship30 "how do you
 * want this framed" instruction, depending on `options.skill` — mirrors
 * `SkillInvocationRequest` (backend `skills/schemas.py`) exactly.
 */
export function sendMessage(
  sessionId: string,
  content: string,
  options: SendMessageOptions = {},
): Promise<SkillInvocationResponse> {
  return apiClient.post<SkillInvocationResponse>(`/sessions/${sessionId}/messages`, {
    content,
    mode: options.mode ?? "auto",
    skill: options.skill ?? null,
    content_type: options.contentType ?? null,
    source_artifact_id: options.sourceArtifactId ?? null,
  });
}
