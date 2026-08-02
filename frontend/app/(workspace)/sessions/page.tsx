import { EmptyState } from "@/components/chat/empty-state";

export default function SessionsIndexPage() {
  return (
    <EmptyState
      title="Select a session"
      description="Choose a session from the sidebar, or start a new chat to ask about Lenny's Podcast."
    />
  );
}
