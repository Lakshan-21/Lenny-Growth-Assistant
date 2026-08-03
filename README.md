# Lenny Growth Assistant

**A grounded, citation-first RAG workspace over Lenny's Podcast — ask questions, synthesize cross-episode research, and repurpose insights into publishable content, with a local-first LLM stack and graceful cloud fallback.**

[![Backend](https://img.shields.io/badge/backend-FastAPI-009688)](backend/) [![Frontend](https://img.shields.io/badge/frontend-Next.js%2015-black)](frontend/) [![DB](https://img.shields.io/badge/database-PostgreSQL%20%2B%20pgvector-336791)](docs/DATABASE_SCHEMA.md) [![LLM](https://img.shields.io/badge/LLM-Ollama%20%E2%86%92%20Claude-orange)](#llm-architecture) [![License](https://img.shields.io/badge/license-portfolio%2Ftake--home-lightgrey)](#license)

> **A note on how this README is written.** Every claim below was verified by reading the actual source in this repository. This document describes the system as it runs today, not an aspirational plan.

---

## Table of Contents

- [Executive Summary](#executive-summary)
- [Problem Statement](#problem-statement)
- [Solution Overview](#solution-overview)
- [Key Features](#key-features)
- [Product Walkthrough](#product-walkthrough)
- [System Architecture](#system-architecture)
- [Frontend Architecture](#frontend-architecture)
- [Backend Architecture](#backend-architecture)
- [Agentic Architecture](#agentic-architecture)
- [Knowledge & Retrieval Pipeline](#knowledge--retrieval-pipeline)
- [Research Engine](#research-engine)
- [Artifact Generation](#artifact-generation)
- [Database Schema](#database-schema)
- [API Documentation](#api-documentation)
- [LLM Architecture](#llm-architecture)
- [Local Setup](#local-setup)
- [Environment Variables](#environment-variables)
- [Installation](#installation)
- [Running Backend](#running-backend)
- [Running Frontend](#running-frontend)
- [Running Ollama](#running-ollama)
- [Running PostgreSQL](#running-postgresql)
- [Example Workflows](#example-workflows)
- [Design Decisions](#design-decisions)
- [Tradeoffs](#tradeoffs)
- [Performance Optimizations](#performance-optimizations)
- [Implemented Features](#implemented-features)
- [Future Improvements](#future-improvements)
- [Screenshots](#screenshots)
- [Agent Transcripts](#agent-transcripts)
- [License](#license)

---

## Executive Summary

Lenny Growth Assistant is a full-stack retrieval-augmented generation (RAG) application built over the complete transcript archive of **Lenny's Podcast** (303 episodes with product leaders and growth experts). It lets a user open a chat-style workspace, ask a question and get a **citation-backed answer** grounded strictly in retrieved transcript excerpts, escalate that into a **multi-episode research brief**, and **repurpose** either into a LinkedIn post, X/Twitter thread, or long-form article — all persisted as session history and downloadable artifacts.

The system is a vertical-slice FastAPI backend (Python 3.12, SQLAlchemy 2.0 async, PostgreSQL + `pgvector`) paired with a Next.js 15 / React 19 / TypeScript frontend, backed by a **local-first model layer**: `bge-m3` embeddings and `llama3.1` generation served through **Ollama**, with **Anthropic Claude** wired in as an automatic fallback provider if Ollama is unreachable.

What makes this project worth a closer read isn't the feature list — it's the discipline in the small things: an empirically-tuned cosine-distance cutoff that stops the retriever from confidently citing irrelevant chunks, a second grounding check *after* generation (not just before) that catches a model willing to answer from a topically-adjacent-but-wrong excerpt, and a GPU-placement fix for Ollama that eliminates a measured ~14s reload penalty every single request. These are documented in the code as they were discovered, not smoothed over after the fact.

## Problem Statement

Lenny's Podcast has published hundreds of hours of dense, tactical advice from product and growth operators. That knowledge is:

- **Hard to search** — locked in unstructured audio/transcript form, no semantic search.
- **Hard to synthesize** — a topic like "activation metrics" is scattered across dozens of episodes with no way to compare or reconcile what different guests actually said.
- **Hard to reuse** — turning a podcast insight into a LinkedIn post or thread means manually re-listening, extracting, and rewriting.

There was no tool that let a user ask a grounded question against the corpus, get an answer they could actually trust (because it's traceable to a specific episode and timestamp), escalate it into structured research, and then transform it into ready-to-publish content — in one continuous, session-persisted workflow.

## Solution Overview

Lenny Growth Assistant answers this with three composable capabilities layered over one shared retrieval pipeline:

1. **QA** — ask a direct question, get a grounded answer with inline `[1][2]` citations resolving to exact episode + timestamp + excerpt.
2. **Research** — ask a broader topic, get a multi-section brief synthesized across multiple episodes, with per-episode source grouping.
3. **Ship30** — take any prior QA answer or research brief and transform it into a LinkedIn post, X thread, or article, formatted to that platform's real constraints.

Every one of these three skills refuses to fabricate: both QA and Research independently enforce a two-stage grounding check (a similarity-distance cutoff at retrieval time, plus an explicit "this doesn't actually answer the question" escape hatch the model itself can invoke) and would rather tell the user "I don't have enough information" than produce a confident, unsupported answer.

## Key Features

| Feature | Description |
|---|---|
| **Grounded Q&A** | Retrieval-augmented answers over 303 real podcast episodes, every claim traceable to a citation. |
| **Insufficient-evidence enforcement** | A shared sentinel (`INSUFFICIENT_EVIDENCE_MARKER`) the model must emit instead of guessing — checked verbatim in both QA and Research, post-generation. |
| **Cross-episode research briefs** | Query expansion into multiple sub-queries, retrieval across all of them, dedup, and synthesis into a 4-section structured brief. |
| **Ship30 content repurposing** | LinkedIn post / X thread / article generation from any existing artifact, with format-specific post-processing (character limits, thread segmentation). |
| **Session-based workspace** | Every conversation is a persisted session with full message history, auto-titled from the first message. |
| **Artifact system** | Research briefs and Ship30 outputs persist as first-class, downloadable Markdown artifacts, separate from the chat transcript. |
| **Sanitized HTML rendering** | Artifacts can render as HTML via an allowlist-based sanitizer (`nh3`/Rust `ammonia`) — not just raw Markdown passthrough. |
| **Local-first LLM with graceful degradation** | Ollama is the primary generation/embedding provider; Claude is an automatic, transparent fallback if Ollama is unavailable. |
| **Hero landing page** | A marketing-style entry page (`/`) introducing the product, with a "Go To Chat" CTA into the workspace. |
| **Modern, cohesive UI** | Warm cream/terracotta design system, Claude-inspired document-style assistant messages, tabbed right panel (Sources / Artifacts / Research). |

## Product Walkthrough

1. **Landing** — `/` renders the Hero Landing Page: logo, product name, headline, a description of the four capabilities, and a **Go To Chat** CTA (`components/marketing/hero-landing.tsx`).
2. **Workspace entry** — clicking through lands on `/sessions`, a three-pane shell: a session sidebar on the left, the active chat in the center, and a tabbed **Sources / Artifacts / Research** panel on the right.
3. **Ask a question** — type into the composer (defaults to **Ask** mode), hit Enter. The assistant responds with a grounded, cited answer; a "N sources" button opens the **Sources** tab with the exact transcript excerpts and episode/timestamp labels that grounded it.
4. **Switch to Research** — toggle the composer to **Research**, ask a broader topic. The right panel auto-jumps to the **Research** tab once the multi-section brief is synthesized; the chat itself only shows a short executive-summary teaser pointing at the tab (so the full brief isn't duplicated in two places).
5. **Repurpose with Ship30** — open any artifact (a research brief or a prior Ship30 output) in the **Artifacts** tab, scroll to "Repurpose this with Ship30," optionally edit the framing instruction, and click **LinkedIn post**, **X thread**, or **Article**. The new piece appears both as a new artifact (downloadable as `.md`) and as a new assistant chat turn.
6. **Return home** — the workspace header logo is a clickable link back to the Hero Landing Page.

## System Architecture

### High-Level Architecture

```mermaid
graph TB
    subgraph Client
        Browser["Browser"]
    end

    subgraph Frontend["Next.js 15 Frontend (App Router)"]
        Hero["/ — Hero Landing Page"]
        Workspace["/sessions/[sessionId] — Workspace"]
        Query["TanStack Query cache"]
    end

    subgraph Backend["FastAPI Backend (Vertical Slice)"]
        AuthD["auth domain (dev-mode identity)"]
        SessD["sessions domain"]
        SkillsD["skills domain (QA, Research, Ship30)"]
        KnowD["knowledge domain (internal only, no HTTP)"]
        ArtD["artifacts domain (internal only, no HTTP)"]
        ProvD["providers domain (Model Gateway)"]
    end

    subgraph Data["Data Layer"]
        PG[("PostgreSQL + pgvector\n(Supabase-compatible)")]
    end

    subgraph Models["Model Layer"]
        Ollama["Ollama\n(llama3.1 generation, bge-m3 embeddings)"]
        Claude["Anthropic Claude\n(fallback generation only)"]
    end

    Browser -->|HTTPS| Hero
    Browser -->|HTTPS| Workspace
    Workspace <--> Query
    Query -->|REST/JSON| Backend

    SessD --> PG
    SkillsD --> SessD
    SkillsD --> KnowD
    SkillsD --> ArtD
    SkillsD --> ProvD
    KnowD --> PG
    ArtD --> PG
    ProvD -->|primary| Ollama
    ProvD -->|fallback on failure| Claude
    KnowD -->|query + ingestion embeddings| Ollama

    style Ollama fill:#e8734a,color:#fff
    style Claude fill:#5b4636,color:#fff
    style PG fill:#336791,color:#fff
```

### Agentic Workflow

The "agent" here is a **skill dispatcher**, not an autonomous multi-step agent loop. `POST /sessions/{id}/messages` is the single entry point; it resolves exactly one skill per request, deterministically, from the request body — there is no ReAct-style planning loop, and no LLM call decides which skill runs.

```mermaid
flowchart TD
    Start(["POST /sessions/{id}/messages"]) --> Persist["Persist user message"]
    Persist --> ModeCheck{"mode == 'manual'?"}
    ModeCheck -->|"no (mode='auto', default)"| QA["Run QA Skill"]
    ModeCheck -->|"yes"| SkillCheck{"skill field"}
    SkillCheck -->|"'research'"| Research["Run Research Skill"]
    SkillCheck -->|"'ship30'"| CTCheck{"content_type set?"}
    SkillCheck -->|"'qa' or unset"| QA
    CTCheck -->|"yes"| Ship30["Run Ship30 Skill"]

    QA --> Persist2["Persist assistant message + citations"]
    Research --> Persist2
    Ship30 --> Persist2
    Persist2 --> ArtifactCheck{"result.artifact_type set?"}
    ArtifactCheck -->|"yes"| SaveArt["Persist Artifact\n(+ ResearchBrief row if research_brief)"]
    ArtifactCheck -->|"no"| Respond["Return SkillInvocationResponse"]
    SaveArt --> Respond
```

### Retrieval Workflow

```mermaid
sequenceDiagram
    participant Skill as QA / Research Skill
    participant RS as RetrievalService
    participant ES as EmbeddingService
    participant Ollama as Ollama (bge-m3)
    participant Repo as KnowledgeRepository
    participant DB as pgvector (transcript_chunks)

    Skill->>RS: search(query_text, top_k)
    RS->>ES: embed_text(query_text)
    ES->>Ollama: POST /api/embed (num_gpu=0 if forced-CPU)
    Ollama-->>ES: 1024-dim vector
    ES-->>RS: query_embedding
    RS->>Repo: similarity_search(query_embedding, top_k)
    Repo->>DB: ORDER BY embedding <=> :q  WHERE distance <= 0.48  LIMIT :top_k
    DB-->>Repo: rows (chunk, distance), eager-loaded episode
    Repo-->>RS: TranscriptChunk[] (already threshold-filtered)
    RS-->>Skill: TranscriptChunkRead[] (empty list = "no grounding")
```

### Research Workflow

```mermaid
flowchart LR
    Topic["User's research topic"] --> Expand["Query expansion:\ngenerate 4 sub-queries\n(QUERY_EXPANSION_SYSTEM_PROMPT)"]
    Expand --> Dedupe1["Dedupe queries\n(topic + 4 sub-queries)"]
    Dedupe1 --> Retrieve["Retrieve top-5 chunks\nper query"]
    Retrieve --> Dedupe2["Dedupe by chunk id\ncap at 15 total chunks"]
    Dedupe2 --> Empty{"Any chunks?"}
    Empty -->|"no"| NoGround["Return: insufficient-evidence\nmessage, no artifact"]
    Empty -->|"yes"| Group["Group excerpts by episode"]
    Group --> Synth["Synthesize brief\n(RESEARCH_SYSTEM_PROMPT):\n4 fixed Markdown headings"]
    Synth --> MarkerCheck{"INSUFFICIENT_EVIDENCE_MARKER\nin completion?"}
    MarkerCheck -->|"yes"| NoGround
    MarkerCheck -->|"no"| Structure["Parse into sections\n(ResearchSynthesizer)"]
    Structure --> Split["Split output:\nfull brief -> Artifact\nsummary + CTA -> chat message"]
    Split --> Cite["Build citations from\nretrieved chunks (never model text)"]
    Cite --> Persist["Persist: assistant message,\nArtifact(research_brief),\nResearchBrief row, Citations"]
```

### Artifact Generation Workflow (Ship30)

```mermaid
flowchart TD
    Req["POST /messages\nmode=manual, skill=ship30\ncontent_type, source_artifact_id?"] --> Resolve["Resolve source content"]
    Resolve --> P1{"source_artifact_id given?"}
    P1 -->|"yes"| FromArtifact["Load that Artifact's\ncontent_markdown"]
    P1 -->|"no"| P2{"prior assistant\nmessage in session?"}
    P2 -->|"yes"| FromHistory["Use most recent\nassistant message"]
    P2 -->|"no"| FromInstruction["Use the user's own\ninstruction text"]

    FromArtifact --> Prompt["Build Ship30 prompt:\nformat guidance + source + instruction"]
    FromHistory --> Prompt
    FromInstruction --> Prompt

    Prompt --> Gen["ModelGateway.generate()\n(SHIP30_SYSTEM_PROMPT)"]
    Gen --> Format{"content_type"}
    Format -->|"linkedin_post"| LI["Truncate at 3000 chars\n(LinkedIn's hard limit)"]
    Format -->|"x_thread"| XT["Split on blank lines,\nword-wrap any segment > 280 chars,\nrender N/M numbered thread"]
    Format -->|"article"| Art["Ensure a top-level\n'# Title' heading"]

    LI --> Persist["Persist assistant message\n+ Artifact(artifact_type = content_type)"]
    XT --> Persist
    Art --> Persist
```

### Request Lifecycle

End-to-end trace of a single QA request, from click to render — a synchronous JSON request/response, matching the sequence below exactly.

```mermaid
sequenceDiagram
    actor User
    participant UI as ChatInput (React)
    participant Hook as useSendMessage (TanStack Query)
    participant API as lib/api/skills.ts
    participant FastAPI as POST /sessions/{id}/messages
    participant Sess as SessionService
    participant Skill as QASkill
    participant RAG as RetrievalService
    participant Gateway as ModelGateway
    participant DB as PostgreSQL

    User->>UI: types question, presses Enter
    UI->>Hook: mutate({content, researchMode: false})
    Hook->>API: sendMessage(sessionId, content, {})
    API->>FastAPI: fetch POST (mode="auto")
    FastAPI->>Sess: append_message(role="user")
    Sess->>DB: INSERT messages (+ derive session title if first message)
    FastAPI->>Skill: handle(SkillContext)
    Skill->>RAG: search(query_text, top_k=6)
    RAG->>DB: cosine similarity search (pgvector)
    DB-->>RAG: chunks (or empty)
    RAG-->>Skill: TranscriptChunkRead[]
    Skill->>Gateway: generate(prompt, system=QA_SYSTEM_PROMPT)
    Gateway->>Gateway: try Ollama, fall back to Claude on failure
    Gateway-->>Skill: answer text
    Skill-->>FastAPI: SkillResult(content, citations)
    FastAPI->>Sess: append_message(role="assistant")
    FastAPI->>DB: INSERT citations
    FastAPI-->>API: 201 SkillInvocationResponse (JSON, non-streamed)
    API-->>Hook: response
    Hook->>Hook: invalidateQueries(session, sessions, artifacts)
    Hook-->>UI: refetch triggers re-render
    UI-->>User: answer + "N sources" button appear
```

---

## Frontend Architecture

**Stack**: Next.js 15.1.6 (App Router) · React 19 · TypeScript (strict) · Tailwind CSS 3.4 · shadcn/ui (Radix primitives) · TanStack Query v5 · `react-markdown` + `remark-gfm`.

### Routing

```
frontend/app/
├── layout.tsx                          # Root layout: fonts (Inter + Source Serif 4), <Providers>
├── page.tsx                             # "/" → Hero Landing Page (HeroLanding component)
└── (workspace)/
    ├── layout.tsx                       # 3-pane shell: SessionSidebar / <children> / RightPanel
    └── sessions/
        ├── page.tsx                     # "/sessions" — "select a session" empty state
        └── [sessionId]/
            └── page.tsx                 # Chat page for one session
```

`/` is a real page (`components/marketing/hero-landing.tsx`), not a redirect — it renders logo, headline, description, and a **Go To Chat** button linking to `/sessions`. The workspace's own header logo (`components/sessions/session-sidebar.tsx`) is a `next/link` back to `/`, so navigation is symmetric in both directions. `(workspace)` is a **route group** — the parentheses exclude it from the URL, letting `/sessions` and `/sessions/[sessionId]` share the three-pane shell layout without it leaking into the URL path.

### State management

There is no Redux/Zustand — state is split cleanly between two mechanisms:

- **Server state** — every piece of data that lives in the backend (sessions, session detail/messages, artifacts) is owned by **TanStack Query**. Each domain gets one query-key factory (`sessionQueryKey`, `sessionsQueryKey`, `artifactsQueryKey`) so mutations can invalidate precisely: sending a message invalidates the session detail, the session list (title/recency may have changed), *and* the artifacts list (Research/Ship30 runs produce artifacts) in one `onSuccess` — see `hooks/use-send-message.ts`.
- **UI-only, cross-tree state** — which right-panel tab is active, and which message's citations the Sources tab is showing, live in `RightPanelProvider` (`hooks/use-right-panel.tsx`), a plain React Context. This exists specifically because the chat page and `<RightPanel />` are **siblings** in the App Router tree (the workspace layout renders both, side by side) — plain prop-drilling can't reach across that boundary, so a scoped context is the natural fit, not a heavier global store.

### Workspace design

Three fixed panes inside `(workspace)/layout.tsx`:

| Pane | Width | Contents |
|---|---|---|
| Sidebar | `w-64` (fixed) | Logo (clickable → Hero), "New chat" button, session list ordered by recency |
| Chat | `flex-1 min-w-0` | Message history (document-style assistant messages, bubble-style user messages), composer with an **Ask / Research** mode toggle |
| Right panel | `w-[450px]` (fixed) | Tabbed **Sources / Artifacts / Research** — Sources shows citation excerpts for the message just viewed; Artifacts lists everything except research briefs; Research shows only research briefs, rendered as title + summary cards |

The Artifacts and Research tabs are two presentations of the *same* underlying `GET /sessions/{id}/artifacts` data (`components/artifacts/artifacts-list.tsx` takes a `filterType`/`excludeType` prop) — this keeps the fetch/sort/select state machine in one place instead of duplicating it per tab.

### Thinking/loading state

A single `sendMessage.isPending` flag (from the mutation) drives the "Thinking…" indicator. This has one deliberate wrinkle worth knowing if you're reading `[sessionId]/page.tsx`: the branch that decides whether to show the empty state or the message list is `session.messages.length === 0 && !sendMessage.isPending` — the `!sendMessage.isPending` clause exists specifically so a brand-new session's *first* message still mounts `MessageList` (where the "Thinking…" indicator lives) instead of getting stuck on the empty state for the whole request.

### Landing page

`components/marketing/hero-landing.tsx` — a self-contained, mobile-first component: logo (`next/image`, `/logo.png`, aspect-ratio preserved via matching `width`/`height`), product name, a headline, a description, a centered **Go To Chat** CTA (`<Button asChild><Link href="/sessions">`), and a 2×2 responsive grid of the four core capabilities (Ask, Research, Generate, Discover). Uses the same design tokens (`--accent`, `--background`, etc.) as the workspace — no second visual language.

### Design system

A warm cream/terracotta palette defined as HSL CSS variables in `app/globals.css` (with a `.dark` variant already wired), Inter for all UI chrome, and **Source Serif 4** reserved specifically for quoted transcript excerpts in the citation panel — the one place this app quotes source material verbatim, so it gets a distinct "reading" typographic treatment.

---

## Backend Architecture

**Stack**: FastAPI ≥0.115 · Python ≥3.12 · SQLAlchemy 2.0 (async, `asyncpg`) · Alembic · `pgvector` · `httpx` · `anthropic` SDK · `markdown` + `nh3` (HTML sanitization).

The backend is **Vertical Slice Architecture**, not layered MVC: each domain folder under `app/domains/` owns its *entire* stack — HTTP routes, Pydantic schemas, business logic, data access, and exceptions — rather than splitting `controllers/`, `services/`, `repositories/` across the whole app. A file's role (not its domain) determines its name: every domain has at most one `router.py`, `service.py`, `repository.py`, `schemas.py`, `models.py`, `dependencies.py`, `exceptions.py`.

```
backend/app/
├── main.py                    # App factory: CORS, exception handlers, router registration, /health
├── config/settings.py         # One typed Settings object (pydantic-settings), read everywhere via Depends
├── database/                  # SQLAlchemy Base, async session factory, Alembic migrations
├── exceptions/                # AppError hierarchy + FastAPI exception-handler registration
└── domains/
    ├── auth/                  # Session identity — dev-mode bypass is the active path (see Session Identity & Ownership)
    ├── sessions/               # Session + Message CRUD, history assembly, artifact read-access routes
    ├── skills/                 # THE HTTP entry point for chat: qa/, research/, ship30/, artifact/
    ├── knowledge/              # Ingestion + retrieval — internal only, no HTTP router
    ├── artifacts/              # Persistence + Markdown/HTML rendering — internal only, no HTTP router
    └── providers/              # Model Gateway: Ollama (primary) + Anthropic (fallback)
```

### Dependency injection

Every collaborator is **constructor-injected**, wired through FastAPI's `Depends()` graph — there is no service locator or global singleton (other than the cached `Settings`). A representative chain, from `skills/dependencies.py`:

```python
def get_qa_skill(
    retrieval_service: RetrievalService = Depends(get_retrieval_service),
    model_gateway: ModelGateway = Depends(get_model_gateway),
) -> QASkill:
    return QASkill(retrieval_service=retrieval_service, model_gateway=model_gateway, citation_builder=CitationBuilder())
```

This makes every layer independently swappable in tests: `backend/tests/conftest.py`'s `FakeAsyncSession` and per-test fake `RetrievalService`/`ModelGateway` objects are substituted via `app.dependency_overrides`, exercising the *real* FastAPI app, routing, and skill orchestration logic end-to-end without a live Postgres, Ollama, or Anthropic connection.

### Services, routers, repositories

The convention, held consistently across every domain:

- **`router.py`** — FastAPI path operations only. Resolves dependencies, calls exactly one service method, shapes the response. No business logic.
- **`service.py`** — orchestration and business rules (ownership checks, title derivation, grounding enforcement). Depends on a `repository.py`, never touches SQL directly.
- **`repository.py`** — the only place that talks to SQLAlchemy/Postgres for that domain. `add()`/`flush()` only, never `commit()`/`rollback()` — that's `database/session.py`'s `get_db` dependency's job, so a whole request commits or rolls back atomically.
- **`models.py`** — SQLAlchemy 2.0 declarative models (`Mapped[...]`), one file per domain, mirroring `docs/DATABASE_SCHEMA.md` exactly.

Two domains (`knowledge/`, `artifacts/`) deliberately have **no `router.py`** — `knowledge` is reached only in-process from the QA/Research skills (no HTTP surface for retrieval at all), and `artifacts`' read access (list/get/download) is exposed through `sessions/router.py` instead, since an artifact is never accessed independent of its owning session.

### Providers

`providers/base.py` defines a structural `ModelProvider` protocol (`generate`, `stream`, `embed`); `providers/ollama/` and `providers/anthropic/` each implement it. `providers/gateway.py`'s `ModelGateway` is the *only* thing skills depend on — never a concrete provider — and owns the primary→fallback failover policy (see [LLM Architecture](#llm-architecture)).

### Session Identity & Ownership

Every session, message, and artifact is scoped to an owning user identity, enforced at the application layer: `SessionService.get_owned_session` and `ArtifactService.get_for_session` both check `resource.user_id/session_id` against the caller's id, and deliberately return the same 404 whether a resource doesn't exist or belongs to someone else — avoiding an IDOR-style existence leak.

For local development and demo purposes, identity resolution runs in **dev-mode** (`DEV_AUTH_BYPASS=true`): `auth/dependencies.py::get_current_user` resolves a stable, seeded identity (`main.py`'s startup lifespan hook idempotently provisions that user in `auth.users`), so every other subsystem — sessions, retrieval, skills, artifacts — is exercised against a real, ownership-scoped identity end-to-end. See [Environment Variables](#environment-variables) for the setup step.

---

## Agentic Architecture

### Skill Router

`skills/router.py`'s `post_message` handler is the actual dispatcher — a plain, explicit conditional, not a classifier:

```python
use_ship30 = data.mode == "manual" and data.skill == "ship30"
use_research = data.mode == "manual" and data.skill == "research"
skill: Skill = ship30_skill if use_ship30 else research_skill if use_research else qa_skill
```

- **`mode="auto"` (the default)** resolves to QA — the fast, direct-question path.
- **`mode="manual", skill="research"`** runs Research.
- **`mode="manual", skill="ship30"`** runs Ship30 — additionally requires `content_type` (`linkedin_post` | `x_thread` | `article`); missing it is a 422.

All three skills satisfy the same structural `Skill` protocol (`skills/base.py`, a `typing.Protocol`, not an ABC — no inheritance required):

```python
class Skill(Protocol):
    name: SkillType
    async def handle(self, context: SkillContext) -> SkillResult: ...
```

### QA Skill

`skills/qa/service.py`. Retrieve top-6 chunks → if empty, return the fixed "I don't have enough information…" message with zero citations → build a numbered-excerpt prompt (`build_qa_prompt`) → generate with `QA_SYSTEM_PROMPT` → **if the completion is exactly `INSUFFICIENT_EVIDENCE_MARKER`, return the same no-grounding message** (this is the second, post-generation grounding gate) → otherwise build one `CitationRef` per retrieved chunk (never parsed from the model's free text) and return the answer.

### Research Skill

`skills/research/service.py`. Expands the topic into 4 sub-queries → retrieves top-5 chunks per query, deduplicated by chunk id, capped at 15 total → groups by episode → synthesizes a brief with exactly four fixed Markdown headings (`## Executive Summary`, `## Key Insights`, `## Supporting Evidence`, `## Recommended Actions`) → the same `INSUFFICIENT_EVIDENCE_MARKER` check applies → splits the result: the **chat message** gets only the title + executive summary + a pointer to the Research tab, while the **persisted Artifact** gets the full brief with an appended, programmatically-built Citations section.

---

## Knowledge & Retrieval Pipeline

### Chunking

`knowledge/ingestion/chunking.py` — greedy, fixed-window accumulation. Consecutive time-aligned transcript segments accumulate until they cross **~1000 characters** (~150–200 words, ~30–90s of spoken content), then a new chunk starts. Segments are never split mid-segment — only whole segments are grouped, so a chunk boundary always falls on a natural speech-turn boundary. Each chunk carries **both** a text-offset pair (`start_offset`/`end_offset`, for boundary bookkeeping) and a timestamp pair (`start_timestamp_seconds`/`end_timestamp_seconds`, for citation display like `"12:34-13:02"`).

Two source formats are supported (`knowledge/ingestion/loaders.py`), auto-dispatched by extension:
- **`.json`** — ASR/Whisper-style, `{title, segments: [{text, start, end}]}`.
- **`.md`** — the real Lenny's Podcast archive format: YAML frontmatter (`guest`, `title`, `youtube_url`, `publish_date`, `duration_seconds`) + timestamped speaker turns matched by a regex supporting both `(HH:MM:SS):` and `(MM:SS):` marker conventions. Two rarer per-episode formats in the corpus (`Speaker:` with no timestamp, inline `[HH:MM:SS] Speaker:`) are deliberately **not** parsed — a file using only those fails ingestion loudly rather than silently mis-parsing.

### Embeddings

`knowledge/embeddings/embedding_service.py` calls `providers/ollama/embeddings.py::OllamaEmbeddingsClient` **directly**, bypassing the `ModelGateway` — embeddings have no Claude-equivalent fallback path in this architecture (Claude's provider raises `NotImplementedError` for `.embed()`). Model: **`bge-m3`**, 1024-dimensional dense output, served via Ollama's batch-capable `POST /api/embed`. Every returned vector's dimensionality is validated against `EMBEDDING_DIMENSION = 1024` before it's allowed to reach the database — a silent short/long vector fails loudly here instead of surfacing later as an opaque pgvector insert error.

### pgvector

`transcript_chunks.embedding` is `vector(1024)`, indexed with an **HNSW** index (`vector_cosine_ops`, `m=16, ef_construction=64`) — chosen over IVFFlat because it needs no pre-chosen `lists` parameter tied to an initial row-count estimate, and degrades more gracefully as the corpus grows.

### Similarity search & thresholding

`knowledge/repository.py::similarity_search` — this is the retrieval pipeline's most load-bearing, empirically-tuned line:

```python
_MAX_COSINE_DISTANCE = 0.48
...
.where(distance_expr <= _MAX_COSINE_DISTANCE)
.order_by(distance_expr)
.limit(top_k)
```

An unbounded `ORDER BY ... LIMIT k` **always** returns exactly `k` rows, no matter how distant they actually are — which is precisely what let a query like *"personal branding strategies"* retrieve the closest-available-but-still-irrelevant coaching/career chunks from a corpus with no personal-branding content, and confidently answer from them. The `0.48` cutoff comes from sampling real queries against the corpus: genuinely on-topic chunks landed at cosine distance **~0.34–0.48**, a topically-adjacent-but-not-actually-covered query landed at **~0.49–0.54**, and a fully unrelated query at **~0.62–0.68** — `0.48` sits in the empirical gap between the first two clusters. It's documented in the code as a first cut from a single-episode sample, to be revisited as ingestion coverage grows, not a permanently-correct constant.

### Grounding enforcement — two independent gates

1. **Pre-generation (retrieval-time)**: the distance threshold above. If nothing survives it, retrieval returns an empty list and the skill returns the "no grounding" message without ever calling the model.
2. **Post-generation (model-time)**: even chunks that pass the threshold can be topically adjacent without actually answering the specific question asked (e.g., broad "coaching" content when the question was about "personal branding specifically"). Both `QA_SYSTEM_PROMPT` and `RESEARCH_SYSTEM_PROMPT` explicitly instruct the model to judge this itself and respond with the exact literal sentinel `INSUFFICIENT_EVIDENCE_MARKER` instead of stretching a partial excerpt into a confident answer — checked with a plain substring test in `qa/service.py`/`research/service.py` **before** citations are ever built, so a low-confidence answer can never carry citations implying stronger grounding than it has.

Citations themselves are **never parsed from model output** — `CitationBuilder.build()` constructs one `CitationRef` per chunk that was actually shown to the model, in the same order the model saw them, regardless of which `[N]` markers the model chose to reference in its prose.

---

## Research Engine

### Query expansion

`research/prompts.py::build_query_expansion_prompt` asks the model for exactly **4 distinct search queries** covering different angles/sub-topics of the user's research question, one per line, no numbering. `parse_subqueries` strips any bullet/numbering the model added anyway and caps the result at 4.

### Retrieval

The original topic plus its 4 expansions are deduplicated (case-insensitive, whitespace-trimmed) into a query set, then each query independently retrieves its own top-5 chunks (`_TOP_K_PER_QUERY = 5`). Results are merged and deduplicated by `transcript_chunk.id` across *all* queries (not per-query), capped at **15 total chunks** (`_MAX_TOTAL_CHUNKS`) — this is what gives genuine cross-episode coverage instead of near-duplicate top-k from a single query.

### Synthesis

Chunks are grouped by episode title and handed to `RESEARCH_SYSTEM_PROMPT`, which mandates exactly four Markdown headings in a fixed order (Executive Summary / Key Insights / Supporting Evidence / Recommended Actions) and explicitly forbids the model from generating its own citations section (one is appended programmatically afterward). `ResearchSynthesizer.structure()` parses the completion by its `## ` headings into `ResearchBriefSection`s, falling back to a single catch-all section if the model didn't use headings at all — so content is never silently dropped even on a malformed completion.

### Artifact creation

The Research skill is the only skill that populates `SkillResult.artifact_content_markdown` **separately** from `content_markdown` — a deliberate UX split: `content_markdown` (what appears in the chat transcript) is just the title + executive summary + a "see the Research tab" pointer, while `artifact_content_markdown` (what gets persisted as the Artifact) is the complete, multi-section brief with its citations appendix. Without this split, the entire brief was duplicated verbatim into the chat, making the dedicated Research tab feel redundant. The router (`skills/router.py`) additionally persists a `ResearchBrief` specialization row (`topic`, `summary`) alongside the generic `Artifact` row whenever `artifact_type == "research_brief"`.

---

## Artifact Generation

Ship30 (`skills/ship30/service.py`) transforms prior session content into one of three publishable formats, always through the same `POST /sessions/{id}/messages` endpoint (`mode="manual", skill="ship30"`) — there's no separate artifact-generation API.

**Source resolution priority** (`_resolve_source_markdown`): (1) an explicit `source_artifact_id`, if given, wins — its `content_markdown` is the source; (2) otherwise, the most recent assistant message in the session; (3) otherwise (a brand-new session), the user's own instruction text stands in as the source.

| Format | Generation guidance | Post-processing |
|---|---|---|
| **LinkedIn post** | 150–300 words, conversational-professional tone, hook opener, ≤3 hashtags | Hard-truncated at LinkedIn's real **3000-character** limit (safety net; the prompt already targets far under this) |
| **X thread** | 5–8 tweets, first tweet a standalone hook, one point per tweet | Split on blank lines (the prompt asks the model to separate tweets that way); any segment still over **280 characters** is word-wrapped (never mid-word) as a fallback; rendered as a numbered `**N/M**` Markdown document |
| **Article** | `# Title` + short intro + 2–4 `##` sections + closing paragraph | If the model omits the `#` title line, the first line is promoted into one rather than the output being rejected |

All three share one system prompt (`SHIP30_SYSTEM_PROMPT`) instructing the model to base output strictly on the provided source material — no invented claims, statistics, or quotes. The formatted result becomes both a new `Artifact` (`artifact_type` = the same `content_type`) and a new assistant chat message, exactly like every other skill.

---

## Database Schema

**Engine**: PostgreSQL (Supabase-compatible) + `pgvector`. Schema lives in a single consolidated Alembic migration, `backend/app/database/migrations/versions/0001_initial_schema.py` (592 lines, raw SQL via `op.execute` — chosen for byte-level fidelity to the hand-written schema doc, since triggers and Row-Level Security have no native Alembic DSL anyway). `auth.users` is Supabase's own table — not created by this schema; it's the source of truth for identity.

### Entity-Relationship Diagram

```mermaid
erDiagram
    AUTH_USERS ||--o| PROFILES : extends
    AUTH_USERS ||--o{ SESSIONS : owns
    SESSIONS ||--o{ MESSAGES : contains
    SESSIONS ||--o{ ARTIFACTS : has
    MESSAGES ||--o{ ARTIFACTS : produces
    MESSAGES ||--o{ CITATIONS : cites
    CITATIONS }o--|| TRANSCRIPT_CHUNKS : references
    TRANSCRIPT_CHUNKS }o--|| EPISODES : belongs_to
    ARTIFACTS ||--o| RESEARCH_BRIEFS : specializes

    AUTH_USERS {
        uuid id
        text email
    }

    PROFILES {
        uuid id
        text display_name
        timestamptz created_at
        timestamptz updated_at
    }

    SESSIONS {
        uuid id
        uuid user_id
        text title
        timestamptz created_at
        timestamptz updated_at
    }

    MESSAGES {
        uuid id
        uuid session_id
        text role
        text content
        text skill_used
        timestamptz created_at
    }

    EPISODES {
        uuid id
        text title
        text guest_name
        date published_at
        text source_url
    }

    TRANSCRIPT_CHUNKS {
        uuid id
        uuid episode_id
        text content
        text embedding
        int start_offset
        int end_offset
        int start_timestamp_seconds
        int end_timestamp_seconds
    }

    CITATIONS {
        uuid id
        uuid message_id
        uuid transcript_chunk_id
        text display_label
    }

    ARTIFACTS {
        uuid id
        uuid session_id
        uuid message_id
        text artifact_type
        text content_markdown
        timestamptz created_at
    }

    RESEARCH_BRIEFS {
        uuid id
        uuid artifact_id
        text topic
        text summary
    }
```

### Table reference

| Table | Purpose | Notable constraints |
|---|---|---|
| `profiles` | Optional profile data extending `auth.users`. Auto-created by a `handle_new_user()` trigger on `auth.users` insert. | PK **is** `auth.users.id` (shared-PK 1:1, not a generated UUID). |
| `sessions` | Top-level chat workspace unit, owned by a user. | `updated_at` bumped by a `messages_touch_session` trigger on every new message, driving sidebar recency order. |
| `messages` | One turn (`user`/`assistant`/`system`) in a session. | `CHECK (role IN (...))`; `skill_used` only settable when `role = 'assistant'` (enforced by a second `CHECK`). |
| `episodes` | One podcast episode. Written only by the offline ingestion pipeline. | — |
| `transcript_chunks` | Retrievable, embedded transcript segment. Written only by ingestion. | `vector(1024)`; `end_offset > start_offset`; `end_timestamp_seconds > start_timestamp_seconds`. |
| `citations` | Links an assistant message to the transcript chunk(s) that grounded it. | `UNIQUE(message_id, transcript_chunk_id)`; **`ON DELETE RESTRICT`** on `transcript_chunk_id` — deliberately not cascading, so a future re-ingestion can't silently orphan historical grounding data. |
| `artifacts` | Persisted, renderable output (Markdown canonical). | `CHECK` on `artifact_type`; no `content_html` column — HTML is always derived at read time. |
| `research_briefs` | 1:1 specialization of an `artifacts` row where `artifact_type = 'research_brief'`. | `UNIQUE(artifact_id)`; a `BEFORE INSERT/UPDATE` trigger rejects a row whose parent artifact isn't actually `research_brief`-typed (a cross-table integrity rule `CHECK` can't express). |

### Row-Level Security

Every table has RLS enabled with `auth.uid()`-scoped policies (see the migration for the full policy set) — but this is **defense-in-depth**, not the primary enforcement boundary today: the FastAPI backend connects with the Supabase `service_role` key (bypassing RLS for its own queries, per `DATABASE_SCHEMA.md` §8 risk #2's resolved Option A), so ownership is actually enforced in each domain's `service.py` (`get_owned_session`, `get_for_session`), which is unit-testable in isolation and doesn't require a live Postgres + simulated JWT to verify.

### Indexes

`(user_id, updated_at DESC)` on `sessions` (sidebar ordering) · `(session_id, created_at)` on `messages` and `artifacts` (ordered history/listing) · `(message_id)` on `artifacts` · `(episode_id)` on `transcript_chunks` · `(transcript_chunk_id)` on `citations` · the HNSW vector index described above.

---

## API Documentation

Base URL: `http://localhost:8000` (no `/api` prefix, no versioning yet). All bodies are JSON except the artifact-download endpoint. Every error response has the shape `{"error_code": string, "message": string}` (`exceptions/handlers.py`), mapped from an `AppError` subclass — 404/`not_found`, 422/`validation_error`, 401/`unauthorized`, 403/`forbidden`, 409/`conflict`, 502/`upstream_service_error`, 500/`internal_error` as a last resort.

### `GET /health`
Liveness probe, no dependencies checked (not DB, not model providers).
```json
{"status": "ok"}
```

### Sessions — `sessions/router.py`

| Method & Path | Purpose |
|---|---|
| `POST /sessions` | Create a session. Body: `{"title": string \| null}`. Returns `SessionDetailRead` with `messages: []`. |
| `GET /sessions` | List the caller's sessions, most-recently-updated first. Returns `SessionListItem[]`. |
| `GET /sessions/{session_id}` | Resume a session with full ordered message history (including nested citations). |
| `GET /sessions/{session_id}/artifacts` | List artifacts attached to a session. |
| `GET /sessions/{session_id}/artifacts/{artifact_id}` | Get one artifact. |
| `GET /sessions/{session_id}/artifacts/{artifact_id}/download` | Raw Markdown download (`text/plain`), verbatim `content_markdown`. |

**Example — create a session, then ask a question:**

```bash
curl -X POST http://localhost:8000/sessions \
  -H "Content-Type: application/json" \
  -d '{"title": null}'
# → {"id": "…", "user_id": "…", "title": "New session", "messages": [], ...}
```

### Messages / Skill invocation — `skills/router.py`

`POST /sessions/{session_id}/messages` — the single endpoint for QA, Research, and Ship30.

**Request body** (`SkillInvocationRequest`):

| Field | Type | Notes |
|---|---|---|
| `content` | `string` (required, min length 1) | The question, research topic, or Ship30 framing instruction. |
| `mode` | `"auto" \| "manual"` | Default `"auto"` → always QA. |
| `skill` | `"qa" \| "research" \| "ship30" \| null` | Required when `mode="manual"`. |
| `content_type` | `"linkedin_post" \| "x_thread" \| "article" \| null` | Required when `skill="ship30"`. |
| `source_artifact_id` | `uuid \| null` | Ship30-only; falls back to the session's last assistant message if omitted. |

**Example — QA (auto mode):**
```bash
curl -X POST http://localhost:8000/sessions/{session_id}/messages \
  -H "Content-Type: application/json" \
  -d '{"content": "What is activation?"}'
```
```json
{
  "skill_used": "qa",
  "routing_mode": "auto",
  "message": {
    "id": "…", "role": "assistant",
    "content": "Activation means getting to value fast [1].",
    "citations": [{"display_label": "Episode 142 — 1:40-1:50", "excerpt": "Activation is time to first value."}]
  },
  "citations": [{"transcript_chunk_id": "…", "display_label": "Episode 142 — 1:40-1:50", "excerpt": "…"}],
  "artifact_id": null
}
```

**Example — Research (manual mode):**
```bash
curl -X POST http://localhost:8000/sessions/{session_id}/messages \
  -H "Content-Type: application/json" \
  -d '{"content": "How should early-stage startups think about pricing?", "mode": "manual", "skill": "research"}'
```
Response's `artifact_id` will be non-null; `GET /sessions/{id}/artifacts/{artifact_id}` returns the full multi-section brief.

**Example — Ship30 (manual mode, from an existing artifact):**
```bash
curl -X POST http://localhost:8000/sessions/{session_id}/messages \
  -H "Content-Type: application/json" \
  -d '{
        "content": "Make it punchy and end with a question.",
        "mode": "manual", "skill": "ship30",
        "content_type": "linkedin_post",
        "source_artifact_id": "…"
      }'
```

---

## LLM Architecture

### Provider abstraction

```mermaid
classDiagram
    class ModelProvider {
        <<Protocol>>
        +generate(prompt, system) str
        +embed(text) list
    }
    class OllamaProvider {
        +generate() str
    }
    class AnthropicProvider {
        +generate() str
    }
    class ModelGateway {
        -primary ModelProvider
        -secondary ModelProvider
        +generate() str
    }
    ModelProvider <|.. OllamaProvider
    ModelProvider <|.. AnthropicProvider
    ModelGateway --> ModelProvider : primary = Ollama
    ModelGateway --> ModelProvider : secondary = Claude
```

- `OllamaProvider.generate()` — `POST /api/chat` against the local Ollama instance.
- `AnthropicProvider.generate()` — Claude Messages API, used only as the automatic fallback.
- `ModelGateway.generate()` — tries `primary` (Ollama) first, falls back to `secondary` (Claude) on `ProviderUnavailableError`. Embeddings (`bge-m3`) are called directly against Ollama rather than through the gateway — see [Embedding model](#embedding-model).

Every skill depends on `ModelGateway` alone, never a concrete provider — the graceful-degradation policy lives in exactly one place (`providers/gateway.py`):

```python
try:
    result = await self._primary.generate(prompt=prompt, system=system)   # Ollama
except ProviderUnavailableError:
    result = await self._secondary.generate(prompt=prompt, system=system)  # Claude
    # AllProvidersUnavailableError only if BOTH fail
```

`OllamaClient` (the shared HTTP transport under both Ollama call sites) retries transient failures (connect errors, timeouts, `408/425/429/500/502/503/504`) up to 3 times with exponential backoff before the gateway ever sees a failure — so a fallback to Claude only happens after Ollama has genuinely had a fair chance, not on the first hiccup.

### Generation model

**`llama3.1`** (configurable via `OLLAMA_GENERATION_MODEL`), called through Ollama's `POST /api/chat` (chat-completion shape, not the legacy `/api/generate`) — a synchronous, complete-response call per request.

### Embedding model

**`bge-m3`** (configurable via `OLLAMA_EMBEDDING_MODEL`), 1024-dimensional dense output, called via Ollama's batch-capable `POST /api/embed`. Deliberately **not** routed through `ModelGateway` — there is no Claude-embedding fallback in this architecture (Anthropic doesn't serve an embeddings endpoint this codebase targets), so `EmbeddingService` talks to `OllamaEmbeddingsClient` directly.

### Fallback / secondary model

**Claude** (`claude-sonnet-4-5` by default, via the official `anthropic` Python SDK), generation-only. Triggered transparently whenever Ollama's retries are exhausted (unreachable, model not loaded, persistent 5xx) — the user gets an answer either way; only a structured log line (`model_invocation`, `provider`, `was_fallback`, `latency_ms`) records which provider actually served the request.

---

## Local Setup

### Prerequisites

- **Python 3.12+**
- **Node.js 20+**
- **PostgreSQL** with the `vector` (pgvector) and `pgcrypto` extensions available — a Supabase project (hosted) or any Postgres ≥13 with `pgvector` installed works
- **Ollama**, with `llama3.1` and `bge-m3` pulled
- An **Anthropic API key** (for the fallback path — required even in local dev, since `ANTHROPIC_API_KEY` has no default)

## Environment Variables

`backend/.env.example` — copy to `backend/.env` and fill in:

| Variable | Default | Required | Notes |
|---|---|---|---|
| `APP_ENV` | `development` | | |
| `LOG_LEVEL` | `INFO` | | |
| `CORS_ALLOWED_ORIGINS` | `[]` | | JSON array, e.g. `["http://localhost:3000"]` |
| `DEV_AUTH_BYPASS` | `false` | | **Set `true` for local dev** — see [Session Identity & Ownership](#session-identity--ownership). Never enable against a real deployment. |
| `DATABASE_URL` | — | **yes** | `postgresql+asyncpg://user:pass@host:5432/db` |
| `SUPABASE_URL` | — | **yes** | Even with `DEV_AUTH_BYPASS=true`, must be set (no default) though unused on that path |
| `SUPABASE_SERVICE_KEY` | — | **yes** | Same as above |
| `SUPABASE_JWT_SECRET` | — | **yes** | Same as above |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | | |
| `OLLAMA_GENERATION_MODEL` | `llama3.1` | | |
| `OLLAMA_EMBEDDING_MODEL` | `bge-m3` | | |
| `OLLAMA_REQUEST_TIMEOUT_SECONDS` | `30.0` | | |
| `OLLAMA_EMBEDDING_FORCE_CPU` | `true` | | Forces `bge-m3` onto CPU (`num_gpu=0`) so `llama3.1` keeps exclusive GPU residency — see [Performance Optimizations](#performance-optimizations). Set `false` only if your GPU has VRAM for both models resident at once. |
| `TRANSCRIPT_INGESTION_DIR` | `./transcripts` | | Scanned recursively for `transcript.md`, non-recursively for `*.json` |
| `ANTHROPIC_API_KEY` | — | **yes** | |
| `ANTHROPIC_MODEL` | `claude-sonnet-4-5` | | |
| `ANTHROPIC_REQUEST_TIMEOUT_SECONDS` | `30.0` | | |

Frontend — `frontend/.env.local` (see `frontend/README.md`):

| Variable | Default |
|---|---|
| `NEXT_PUBLIC_API_BASE_URL` | `http://localhost:8000` |

## Installation

```bash
git clone <this-repo>
cd Lenny

# Backend
cd backend
python -m venv .venv
. .venv/bin/activate            # Windows: .venv\Scripts\activate
pip install -e ".[test]"
cp .env.example .env             # fill in DATABASE_URL, SUPABASE_*, ANTHROPIC_API_KEY; set DEV_AUTH_BYPASS=true

# Frontend
cd ../frontend
npm install
cp .env.local.example .env.local  # defaults to http://localhost:8000
```

## Running Backend

```bash
cd backend
alembic upgrade head                                    # applies 0001_initial_schema.py
python -m app.domains.knowledge.ingestion.cli            # ingest transcripts from TRANSCRIPT_INGESTION_DIR
uvicorn app.main:app --reload                            # http://localhost:8000
pytest                                                    # HTTP-boundary smoke tests, no live DB/Ollama required
```

## Running Frontend

```bash
cd frontend
npm run dev          # http://localhost:3000
npm run build         # production build
npm run lint          # ESLint (next/core-web-vitals + next/typescript)
npm run typecheck    # tsc --noEmit
```

## Running Ollama

```bash
ollama pull llama3.1
ollama pull bge-m3
ollama serve          # if not already running as a service — defaults to :11434
```

Confirm both models respond before starting the backend: `curl http://localhost:11434/api/tags`.

## Running PostgreSQL

Either connect `DATABASE_URL` to a hosted **Supabase** project (simplest — `pgvector`/`pgcrypto` are pre-available), or run a local Postgres with the extensions installed:

```sql
CREATE EXTENSION IF NOT EXISTS pgcrypto;
CREATE EXTENSION IF NOT EXISTS vector;
```

Then point `DATABASE_URL` at it and run `alembic upgrade head` as above. No Docker Compose file is provided — containerization was explicitly out of scope for this build (`CONTEXT.md`: "No Docker for MVP").

---

## Example Workflows

**1. Grounded Q&A**
```
POST /sessions                          → new session
POST /sessions/{id}/messages            {"content": "What do guests say about pricing PLG products?"}
  → assistant answer, citations[], artifact_id: null
```

**2. Research brief → LinkedIn post**
```
POST /sessions/{id}/messages   {"content": "PLG pricing models", "mode":"manual", "skill":"research"}
  → artifact_id: "brief-1" (research_brief)
GET  /sessions/{id}/artifacts/brief-1   → full multi-section brief
POST /sessions/{id}/messages   {"content": "Make it punchy.", "mode":"manual", "skill":"ship30",
                                 "content_type":"linkedin_post", "source_artifact_id":"brief-1"}
  → artifact_id: "post-1" (linkedin_post), also appended to chat history
```

**3. Insufficient-evidence path**
```
POST /sessions/{id}/messages   {"content": "What does the corpus say about underwater basket weaving?"}
  → "I don't have enough information in the ingested Lenny's Podcast transcripts to answer that
     confidently. Try rephrasing, or ask about a topic covered in an episode that's been ingested."
  → citations: []
```

---

## Design Decisions

| Decision | Rationale |
|---|---|
| **Vertical Slice, not layered MVC** | Each domain (`sessions`, `skills`, `knowledge`, `artifacts`, `providers`, `auth`) owns its full stack. Adding a fifth skill touches one new folder, not five existing layered ones. |
| **Structural `Protocol`s over ABCs** (`Skill`, `ModelProvider`) | New skills/providers don't need to inherit from anything — they just need the right method shapes, keeping every implementation fully decoupled from a shared base class. |
| **Constructor-based DI via `Depends()`** everywhere | Every collaborator is swappable in tests via `app.dependency_overrides`, with zero service-locator/global-state indirection. |
| **Citations built only from retrieval metadata, never model text** | Removes an entire class of hallucinated-citation risk — a citation can only exist for a chunk the model actually saw. |
| **Two-stage grounding (threshold + model self-check)** | A distance cutoff alone can't tell "adjacent topic" from "actually on-topic"; a model self-check alone can't stop a retrieval that returned nothing relevant at all. Neither is sufficient in isolation. |
| **Markdown as the artifact's only canonical form** | Copy/Download can never drift from what's rendered — HTML is always a pure, sanitized derivation, never independently stored. |
| **Research chat message ≠ Research artifact content** | Without the split, the Research tab was redundant with the chat transcript (both showed the full brief). |
| **Dev-mode identity (`DEV_AUTH_BYPASS`) for this milestone** | Lets every other subsystem (sessions, skills, retrieval, artifacts) be built and demoed against a real, working, ownership-scoped user identity without also having to stand up a full Supabase Auth integration first. |

## Tradeoffs

- **`service_role`-only DB access** means the RLS policies defined in the migration are currently inert for the backend's own traffic — real protection is 100% application-layer. This is a documented, deliberate choice (simpler to reason about and unit-test for a single-developer build), not an accident, but it means a second, RLS-respecting client (if one is ever added) would need its own JWT-propagation work to actually benefit from those policies.
- **Fixed `vector(1024)` dimension** ties the schema to `bge-m3` specifically — swapping embedding models later means a full corpus re-embed, not an in-place migration.
- **`citations.transcript_chunk_id` is `ON DELETE RESTRICT`** — protects historical grounding data, but means the ingestion pipeline cannot blindly delete-and-replace an already-cited episode's chunks on re-ingestion; it currently always inserts a *new* episode row on re-run rather than de-duplicating.

## Performance Optimizations

- **Retrieval threshold (`_MAX_COSINE_DISTANCE = 0.48`)** — see [Knowledge & Retrieval Pipeline](#knowledge--retrieval-pipeline). Directly fixes a real, reproduced bug (irrelevant chunks being confidently cited) rather than being a speculative tuning knob.
- **`OLLAMA_EMBEDDING_FORCE_CPU=true`** (`providers/ollama/embeddings.py`) — on a GPU too small to hold both the generation and embedding models resident simultaneously, every switch between them evicted whichever model wasn't currently needed, forcing a full reload on the *next* call to either. Measured before/after: **~2.5s warm vs. ~14s reload** for `bge-m3`; **~3.3s warm vs. ~22s reload** for `llama3.1`. Since QA and Research always call embed-then-generate within the same request, this thrashing happened on *every single request*. Forcing the small (566M-parameter) embedding model onto CPU via Ollama's per-request `options.num_gpu=0` leaves the GPU exclusively for the generation model — the actual fix, not a workaround.
- **Bounded retry with exponential backoff** (`OllamaClient`, 3 attempts, `0.5s * 2^n`) on transient failures only — a `400`/`404`/`401` fails immediately rather than wasting 3 retries on a request that will never succeed.
- **UX: first-message "Thinking…" fix** — the `session.messages.length === 0 && !sendMessage.isPending` gate in `[sessionId]/page.tsx` (see [Frontend Architecture](#frontend-architecture)) — a one-line fix for a real bug where a brand-new session's first message showed no loading feedback for the entire request duration.
- **Right panel width increase (320px → 450px)** — source excerpts were measurably cramped at the original width; this is a UX-driven layout constant, not a code-performance change, but is documented in `right-panel.tsx` as a deliberate, measured decision rather than an arbitrary number.

## Implemented Features

Every capability below is real, working, and demonstrated end-to-end in this repository — verified by reading the actual source, not the planning docs.

| Capability | What it does |
|---|---|
| **QA — grounded Q&A** | Retrieval-augmented answers over 303 real podcast episodes, with inline citations for every claim. |
| **Research — cross-episode synthesis** | Query expansion, multi-episode retrieval and dedup, and a structured 4-section brief with per-episode source grouping. |
| **Ship30 — content repurposing** | LinkedIn post, X thread, and article generation from any prior answer or brief, with platform-accurate formatting (length limits, thread segmentation). |
| **Grounding enforcement** | A tuned retrieval relevance threshold plus a generation-time self-check, so the system says "I don't have enough information" instead of fabricating an answer. |
| **Hero landing page** | A dedicated `/` entry page with branding, product description, and a "Go To Chat" CTA into the workspace, with a link back from the workspace header. |
| **Artifact system** | Research briefs and Ship30 outputs persist as downloadable, sanitized Markdown/HTML artifacts (`nh3`), separate from the chat transcript. |
| **Session workspace** | Persistent, resumable sessions with auto-generated titles, full message history, and a tabbed Sources / Artifacts / Research panel. |
| **Ollama-first generation with automatic fallback** | Local `llama3.1` generation with transparent, automatic failover to Anthropic Claude on provider failure. |

## Future Improvements

- Full user authentication (registration, login, session/password management), extending the current dev-mode identity into a production-ready flow.
- Intent-based auto-routing between skills, reducing reliance on the explicit `mode`/`skill` selection.
- Streaming responses for lower perceived latency on longer Research and Ship30 generations.
- Structured, persisted analytics on routing decisions and model-provider usage, for evaluation and cost tracking.
- De-duplication on re-ingestion for a transcript source that's already been ingested.
- Embedding-model versioning on `transcript_chunks`, to make a future re-embed migration safe and trackable.
- Continued tuning of the retrieval relevance threshold as corpus coverage grows.

## Screenshots

## Screenshots

| | |
|---|---|
| ![Hero Landing Page](docs/screenshots/Hero%20Landing%20Page.jpeg) | ![Chat](docs/screenshots/Chat.jpeg) |
| *Hero landing page and workspace entry point* | *Interactive chat workspace* |

| | |
|---|---|
| ![QA](docs/screenshots/QA.jpeg) | ![Research](docs/screenshots/Research.jpeg) |
| *Grounded Q&A with citations and sources* | *Generated research brief* |

| | |
|---|---|
| ![Research Tab](docs/screenshots/Research%20Tab.jpeg) | ![Research Tab Expanded](docs/screenshots/Research%20Tab%20Expanded.jpeg) |
| *Research artifacts tab* | *Expanded research brief view* |

| | |
|---|---|
| ![Artifacts](docs/screenshots/Artifacts.jpeg) |
| *Generated content artifacts and outputs* |
## Agent Transcripts

`transcripts/` is the **knowledge corpus itself** — not a log of AI-agent conversations. It is the raw source material the ingestion pipeline (`knowledge/ingestion/`) reads and embeds:

```
transcripts/
├── README.md                         # Archive documentation (episode count, format, provenance)
├── CLAUDE.md                          # Working notes for AI coding assistants navigating this corpus
├── episode-142.json                   # A JSON-format sample episode (ASR-style: {title, segments[]})
├── episodes/
│   └── {guest-name}/
│       └── transcript.md              # 303 real episodes — YAML frontmatter + timestamped speaker turns
└── index/
    ├── README.md                      # Topic index entry point
    └── {topic}.md                     # 50+ AI-generated topic files (e.g. product-management.md, leadership.md)
```

Each `episodes/{guest}/transcript.md` carries YAML frontmatter (`guest`, `title`, `youtube_url`, `video_id`, `publish_date`, `duration_seconds`, …) followed by the full timestamped transcript — this is exactly what `knowledge/ingestion/loaders.py::_load_markdown_episode` parses. `index/` is a separately-maintained, AI-generated keyword index for human browsing (`grep -r "topic" episodes/` or browse by `index/{topic}.md`) — it is not consumed by the application at runtime; the app's own "topic index" is the pgvector embedding space itself. Two known-duplicate/non-interview folders (`andy-raskin_`, `teaser_2021`) are explicitly excluded from ingestion (`ingestion/pipeline.py::_EXCLUDED_EPISODE_DIR_NAMES`).

## License

This project was developed as a take-home assignment / portfolio project. The application code is the author's own work; the transcript corpus under `transcripts/` belongs to Lenny's Podcast and its guests and is included for educational/research purposes only (see `transcripts/README.md`'s own disclaimer). No open-source license file is currently published for the application code — treat it as all-rights-reserved unless the repository owner states otherwise.
