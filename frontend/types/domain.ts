/**
 * Types mirroring the backend's Pydantic schemas 1:1 — see
 * `backend/app/domains/sessions/schemas.py` and
 * `backend/app/domains/skills/schemas.py`. Field names/shapes are kept
 * identical on purpose so this file stays a direct, low-friction map back
 * to the API contract, not a reinterpretation of it.
 */

export type MessageRole = "user" | "assistant" | "system";

export type SkillType = "qa" | "research" | "ship30" | "artifact";

export type RoutingMode = "auto" | "manual";

export type ArtifactType = "qa_answer" | "research_brief" | "linkedin_post" | "x_thread" | "article";

export type Ship30ContentType = Extract<ArtifactType, "linkedin_post" | "x_thread" | "article">;

/**
 * A citation as embedded in message history (`Message.citations`) — the
 * backend's `sessions.schemas.CitationRead`. Deliberately smaller than
 * `CitationRef` below (no `transcript_chunk_id`): it only ever appears
 * nested inside a message the client already has an id for.
 */
export interface CitationRead {
  display_label: string;
  excerpt: string;
}

export interface Message {
  id: string;
  session_id: string;
  role: MessageRole;
  content: string;
  skill_used: SkillType | null;
  created_at: string;
  /** Persisted — populated for both a live send and `GET /sessions/{id}` history. */
  citations: CitationRead[];
}

export interface SessionListItem {
  id: string;
  title: string;
  updated_at: string;
}

export interface SessionDetail {
  id: string;
  user_id: string;
  title: string;
  created_at: string;
  updated_at: string;
  messages: Message[];
}

export interface CitationRef {
  transcript_chunk_id: string;
  display_label: string;
  excerpt: string;
}

export interface SkillInvocationResponse {
  skill_used: SkillType | null;
  routing_mode: RoutingMode;
  message: Message;
  citations: CitationRef[];
  artifact_id: string | null;
}

export interface Artifact {
  id: string;
  session_id: string;
  message_id: string;
  artifact_type: ArtifactType;
  content_markdown: string;
  created_at: string;
}

export interface ApiErrorBody {
  error_code: string;
  message: string;
}
