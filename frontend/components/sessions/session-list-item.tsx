"use client";

import Link from "next/link";

import { cn, formatRelativeTime } from "@/lib/utils";
import type { SessionListItem as SessionListItemType } from "@/types/domain";

interface SessionListItemProps {
  session: SessionListItemType;
  active: boolean;
}

export function SessionListItem({ session, active }: SessionListItemProps) {
  return (
    <Link
      href={`/sessions/${session.id}`}
      className={cn(
        "group flex flex-col gap-0.5 rounded-md px-3 py-2 text-sm transition-colors",
        active ? "bg-accent-soft text-foreground" : "text-foreground/80 hover:bg-muted",
      )}
      aria-current={active ? "page" : undefined}
    >
      <span className="truncate font-medium">{session.title}</span>
      <span className="truncate text-xs text-muted-foreground">{formatRelativeTime(session.updated_at)}</span>
    </Link>
  );
}
