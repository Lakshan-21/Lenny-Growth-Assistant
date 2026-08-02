import { apiClient } from "@/lib/api/client";
import type { Artifact } from "@/types/domain";

/**
 * `ArtifactRead` already carries full `content_markdown` — there's no
 * separate "open artifact" fetch here, since the list response has
 * everything a detail view needs. `GET /sessions/{id}/artifacts/{id}`
 * exists on the backend too, but calling it after the list would just
 * refetch data already in hand.
 */
export function listArtifacts(sessionId: string): Promise<Artifact[]> {
  return apiClient.get<Artifact[]>(`/sessions/${sessionId}/artifacts`);
}

/** Raw Markdown, exactly as stored (backend: `PlainTextResponse`, ADR-4). */
export function downloadArtifactMarkdown(sessionId: string, artifactId: string): Promise<string> {
  return apiClient.getText(`/sessions/${sessionId}/artifacts/${artifactId}/download`);
}
