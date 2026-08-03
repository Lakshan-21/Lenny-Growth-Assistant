"use client";

import { useEffect } from "react";
import { useParams } from "next/navigation";

import { ChatInput } from "@/components/chat/chat-input";
import { EmptyState } from "@/components/chat/empty-state";
import { MessageList } from "@/components/chat/message-list";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Skeleton } from "@/components/ui/skeleton";
import { useRightPanel } from "@/hooks/use-right-panel";
import { useSendMessage } from "@/hooks/use-send-message";
import { useSession } from "@/hooks/use-session";

export default function SessionChatPage() {
  const { sessionId } = useParams<{ sessionId: string }>();
  const { data: session, isLoading, isError } = useSession(sessionId);
  const sendMessage = useSendMessage(sessionId);
  const { showCitations, clearCitations: clear, setActiveTab } = useRightPanel();

  // Citations are persisted (`message.citations`, from either a live send
  // or `GET /sessions/{id}` history) — no local cache needed for the data
  // itself. The Sources tab is still reset on session switch for UX
  // reasons (don't show the previous session's sources while this one
  // loads), not because the data would otherwise be unavailable.
  useEffect(() => {
    clear();
    // `clear` is stable (useCallback'd with no deps in the provider) but
    // included for exhaustive-deps correctness.
  }, [sessionId, clear]);

  const handleSend = (content: string, researchMode: boolean) => {
    sendMessage.mutate(
      { content, researchMode },
      {
        onSuccess: (response) => {
          if (response.message.citations.length > 0) {
            showCitations(response.message.id, response.message.citations);
          }
          if (researchMode && response.artifact_id) {
            // Surface the freshly synthesized brief instead of leaving the
            // panel wherever the user last left it.
            setActiveTab("research");
          }
        },
      },
    );
  };

  if (isLoading) {
    return (
      <div className="flex flex-1 flex-col gap-4 px-6 py-6">
        <Skeleton className="h-16 w-2/3" />
        <Skeleton className="ml-auto h-16 w-1/2" />
        <Skeleton className="h-16 w-3/4" />
      </div>
    );
  }

  if (isError || !session) {
    return (
      <EmptyState
        title="Couldn't load this session"
        description="It may not exist, or may belong to a different account."
      />
    );
  }

  return (
    <>
      <header className="flex items-center border-b border-border px-6 py-4">
        <h1 className="truncate text-sm font-semibold">{session.title}</h1>
      </header>

      {/* `&& !sendMessage.isPending`: without it, submitting the very
          first message in a session leaves `session.messages` at `[]`
          (the local session query hasn't refetched yet — that only
          happens in `useSendMessage`'s `onSuccess`), so this branch kept
          rendering `EmptyState` for the whole request -- `MessageList`,
          the only place `ThinkingIndicator` lives, never mounted, so the
          thinking state had nowhere to appear until the response arrived
          and immediately cleared it. From the second message onward this
          never mattered, since `messages.length` was already > 0. */}
      {session.messages.length === 0 && !sendMessage.isPending ? (
        <EmptyState
          title="Ask about Lenny's Podcast"
          description="Ask a question and get a grounded answer with citations from real episodes."
        />
      ) : (
        <ScrollArea className="flex-1">
          <MessageList
            messages={session.messages}
            onViewSources={(messageId, citations) => showCitations(messageId, citations)}
            isSending={sendMessage.isPending}
          />
        </ScrollArea>
      )}

      {sendMessage.isError && (
        <p className="px-6 py-2 text-xs text-destructive" role="alert">
          Couldn&apos;t send that message. Check the backend is running and try again.
        </p>
      )}

      <ChatInput onSend={handleSend} disabled={sendMessage.isPending} />
    </>
  );
}
