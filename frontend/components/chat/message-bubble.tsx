"use client";

import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { BookOpen } from "lucide-react";

import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import type { Message } from "@/types/domain";

interface MessageBubbleProps {
  message: Message;
  onViewSources?: () => void;
}

const SKILL_LABEL: Partial<Record<NonNullable<Message["skill_used"]>, string>> = {
  qa: "Q&A",
  research: "Research",
  ship30: "Ship30",
  artifact: "Artifact",
};

/**
 * Assistant messages render like a document (no bubble box) — Claude's
 * own chat reads this way, and it suits long, cited answers better than
 * a chat-bubble box would. User messages get a soft bubble for contrast,
 * right-aligned.
 */
export function MessageBubble({ message, onViewSources }: MessageBubbleProps) {
  const isUser = message.role === "user";

  if (message.role === "system") {
    // Router/skill breadcrumbs are not user-facing in Phase 1.
    return null;
  }

  return (
    <div className={cn("flex gap-3", isUser && "flex-row-reverse")}>
      <Avatar className={isUser ? "bg-user-bubble" : "bg-accent-soft"}>
        <AvatarFallback className={isUser ? "text-foreground" : "text-accent"}>{isUser ? "You" : "L"}</AvatarFallback>
      </Avatar>

      <div className={cn("flex max-w-[42rem] flex-col gap-1.5", isUser && "items-end")}>
        {!isUser && message.skill_used && (
          <Badge variant="soft">{SKILL_LABEL[message.skill_used] ?? message.skill_used}</Badge>
        )}

        <div className={cn("rounded-lg", isUser ? "bg-user-bubble px-4 py-2.5" : "px-0 py-0")}>
          <div className="markdown-body">
            <ReactMarkdown remarkPlugins={[remarkGfm]}>{message.content}</ReactMarkdown>
          </div>
        </div>

        {message.citations.length > 0 && (
          <Button variant="outline" size="sm" onClick={onViewSources} className="mt-0.5">
            <BookOpen />
            {message.citations.length === 1 ? "1 source" : `${message.citations.length} sources`}
          </Button>
        )}
      </div>
    </div>
  );
}
