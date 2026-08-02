"use client";

import { useEffect, useRef } from "react";

import { MessageBubble } from "@/components/chat/message-bubble";
import type { CitationRead, Message } from "@/types/domain";

interface MessageListProps {
  messages: Message[];
  onViewSources: (messageId: string, citations: CitationRead[]) => void;
  isSending: boolean;
}

export function MessageList({ messages, onViewSources, isSending }: MessageListProps) {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [messages.length, isSending]);

  return (
    <div className="flex flex-col gap-6 px-6 py-6">
      {messages
        .filter((message) => message.role !== "system")
        .map((message) => (
          <MessageBubble
            key={message.id}
            message={message}
            onViewSources={() => onViewSources(message.id, message.citations)}
          />
        ))}

      {isSending && <ThinkingIndicator />}

      <div ref={bottomRef} />
    </div>
  );
}

function ThinkingIndicator() {
  return (
    <div className="flex items-center gap-2 pl-10 text-sm text-muted-foreground" role="status" aria-live="polite">
      <span className="flex gap-1">
        <span className="size-1.5 animate-pulse-soft rounded-full bg-accent [animation-delay:0ms]" />
        <span className="size-1.5 animate-pulse-soft rounded-full bg-accent [animation-delay:150ms]" />
        <span className="size-1.5 animate-pulse-soft rounded-full bg-accent [animation-delay:300ms]" />
      </span>
      Thinking…
    </div>
  );
}
