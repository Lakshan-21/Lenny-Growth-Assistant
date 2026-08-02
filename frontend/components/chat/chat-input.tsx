"use client";

import { useState, type FormEvent, type KeyboardEvent } from "react";
import { ArrowUp } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { cn } from "@/lib/utils";

interface ChatInputProps {
  onSend: (content: string, researchMode: boolean) => void;
  disabled?: boolean;
}

export function ChatInput({ onSend, disabled }: ChatInputProps) {
  const [value, setValue] = useState("");
  const [researchMode, setResearchMode] = useState(false);

  const submit = () => {
    const trimmed = value.trim();
    if (!trimmed || disabled) return;
    onSend(trimmed, researchMode);
    setValue("");
  };

  const handleSubmit = (event: FormEvent) => {
    event.preventDefault();
    submit();
  };

  const handleKeyDown = (event: KeyboardEvent<HTMLTextAreaElement>) => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      submit();
    }
  };

  return (
    <form onSubmit={handleSubmit} className="flex flex-col gap-2 border-t border-border bg-background px-6 py-4">
      <div
        className="inline-flex w-fit items-center gap-1 self-start rounded-md bg-muted p-1"
        role="radiogroup"
        aria-label="Composer mode"
      >
        <button
          type="button"
          role="radio"
          aria-checked={!researchMode}
          onClick={() => setResearchMode(false)}
          className={cn(
            "rounded-sm px-2.5 py-1 text-xs font-medium transition-colors",
            !researchMode ? "bg-card text-foreground shadow-sm" : "text-muted-foreground",
          )}
        >
          Ask
        </button>
        <button
          type="button"
          role="radio"
          aria-checked={researchMode}
          onClick={() => setResearchMode(true)}
          className={cn(
            "rounded-sm px-2.5 py-1 text-xs font-medium transition-colors",
            researchMode ? "bg-card text-foreground shadow-sm" : "text-muted-foreground",
          )}
        >
          Research
        </button>
      </div>

      <div className="flex items-end gap-2">
        <Textarea
          value={value}
          onChange={(event) => setValue(event.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={researchMode ? "What topic should it research across episodes?" : "Ask about the podcast…"}
          rows={1}
          disabled={disabled}
          className="max-h-40 min-h-10"
          aria-label="Message"
        />
        <Button type="submit" size="icon" disabled={disabled || !value.trim()} aria-label="Send message">
          <ArrowUp />
        </Button>
      </div>
    </form>
  );
}
