"use client";

import { createContext, useCallback, useContext, useMemo, useState } from "react";

import type { CitationRead } from "@/types/domain";

export type RightPanelTab = "sources" | "artifacts" | "research";

interface CitationPanelState {
  messageId: string | null;
  citations: CitationRead[];
}

interface RightPanelContextValue {
  activeTab: RightPanelTab;
  setActiveTab: (tab: RightPanelTab) => void;
  activeCitations: CitationPanelState;
  showCitations: (messageId: string, citations: CitationRead[]) => void;
  clearCitations: () => void;
}

const EMPTY_CITATIONS: CitationPanelState = { messageId: null, citations: [] };

const RightPanelContext = createContext<RightPanelContextValue | null>(null);

/**
 * Bridges right-panel state (which of the 3 tabs is active, plus which
 * message's citations the Sources tab is currently showing) between the
 * chat page — which knows about messages as they arrive from
 * `POST /messages`, and triggers skill runs that should surface a
 * particular tab — and the workspace layout's `<RightPanel />`, a
 * sibling in the App Router tree, not a child of the page, so plain
 * prop-drilling doesn't reach it.
 *
 * Citations themselves are persisted and come from `message.citations`
 * on whichever `Message` is active (both `POST /messages` and
 * `GET /sessions/{id}` return them — see backend
 * `sessions/schemas.py::CitationRead`), so this state resets on session
 * switch for UX reasons (don't show the previous session's sources) —
 * see `[sessionId]/page.tsx` — not because the data would be unavailable
 * otherwise.
 */
export function RightPanelProvider({ children }: { children: React.ReactNode }) {
  const [activeTab, setActiveTab] = useState<RightPanelTab>("sources");
  const [activeCitations, setActiveCitations] = useState<CitationPanelState>(EMPTY_CITATIONS);

  const showCitations = useCallback((messageId: string, citations: CitationRead[]) => {
    setActiveCitations({ messageId, citations });
    setActiveTab("sources");
  }, []);

  const clearCitations = useCallback(() => {
    setActiveCitations(EMPTY_CITATIONS);
  }, []);

  const value = useMemo<RightPanelContextValue>(
    () => ({ activeTab, setActiveTab, activeCitations, showCitations, clearCitations }),
    [activeTab, activeCitations, showCitations, clearCitations],
  );

  return <RightPanelContext.Provider value={value}>{children}</RightPanelContext.Provider>;
}

export function useRightPanel(): RightPanelContextValue {
  const ctx = useContext(RightPanelContext);
  if (!ctx) {
    throw new Error("useRightPanel must be used within a RightPanelProvider");
  }
  return ctx;
}
