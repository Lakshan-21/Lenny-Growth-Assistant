import { RightPanel } from "@/components/right-panel/right-panel";
import { SessionSidebar } from "@/components/sessions/session-sidebar";
import { RightPanelProvider } from "@/hooks/use-right-panel";

/**
 * The fixed three-pane shell: left sidebar (sessions), center (the routed
 * chat page), right (Sources / Artifacts / Research tabs) — see README
 * "Layout" for the rationale. `RightPanelProvider` bridges state between
 * the chat page (which knows about messages/citations as they arrive,
 * and triggers skill runs that should surface a particular tab) and this
 * layout's `<RightPanel />` (a sibling, not a child, of the page — React
 * context is the standard way to share state across that boundary in the
 * App Router).
 */
export default function WorkspaceLayout({ children }: { children: React.ReactNode }) {
  return (
    <RightPanelProvider>
      <div className="flex h-dvh w-full overflow-hidden bg-background">
        <SessionSidebar />
        <main className="flex min-w-0 flex-1 flex-col">{children}</main>
        <RightPanel />
      </div>
    </RightPanelProvider>
  );
}
