"use client";

import { useRouter } from "next/navigation";
import { Plus } from "lucide-react";

import { Button } from "@/components/ui/button";
import { useCreateSession } from "@/hooks/use-sessions";

export function NewSessionButton() {
  const router = useRouter();
  const createSession = useCreateSession();

  const handleClick = () => {
    // Title is derived server-side from the first message (PRD §6.2) —
    // no title-entry form needed here.
    createSession.mutate(null, {
      onSuccess: (session) => router.push(`/sessions/${session.id}`),
    });
  };

  return (
    <Button
      onClick={handleClick}
      disabled={createSession.isPending}
      className="w-full justify-start"
      variant="default"
    >
      <Plus />
      {createSession.isPending ? "Creating…" : "New chat"}
    </Button>
  );
}
