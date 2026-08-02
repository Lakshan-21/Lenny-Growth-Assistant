import type { ArtifactType, Ship30ContentType } from "@/types/domain";

export const ARTIFACT_TYPE_LABEL: Record<ArtifactType, string> = {
  qa_answer: "Q&A",
  research_brief: "Research brief",
  linkedin_post: "LinkedIn post",
  x_thread: "X thread",
  article: "Article",
};

export const SHIP30_CONTENT_TYPES: readonly Ship30ContentType[] = ["linkedin_post", "x_thread", "article"];
