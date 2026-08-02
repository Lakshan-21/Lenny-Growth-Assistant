import { apiClient } from "@/lib/api/client";
import type { SessionDetail, SessionListItem } from "@/types/domain";

export function listSessions(): Promise<SessionListItem[]> {
  return apiClient.get<SessionListItem[]>("/sessions");
}

export function getSession(sessionId: string): Promise<SessionDetail> {
  return apiClient.get<SessionDetail>(`/sessions/${sessionId}`);
}

export function createSession(title: string | null = null): Promise<SessionDetail> {
  return apiClient.post<SessionDetail>("/sessions", { title });
}
