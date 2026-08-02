"use client";

import { useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { ArrowLeft, Download } from "lucide-react";

import { Ship30Actions } from "@/components/artifacts/ship30-actions";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import { downloadArtifactMarkdown } from "@/lib/api/artifacts";
import { ARTIFACT_TYPE_LABEL } from "@/lib/artifact-labels";
import { formatRelativeTime } from "@/lib/utils";
import type { Artifact } from "@/types/domain";

interface ArtifactDetailProps {
  sessionId: string;
  artifact: Artifact;
  onBack: () => void;
}

function triggerBrowserDownload(filename: string, content: string) {
  const blob = new Blob([content], { type: "text/markdown;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  link.click();
  URL.revokeObjectURL(url);
}

export function ArtifactDetail({ sessionId, artifact, onBack }: ArtifactDetailProps) {
  const [isDownloading, setIsDownloading] = useState(false);
  const [downloadError, setDownloadError] = useState(false);

  const handleDownload = async () => {
    setDownloadError(false);
    setIsDownloading(true);
    try {
      const markdown = await downloadArtifactMarkdown(sessionId, artifact.id);
      triggerBrowserDownload(`${artifact.artifact_type}-${artifact.id.slice(0, 8)}.md`, markdown);
    } catch {
      setDownloadError(true);
    } finally {
      setIsDownloading(false);
    }
  };

  return (
    <div className="flex h-full flex-col">
      <div className="flex items-center justify-between gap-2 px-4 pt-4">
        <Button variant="ghost" size="sm" onClick={onBack}>
          <ArrowLeft />
          Back
        </Button>
        <Button variant="outline" size="sm" onClick={handleDownload} disabled={isDownloading}>
          <Download />
          {isDownloading ? "Downloading…" : "Download"}
        </Button>
      </div>

      <div className="flex flex-col gap-1 px-4 pt-3">
        <div className="flex items-center gap-2">
          <Badge variant="soft">{ARTIFACT_TYPE_LABEL[artifact.artifact_type]}</Badge>
          <span className="text-xs text-muted-foreground">{formatRelativeTime(artifact.created_at)}</span>
        </div>
        {downloadError && (
          <p className="text-xs text-destructive" role="alert">
            Couldn&apos;t download this artifact. Try again.
          </p>
        )}
      </div>

      <ScrollArea className="min-h-0 flex-1 px-4 py-3">
        <div className="markdown-body pb-3">
          <ReactMarkdown remarkPlugins={[remarkGfm]}>{artifact.content_markdown}</ReactMarkdown>
        </div>

        <Ship30Actions sessionId={sessionId} sourceArtifactId={artifact.id} onGenerated={onBack} />
      </ScrollArea>
    </div>
  );
}
