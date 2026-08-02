"use client";

import { useParams } from "next/navigation";

import { ArtifactsTab } from "@/components/artifacts/artifacts-tab";
import { SourcesTab } from "@/components/citations/sources-tab";
import { ResearchTab } from "@/components/research/research-tab";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { useRightPanel, type RightPanelTab } from "@/hooks/use-right-panel";

export function RightPanel() {
  const { activeTab, setActiveTab } = useRightPanel();
  const params = useParams<{ sessionId?: string }>();
  const sessionId = params?.sessionId ?? null;

  return (
    <aside className="flex w-80 shrink-0 flex-col border-l border-border bg-background-sidebar">
      <Tabs
        value={activeTab}
        onValueChange={(value: string) => setActiveTab(value as RightPanelTab)}
        className="flex min-h-0 flex-1 flex-col"
      >
        <div className="px-4 pt-4">
          <TabsList className="w-full">
            <TabsTrigger value="sources">Sources</TabsTrigger>
            <TabsTrigger value="artifacts">Artifacts</TabsTrigger>
            <TabsTrigger value="research">Research</TabsTrigger>
          </TabsList>
        </div>

        {!sessionId ? (
          <p className="px-4 pt-4 text-sm text-muted-foreground">Select a session to see its sources and artifacts.</p>
        ) : (
          <>
            <TabsContent value="sources" className="flex min-h-0 flex-col pt-2">
              <SourcesTab />
            </TabsContent>
            <TabsContent value="artifacts" className="flex min-h-0 flex-col pt-2">
              <ArtifactsTab sessionId={sessionId} />
            </TabsContent>
            <TabsContent value="research" className="flex min-h-0 flex-col pt-2">
              <ResearchTab sessionId={sessionId} />
            </TabsContent>
          </>
        )}
      </Tabs>
    </aside>
  );
}
