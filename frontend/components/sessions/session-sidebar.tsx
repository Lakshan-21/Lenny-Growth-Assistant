"use client";

import Image from "next/image";
import Link from "next/link";
import { useParams } from "next/navigation";

import { NewSessionButton } from "@/components/sessions/new-session-button";
import { SessionListItem } from "@/components/sessions/session-list-item";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Skeleton } from "@/components/ui/skeleton";
import { useSessions } from "@/hooks/use-sessions";

export function SessionSidebar() {
  const { data: sessions, isLoading, isError } = useSessions();
  const params = useParams<{ sessionId?: string }>();
  const activeSessionId = params?.sessionId;

  return (
    <aside className="flex w-64 shrink-0 flex-col border-r border-border bg-background-sidebar">
      <div className="flex items-center gap-2 px-4 py-4">
        {/* `public/logo.png` (copied from Assets/Logo 1.PNG, unchanged
            pixels — 1254x1254 source) replaces the previous plain colored
            div placeholder. `next/image` needs no extra config for local
            `public/` assets. width/height match the `size-7` CSS box
            exactly (both square, so the aspect ratio can't distort), and
            `object-contain` is a second guard against any future
            container-size change stretching it. Wrapped in a `Link` back
            to `/` (the Hero Landing Page) per the workspace header update
            — the rest of the header's functionality is untouched. */}
        <Link href="/" className="shrink-0 rounded-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background-sidebar">
          <Image
            src="/logo.png"
            alt="Back to Lenny Growth Assistant home"
            width={28}
            height={28}
            className="size-7 shrink-0 rounded-sm object-contain"
          />
        </Link>
        <span className="truncate text-sm font-semibold">Lenny Growth Workspace</span>
      </div>

      <div className="px-3 pb-3">
        <NewSessionButton />
      </div>

      <div className="px-3 pb-2 text-xs font-medium uppercase tracking-wide text-muted-foreground">Sessions</div>

      <ScrollArea className="flex-1 px-3 pb-3">
        {isLoading && (
          <div className="flex flex-col gap-2">
            <Skeleton className="h-11 w-full" />
            <Skeleton className="h-11 w-full" />
            <Skeleton className="h-11 w-full" />
          </div>
        )}

        {isError && <p className="px-3 text-xs text-destructive">Couldn&apos;t load sessions. Try reloading the page.</p>}

        {sessions?.length === 0 && (
          <p className="px-3 text-xs text-muted-foreground">No sessions yet — start one above.</p>
        )}

        <nav className="flex flex-col gap-0.5" aria-label="Sessions">
          {sessions?.map((session) => (
            <SessionListItem key={session.id} session={session} active={session.id === activeSessionId} />
          ))}
        </nav>
      </ScrollArea>
    </aside>
  );
}
