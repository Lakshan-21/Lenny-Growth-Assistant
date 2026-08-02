"use client";

import { useState } from "react";
import { Wand2 } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { useGenerateShip30 } from "@/hooks/use-generate-ship30";
import { ARTIFACT_TYPE_LABEL, SHIP30_CONTENT_TYPES } from "@/lib/artifact-labels";
import type { Ship30ContentType } from "@/types/domain";

const DEFAULT_INSTRUCTION = "Repurpose this content.";

interface Ship30ActionsProps {
  sessionId: string;
  sourceArtifactId: string;
  onGenerated: () => void;
}

/** "Generate from selected artifact" — turns the open artifact into a LinkedIn post, X thread, or article. */
export function Ship30Actions({ sessionId, sourceArtifactId, onGenerated }: Ship30ActionsProps) {
  const [instruction, setInstruction] = useState(DEFAULT_INSTRUCTION);
  const generate = useGenerateShip30(sessionId);

  const handleGenerate = (contentType: Ship30ContentType) => {
    const trimmed = instruction.trim();
    if (!trimmed) return;
    generate.mutate(
      { instruction: trimmed, contentType, sourceArtifactId },
      { onSuccess: onGenerated },
    );
  };

  return (
    <div className="flex flex-col gap-2 border-t border-border pt-3">
      <p className="flex items-center gap-1.5 text-xs font-medium text-muted-foreground">
        <Wand2 className="size-3.5" aria-hidden="true" />
        Repurpose this with Ship30
      </p>

      <Textarea
        value={instruction}
        onChange={(event) => setInstruction(event.target.value)}
        placeholder="How should it be framed? (optional)"
        rows={2}
        disabled={generate.isPending}
        className="text-xs"
        aria-label="Ship30 instruction"
      />

      <div className="flex flex-wrap gap-1.5">
        {SHIP30_CONTENT_TYPES.map((contentType) => (
          <Button
            key={contentType}
            type="button"
            variant="outline"
            size="sm"
            disabled={generate.isPending || !instruction.trim()}
            onClick={() => handleGenerate(contentType)}
          >
            {generate.isPending && generate.variables?.contentType === contentType
              ? "Generating…"
              : ARTIFACT_TYPE_LABEL[contentType]}
          </Button>
        ))}
      </div>

      {generate.isError && (
        <p className="text-xs text-destructive" role="alert">
          Couldn&apos;t generate that. Check the backend is running and try again.
        </p>
      )}
    </div>
  );
}
