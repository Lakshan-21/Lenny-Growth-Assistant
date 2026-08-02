import type { CitationRead } from "@/types/domain";

interface CitationCardProps {
  index: number;
  citation: CitationRead;
}

/**
 * Excerpt text is set in the serif face (see app/globals.css) — the one
 * place this app quotes source material verbatim, styled distinctly from
 * the sans-serif UI chrome around it.
 */
export function CitationCard({ index, citation }: CitationCardProps) {
  return (
    // `line-clamp-1`, not `truncate`, on the label below: `truncate` sets
    // `white-space: nowrap`, and this list lives inside the shared
    // `ScrollArea` (Radix), whose Viewport wrapper renders as `display:
    // table` internally. A `display: table` box's width is computed from
    // its content's *unwrapped* natural width, so a nowrap descendant here
    // forced the whole card to grow past the sidebar's width — `min-w-0`
    // on ancestors doesn't stop that, since table auto-sizing isn't a flex
    // shrink. `line-clamp-1` clips to one line via `-webkit-line-clamp`
    // instead of `nowrap`, so it doesn't feed an inflated width back into
    // the table measurement. This was the actual cause of the excerpt text
    // looking clipped: the whole card (not just the label) was overflowing
    // off the right edge of the sidebar.
    <li className="min-w-0 rounded-md border border-border bg-card p-2.5">
      <div className="flex items-start gap-2">
        <span
          className="mt-0.5 flex size-5 shrink-0 items-center justify-center rounded-full bg-accent text-[0.6875rem] font-semibold text-accent-foreground"
          aria-hidden="true"
        >
          {index}
        </span>
        <div className="flex min-w-0 flex-1 flex-col gap-1.5">
          <p className="line-clamp-1 text-xs font-medium text-muted-foreground">{citation.display_label}</p>
          <p className="text-balance font-serif text-[0.9375rem] italic leading-snug text-foreground">
            &ldquo;{citation.excerpt}&rdquo;
          </p>
        </div>
      </div>
    </li>
  );
}
