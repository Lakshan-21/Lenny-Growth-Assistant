import Image from "next/image";
import Link from "next/link";
import { FileText, MessageCircle, Search, Sparkles } from "lucide-react";

import { Button } from "@/components/ui/button";

const CAPABILITIES = [
  {
    icon: MessageCircle,
    title: "Ask questions",
    description: "Get grounded answers with citations from real episodes.",
  },
  {
    icon: Search,
    title: "Research topics",
    description: "Cross-episode research synthesized into structured briefs.",
  },
  {
    icon: FileText,
    title: "Generate content",
    description: "Repurpose findings into LinkedIn posts, threads, and articles.",
  },
  {
    icon: Sparkles,
    title: "Discover growth insights",
    description: "Surface the frameworks and tactics buried in the archive.",
  },
] as const;

export function HeroLanding() {
  return (
    <div className="flex min-h-dvh flex-col items-center bg-background px-6 py-16">
      <div className="flex w-full max-w-3xl flex-1 flex-col items-center justify-center text-center">
        <Image
          src="/logo.png"
          alt="Lenny Growth Assistant logo"
          width={72}
          height={72}
          priority
          className="size-16 shrink-0 rounded-xl object-contain sm:size-[72px]"
        />

        <p className="mt-4 text-sm font-semibold uppercase tracking-wide text-accent">
          Lenny Growth Assistant
        </p>

        <h1 className="mt-4 text-balance text-3xl font-semibold leading-tight text-foreground sm:text-4xl md:text-5xl">
          Your AI growth partner, trained on Lenny&apos;s Podcast
        </h1>

        <p className="mt-5 max-w-xl text-balance text-base leading-relaxed text-muted-foreground sm:text-lg">
          Ask questions, research topics, generate content, create artifacts, and discover growth
          insights — all grounded in real conversations from Lenny&apos;s Podcast.
        </p>

        <Button asChild size="default" className="mt-8 h-12 px-8 text-base font-medium">
          <Link href="/sessions">Go To Chat</Link>
        </Button>

        <div className="mt-16 grid w-full grid-cols-1 gap-4 sm:grid-cols-2">
          {CAPABILITIES.map(({ icon: Icon, title, description }) => (
            <div
              key={title}
              className="flex flex-col items-start gap-2 rounded-lg border border-border bg-card p-5 text-left"
            >
              <div className="flex size-9 shrink-0 items-center justify-center rounded-md bg-accent-soft">
                <Icon className="size-4 text-accent" aria-hidden="true" />
              </div>
              <p className="text-sm font-semibold text-foreground">{title}</p>
              <p className="text-sm text-muted-foreground">{description}</p>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
