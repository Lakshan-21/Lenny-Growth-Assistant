# Repository Structure: Lenny Growth Workspace

| | |
|---|---|
| **Status** | Draft |
| **Version** | 0.1.0 |
| **Owner** | Engineering |
| **Last Updated** | 2026-08-02 |

Related: [CONTEXT.md](../CONTEXT.md) · [PRD.md](./PRD.md) · [ARCHITECTURE.md](./ARCHITECTURE.md) · [DOMAIN_MODEL.md](./DOMAIN_MODEL.md) · [IMPLEMENTATION_PLAN.md](./IMPLEMENTATION_PLAN.md)

This document defines the repository layout only. It does not introduce any technology, pattern, or domain not already locked in `CONTEXT.md`. Backend is organized as **Vertical Slice Architecture**: each domain folder under `app/domains/` owns its own API layer, schemas, business logic, data access, and tests — nothing is split across horizontal "controllers/services/repositories" layers at the top level. No Docker (per `CONTEXT.md` — MVP has no containerization).

**MVP simplifications applied (all domains, technologies, and behaviors below remain exactly as locked in `CONTEXT.md`):**

1. `knowledge/` has no HTTP router — it is an internal domain reached only via in-process calls from the QA and Research skills.
2. `artifacts/` has no HTTP router — artifact access is exposed through `sessions/router.py` instead.
3. `RoutingDecision` is not persisted — routing decisions are recorded to application logs only. Router behavior is unchanged.
4. `ModelInvocation` is not persisted — provider invocation details are recorded to application logs only. Graceful-degradation/fallback behavior is unchanged.

---

## 1. Complete Repository Tree

```
lenny-growth-workspace/
├── CONTEXT.md
├── README.md
├── .gitignore
├── .editorconfig
├── docs/
│   ├── PRD.md
│   ├── ARCHITECTURE.md
│   ├── DOMAIN_MODEL.md
│   ├── IMPLEMENTATION_PLAN.md
│   └── REPOSITORY_STRUCTURE.md
│
├── backend/
│   ├── pyproject.toml
│   ├── requirements.txt
│   ├── alembic.ini
│   ├── .env.example
│   ├── README.md
│   ├── app/
│   │   ├── main.py
│   │   │
│   │   ├── config/
│   │   │   ├── __init__.py
│   │   │   └── settings.py
│   │   │
│   │   ├── database/
│   │   │   ├── __init__.py
│   │   │   ├── base.py
│   │   │   ├── session.py
│   │   │   └── migrations/
│   │   │       ├── env.py
│   │   │       ├── script.py.mako
│   │   │       └── versions/
│   │   │           └── .gitkeep
│   │   │
│   │   ├── exceptions/
│   │   │   ├── __init__.py
│   │   │   ├── base.py
│   │   │   └── handlers.py
│   │   │
│   │   └── domains/
│   │       ├── __init__.py
│   │       │
│   │       ├── auth/
│   │       │   ├── __init__.py
│   │       │   ├── router.py
│   │       │   ├── schemas.py
│   │       │   ├── service.py
│   │       │   ├── dependencies.py
│   │       │   ├── supabase_client.py
│   │       │   ├── exceptions.py
│   │       │   └── tests/
│   │       │       ├── test_router.py
│   │       │       └── test_service.py
│   │       │
│   │       ├── sessions/
│   │       │   ├── __init__.py
│   │       │   ├── router.py
│   │       │   ├── schemas.py
│   │       │   ├── service.py
│   │       │   ├── repository.py
│   │       │   ├── models.py
│   │       │   ├── dependencies.py
│   │       │   ├── exceptions.py
│   │       │   └── tests/
│   │       │       ├── test_router.py
│   │       │       ├── test_service.py
│   │       │       └── test_repository.py
│   │       │
│   │       ├── skills/
│   │       │   ├── __init__.py
│   │       │   ├── router.py
│   │       │   ├── schemas.py
│   │       │   ├── base.py
│   │       │   ├── skill_router.py
│   │       │   ├── exceptions.py
│   │       │   ├── qa/
│   │       │   │   ├── __init__.py
│   │       │   │   ├── service.py
│   │       │   │   ├── schemas.py
│   │       │   │   ├── prompts.py
│   │       │   │   ├── citation_builder.py
│   │       │   │   └── tests/
│   │       │   │       └── test_service.py
│   │       │   ├── research/
│   │       │   │   ├── __init__.py
│   │       │   │   ├── service.py
│   │       │   │   ├── schemas.py
│   │       │   │   ├── prompts.py
│   │       │   │   ├── synthesis.py
│   │       │   │   └── tests/
│   │       │   │       └── test_service.py
│   │       │   ├── ship30/
│   │       │   │   ├── __init__.py
│   │       │   │   ├── service.py
│   │       │   │   ├── schemas.py
│   │       │   │   ├── prompts.py
│   │       │   │   ├── formatters/
│   │       │   │   │   ├── __init__.py
│   │       │   │   │   ├── linkedin.py
│   │       │   │   │   ├── x_thread.py
│   │       │   │   │   └── article.py
│   │       │   │   └── tests/
│   │       │   │       └── test_service.py
│   │       │   ├── artifact/
│   │       │   │   ├── __init__.py
│   │       │   │   ├── service.py
│   │       │   │   ├── schemas.py
│   │       │   │   └── tests/
│   │       │   │       └── test_service.py
│   │       │   └── tests/
│   │       │       └── test_skill_router.py
│   │       │
│   │       ├── artifacts/
│   │       │   ├── __init__.py
│   │       │   ├── schemas.py
│   │       │   ├── service.py
│   │       │   ├── repository.py
│   │       │   ├── models.py
│   │       │   ├── exceptions.py
│   │       │   ├── renderers/
│   │       │   │   ├── __init__.py
│   │       │   │   ├── markdown_renderer.py
│   │       │   │   └── html_renderer.py
│   │       │   └── tests/
│   │       │       ├── test_service.py
│   │       │       └── test_renderers.py
│   │       │
│   │       ├── knowledge/
│   │       │   ├── __init__.py
│   │       │   ├── schemas.py
│   │       │   ├── retrieval_service.py
│   │       │   ├── repository.py
│   │       │   ├── models.py
│   │       │   ├── exceptions.py
│   │       │   ├── ingestion/
│   │       │   │   ├── __init__.py
│   │       │   │   ├── cli.py
│   │       │   │   ├── pipeline.py
│   │       │   │   ├── chunking.py
│   │       │   │   └── loaders.py
│   │       │   ├── embeddings/
│   │       │   │   ├── __init__.py
│   │       │   │   └── embedding_service.py
│   │       │   └── tests/
│   │       │       ├── test_retrieval_service.py
│   │       │       └── test_chunking.py
│   │       │
│   │       └── providers/
│   │           ├── __init__.py
│   │           ├── base.py
│   │           ├── gateway.py
│   │           ├── exceptions.py
│   │           ├── ollama/
│   │           │   ├── __init__.py
│   │           │   ├── client.py
│   │           │   ├── generation.py
│   │           │   └── embeddings.py
│   │           ├── anthropic/
│   │           │   ├── __init__.py
│   │           │   ├── client.py
│   │           │   └── generation.py
│   │           └── tests/
│   │               ├── test_gateway.py
│   │               ├── test_ollama_client.py
│   │               └── test_anthropic_client.py
│   │
│   └── tests/
│       ├── conftest.py
│       ├── integration/
│       │   ├── test_auth_flow.py
│       │   ├── test_session_flow.py
│       │   ├── test_qa_flow.py
│       │   ├── test_research_flow.py
│       │   ├── test_ship30_flow.py
│       │   └── test_router_dispatch.py
│       └── fixtures/
│           └── sample_transcripts/
│               └── .gitkeep
│
└── frontend/
    ├── package.json
    ├── tsconfig.json
    ├── next.config.ts
    ├── tailwind.config.ts
    ├── postcss.config.js
    ├── components.json
    ├── middleware.ts
    ├── .env.local.example
    ├── README.md
    ├── public/
    │   └── favicon.ico
    ├── app/
    │   ├── layout.tsx
    │   ├── globals.css
    │   ├── page.tsx
    │   ├── (auth)/
    │   │   ├── layout.tsx
    │   │   ├── login/
    │   │   │   └── page.tsx
    │   │   ├── register/
    │   │   │   └── page.tsx
    │   │   └── reset-password/
    │   │       └── page.tsx
    │   ├── (workspace)/
    │   │   ├── layout.tsx
    │   │   └── sessions/
    │   │       ├── page.tsx
    │   │       └── [sessionId]/
    │   │           ├── page.tsx
    │   │           └── loading.tsx
    │   └── api/
    │       └── auth/
    │           └── callback/
    │               └── route.ts
    ├── components/
    │   ├── ui/
    │   │   └── .gitkeep
    │   ├── layout/
    │   │   ├── app-shell.tsx
    │   │   ├── top-bar.tsx
    │   │   └── theme-toggle.tsx
    │   ├── auth/
    │   │   ├── login-form.tsx
    │   │   ├── register-form.tsx
    │   │   └── reset-password-form.tsx
    │   ├── sessions/
    │   │   ├── session-sidebar.tsx
    │   │   ├── session-list-item.tsx
    │   │   └── new-session-button.tsx
    │   ├── chat/
    │   │   ├── message-list.tsx
    │   │   ├── message-bubble.tsx
    │   │   ├── chat-input.tsx
    │   │   ├── streaming-indicator.tsx
    │   │   ├── skill-indicator.tsx
    │   │   └── skill-override-selector.tsx
    │   ├── citations/
    │   │   ├── citation-badge.tsx
    │   │   └── citation-source-panel.tsx
    │   └── artifacts/
    │       ├── artifact-panel.tsx
    │       ├── artifact-markdown-view.tsx
    │       ├── artifact-html-view.tsx
    │       ├── artifact-toolbar.tsx
    │       └── artifact-type-badge.tsx
    ├── lib/
    │   ├── utils.ts
    │   ├── api/
    │   │   ├── client.ts
    │   │   ├── auth.ts
    │   │   ├── sessions.ts
    │   │   ├── skills.ts
    │   │   └── artifacts.ts
    │   ├── supabase/
    │   │   ├── client.ts
    │   │   └── server.ts
    │   ├── streaming/
    │   │   └── sse.ts
    │   └── validators/
    │       ├── auth.ts
    │       └── session.ts
    ├── hooks/
    │   ├── use-auth.ts
    │   ├── use-sessions-list.ts
    │   ├── use-session.ts
    │   ├── use-chat-stream.ts
    │   └── use-artifact.ts
    └── types/
        ├── api.ts
        └── domain.ts
```

---

## 2. Purpose of Each Folder

### Root

| Path | Purpose |
|---|---|
| `docs/` | Product/architecture/domain/planning documentation (source of truth, per `CONTEXT.md`). |
| `backend/` | FastAPI service — vertical-slice domains, API, retrieval, model gateway. |
| `frontend/` | Next.js 15 App Router client. |

### Backend

| Path | Purpose |
|---|---|
| `backend/app/` | The FastAPI application package. |
| `backend/app/config/` | **Shared.** Environment/settings loading used by every domain. |
| `backend/app/database/` | **Shared.** Supabase Postgres connection/session management, SQLAlchemy declarative base, Alembic migrations. |
| `backend/app/exceptions/` | **Shared.** Base application exception type and the FastAPI exception-handler registration used by all domains. |
| `backend/app/domains/` | Container for the six locked vertical slices. Nothing lives directly in this folder except `__init__.py`. |
| `backend/app/domains/auth/` | Registration, login, logout, password reset — thin orchestration layer in front of **Supabase Auth** (per `CONTEXT.md`, auth is not custom-built). |
| `backend/app/domains/sessions/` | Session and message lifecycle: create, list (sidebar), resume, persist message history. |
| `backend/app/domains/skills/` | The four skills (QA, Research, Ship30, Artifact) plus the **Router** (auto routing, manual override, skill chaining) that dispatches between them. Routing decisions are recorded to application logs in MVP — no `RoutingDecision` persistence (see §3 below). |
| `backend/app/domains/skills/qa/` | RAG question answering: retrieval → grounded generation → inline citation assembly. |
| `backend/app/domains/skills/research/` | Cross-episode retrieval and synthesis into structured research briefs. |
| `backend/app/domains/skills/ship30/` | Transforms session context into LinkedIn posts, X/Twitter threads, and articles. |
| `backend/app/domains/skills/artifact/` | Direct artifact-producing operations invoked by the router independent of QA/Research (e.g., explicit "turn this into a document"). |
| `backend/app/domains/artifacts/` | Persistence, rendering (Markdown/HTML), copy/download support for artifacts attached to sessions. **No dedicated HTTP router in MVP** — artifact access is exposed through `sessions/router.py`, since artifacts are always accessed in the context of their owning session. |
| `backend/app/domains/knowledge/` | The Lenny Podcast transcript corpus: episodes, transcript chunks, offline ingestion pipeline, runtime retrieval. **Internal domain only** — no HTTP endpoints in MVP. Retrieval is reached exclusively through in-process calls from `skills/qa/` and `skills/research/`. |
| `backend/app/domains/knowledge/ingestion/` | Offline batch pipeline: transcript loading, chunking, embedding, upsert into `pgvector`. Not part of the request/response path. |
| `backend/app/domains/knowledge/embeddings/` | Runtime query-embedding calls (via the `bge-m3`/Ollama provider) used at retrieval time. |
| `backend/app/domains/providers/` | Model Gateway: the primary/secondary abstraction over LLM providers, with graceful degradation. Provider invocation details are recorded to application logs in MVP — no `ModelInvocation` persistence (see §3 below). |
| `backend/app/domains/providers/ollama/` | Primary provider client (generation + `bge-m3` embeddings). |
| `backend/app/domains/providers/anthropic/` | Secondary/fallback provider client (Claude SDK). |
| `backend/tests/` | Cross-domain integration tests that exercise a full request flow (message → route → skill → artifact), as opposed to the domain-local unit tests colocated inside each slice. |
| `backend/tests/fixtures/` | Shared test fixtures, including sample transcript data for retrieval/ingestion tests. |

Each domain's own `tests/` subfolder holds unit tests for that slice only — this keeps tests colocated with the code they verify, consistent with vertical slice ownership.

### Frontend

| Path | Purpose |
|---|---|
| `frontend/app/` | Next.js App Router route tree. |
| `frontend/app/(auth)/` | Route group for unauthenticated pages (login, register, reset password); shares a minimal auth layout. Parentheses exclude it from the URL path. |
| `frontend/app/(workspace)/` | Route group for the authenticated app shell (sidebar + chat + artifact panel); layout enforces auth. |
| `frontend/app/(workspace)/sessions/[sessionId]/` | The core chat workspace for a single session. |
| `frontend/app/api/` | Next.js Route Handlers for server-side concerns that must not run in the browser (e.g., the Supabase auth callback). |
| `frontend/components/ui/` | Generated shadcn/ui primitives (button, dialog, input, etc.) — left unedited; app logic never lives here. |
| `frontend/components/layout/` | App shell chrome: overall layout, top bar, theme toggle. |
| `frontend/components/auth/` | Auth form components (register/login/reset). |
| `frontend/components/sessions/` | Session sidebar and session list UI. |
| `frontend/components/chat/` | Chat transcript UI: message list/bubbles, input, streaming state, skill indicator, manual override control. |
| `frontend/components/citations/` | Inline citation badge and the expandable source panel (episode, timestamp, transcript excerpt). |
| `frontend/components/artifacts/` | Artifact side panel: Markdown/HTML rendering, copy/download toolbar. |
| `frontend/lib/api/` | Typed client functions calling the FastAPI backend, one module per domain. |
| `frontend/lib/supabase/` | Browser and server Supabase client instances (used for Supabase Auth). |
| `frontend/lib/streaming/` | Client-side parsing helpers for streamed skill responses. |
| `frontend/lib/validators/` | Form/input validation schemas. |
| `frontend/hooks/` | Reusable client hooks wrapping data fetching, streaming, and auth state. |
| `frontend/types/` | Shared TypeScript types mirroring backend Pydantic schemas and domain entities. |

---

## 3. Purpose of Each File

### Backend — Shared

| File | Purpose |
|---|---|
| `backend/app/main.py` | FastAPI app instantiation; registers exception handlers and includes each domain's `router.py`. |
| `backend/pyproject.toml` / `requirements.txt` | Python dependency and tooling configuration. |
| `backend/alembic.ini` | Alembic configuration pointing at `app/database/migrations/`. |
| `backend/.env.example` | Documents required environment variables (Supabase, Ollama, Anthropic) without real values. |
| `backend/app/config/settings.py` | Typed settings object (env-var driven) consumed by every domain — the single place configuration is read from. |
| `backend/app/database/base.py` | SQLAlchemy declarative base class that every domain's `models.py` inherits from. |
| `backend/app/database/session.py` | Async DB session/connection factory and the `get_db` FastAPI dependency. |
| `backend/app/database/migrations/env.py` | Alembic migration runtime environment. |
| `backend/app/database/migrations/versions/` | Generated migration files (one per schema change). |
| `backend/app/exceptions/base.py` | Root `AppError` exception type that all domain-specific exceptions inherit from. |
| `backend/app/exceptions/handlers.py` | FastAPI exception handlers mapping `AppError` subclasses to HTTP responses. |

### Backend — `auth/`

| File | Purpose |
|---|---|
| `router.py` | HTTP endpoints: register, login, logout, password reset. |
| `schemas.py` | Request/response models (`RegisterRequest`, `LoginRequest`, `PasswordResetRequest`, etc.). |
| `service.py` | Orchestrates calls to Supabase Auth; contains no password-handling logic of its own since Supabase Auth owns credential storage. |
| `dependencies.py` | `get_current_user` and related auth-guard dependencies consumed by other domains. |
| `supabase_client.py` | Thin wrapper around the Supabase Auth SDK client. |
| `exceptions.py` | e.g., `InvalidCredentialsError`, `ResetTokenExpiredError`. |
| `tests/` | Unit tests for the router and service in isolation. |

### Backend — `sessions/`

| File | Purpose |
|---|---|
| `router.py` | Endpoints: create session, list sessions, get session (with history), post message — and, per the MVP simplification, list/retrieve/download the artifacts attached to a session. Consolidates the artifact HTTP surface here since `artifacts/router.py` was removed; delegates to `artifacts/service.py` for the actual logic. |
| `schemas.py` | `SessionCreate`, `SessionRead`, `MessageRead`, etc. |
| `service.py` | Session lifecycle logic (title derivation from first message, recency ordering). |
| `repository.py` | Data-access layer for `Session`/`Message` rows. |
| `models.py` | SQLAlchemy models: `Session`, `Message` (per `DOMAIN_MODEL.md`). |
| `dependencies.py` | e.g., `get_owned_session` — resolves a session and enforces it belongs to the current user. |
| `exceptions.py` | e.g., `SessionNotFoundError`. |
| `tests/` | Router/service/repository unit tests. |

### Backend — `skills/` (router/dispatch layer)

| File | Purpose |
|---|---|
| `router.py` | The HTTP endpoint that receives a user message for a session and returns the (streamed) skill result. |
| `schemas.py` | Shared skill I/O contracts: `SkillContext`, `SkillResult`, `SkillInvocationRequest`. |
| `base.py` | The `Skill` protocol/interface every skill module (`qa`, `research`, `ship30`, `artifact`) implements. |
| `skill_router.py` | The routing **engine**: auto-classification, manual override handling, and skill chaining logic described in `CONTEXT.md`. Distinct from `router.py` (HTTP layer) — this is the domain logic the HTTP layer calls into. Emits a structured application-log entry per routing decision (selected skill, mode, confidence) — **no `RoutingDecision` database persistence in MVP** (delayed; see §3 "Downstream impacts" in the change summary). Auto-routing, manual override precedence, and skill-chaining behavior are unchanged. |
| `exceptions.py` | e.g., `UnroutableMessageError`. |
| `tests/test_skill_router.py` | Tests for auto-routing, manual override precedence, and chaining behavior. |

### Backend — `skills/qa/`, `skills/research/`, `skills/ship30/`, `skills/artifact/`

| File | Purpose |
|---|---|
| `qa/service.py` | Implements the QA `Skill`: retrieval call → grounded generation → citation assembly. |
| `qa/prompts.py` | Prompt templates for grounded QA generation. |
| `qa/citation_builder.py` | Builds `Citation` records strictly from retrieval metadata (never free-generated), per the grounding requirement. |
| `research/service.py` | Implements the Research `Skill`: multi-episode retrieval → synthesis. |
| `research/synthesis.py` | Structuring logic for the brief (summary, per-guest perspectives, agreement/disagreement). |
| `research/prompts.py` | Prompt templates for cross-episode synthesis. |
| `ship30/service.py` | Implements the Ship30 `Skill`: dispatches to the correct formatter based on requested content type. |
| `ship30/formatters/linkedin.py` | LinkedIn post formatting/constraints. |
| `ship30/formatters/x_thread.py` | Thread segmentation logic (per-tweet splitting). |
| `ship30/formatters/article.py` | Long-form article formatting. |
| `artifact/service.py` | Implements the Artifact `Skill`: direct artifact-producing operations invoked via the router (distinct from the `artifacts/` domain's persistence/CRUD). |
| `*/schemas.py` | Skill-specific request/response shapes. |
| `*/tests/test_service.py` | Per-skill unit tests. |

### Backend — `artifacts/`

**No `router.py` in MVP.** Artifacts have no dedicated HTTP surface — they are created internally by skills and exposed to clients exclusively through `sessions/router.py` (`GET`-style list/retrieve/download of a session's artifacts), which calls into `service.py` below.

| File | Purpose |
|---|---|
| `schemas.py` | `ArtifactCreate`, `ArtifactRead`, `ResearchBriefRead`. |
| `service.py` | Artifact lifecycle logic; enforces Markdown as the canonical source of truth. Invoked by skill modules (to create artifacts) and by `sessions/router.py` (to read/download them). |
| `repository.py` | Data-access layer for `Artifact`/`ResearchBrief` rows. |
| `models.py` | SQLAlchemy models: `Artifact`, `ResearchBrief` (per `DOMAIN_MODEL.md`). |
| `renderers/markdown_renderer.py` | Passthrough/formatting for the canonical Markdown view. |
| `renderers/html_renderer.py` | Sanitized HTML derivation from `content_markdown` for the HTML rendering mode. |
| `exceptions.py` | e.g., `ArtifactNotFoundError`. |
| `tests/` | Service/renderer unit tests, including sanitization tests. HTTP-level artifact-access behavior is now covered by `sessions/tests/test_router.py`. |

### Backend — `knowledge/`

**No `router.py` in MVP.** Knowledge is an internal-only domain in MVP — retrieval is reached exclusively via in-process calls from `skills/qa/service.py` and `skills/research/service.py`; no HTTP endpoint (including debug/tooling) is exposed.

| File | Purpose |
|---|---|
| `schemas.py` | `TranscriptChunkRead`, `EpisodeRead`, `CitationRead`. |
| `retrieval_service.py` | Runtime `search(query_text, k, filters) -> TranscriptChunk[]`, called in-process by the QA and Research skills only. |
| `repository.py` | pgvector similarity-search queries and episode/chunk lookups. |
| `models.py` | SQLAlchemy models: `Episode`, `TranscriptChunk`, `Citation` (per `DOMAIN_MODEL.md`). |
| `exceptions.py` | e.g., `InsufficientGroundingError` (no relevant chunks found). |
| `ingestion/cli.py` | Command-line entrypoint to run the offline ingestion pipeline. |
| `ingestion/pipeline.py` | Orchestrates the ingestion sequence: load → chunk → embed → upsert. |
| `ingestion/chunking.py` | Transcript chunking strategy. |
| `ingestion/loaders.py` | Reads raw transcript/episode metadata from source files. |
| `embeddings/embedding_service.py` | Calls the Ollama provider's `bge-m3` embedding endpoint for both ingestion and query-time embedding. |
| `tests/` | Retrieval and chunking unit tests against fixture transcripts. |

### Backend — `providers/`

| File | Purpose |
|---|---|
| `base.py` | The `ModelProvider` protocol (`generate`, `stream`, `embed`) both `ollama` and `anthropic` implement. |
| `gateway.py` | The Model Gateway: attempts Ollama first, fails over to Claude on timeout/health-check failure. Emits a structured application-log entry per invocation (provider, whether it was a fallback, latency) — **no `ModelInvocation` database persistence in MVP** (delayed; see §3 "Downstream impacts" in the change summary). Graceful-degradation/fallback behavior itself is unchanged. |
| `exceptions.py` | e.g., `ProviderUnavailableError`. |
| `ollama/client.py` | Low-level HTTP client for the local Ollama server. |
| `ollama/generation.py` | Text-generation calls against Ollama (primary path). |
| `ollama/embeddings.py` | `bge-m3` embedding calls against Ollama. |
| `anthropic/client.py` | Claude SDK client wrapper. |
| `anthropic/generation.py` | Text-generation calls against Claude (secondary/fallback path). |
| `tests/test_gateway.py` | Failover behavior tests (forced Ollama outage → Claude fallback). |

### Backend — top-level `tests/`

| File | Purpose |
|---|---|
| `conftest.py` | Shared pytest fixtures (test DB session, authenticated test client, seeded fixture data). |
| `integration/test_*_flow.py` | End-to-end flow tests spanning multiple domains (e.g., message → router → QA skill → artifact). |
| `fixtures/sample_transcripts/` | Small transcript corpus used by ingestion/retrieval tests, avoiding dependency on the full corpus. |

### Frontend — root config

| File | Purpose |
|---|---|
| `package.json` | Dependencies and scripts. |
| `tsconfig.json` | TypeScript compiler configuration. |
| `next.config.ts` | Next.js configuration. |
| `tailwind.config.ts` | Tailwind theme/tokens configuration. |
| `postcss.config.js` | PostCSS pipeline for Tailwind. |
| `components.json` | shadcn/ui CLI configuration (paths, aliases). |
| `middleware.ts` | Route-level auth guard redirecting unauthenticated requests away from `(workspace)`. |
| `.env.local.example` | Documents required frontend env vars (Supabase URL/key, backend API base URL). |

### Frontend — `app/`

| File | Purpose |
|---|---|
| `layout.tsx` | Root layout: fonts, global providers, `globals.css` import. |
| `globals.css` | Tailwind base layers and global styles. |
| `page.tsx` | Root route; redirects to login or the workspace depending on auth state. |
| `(auth)/layout.tsx` | Minimal centered layout for auth pages. |
| `(auth)/login/page.tsx`, `register/page.tsx`, `reset-password/page.tsx` | Auth pages, each rendering the corresponding form component. |
| `(workspace)/layout.tsx` | Authenticated shell: renders `AppShell` (sidebar + top bar), enforces auth. |
| `(workspace)/sessions/page.tsx` | Empty/default state before a session is selected. |
| `(workspace)/sessions/[sessionId]/page.tsx` | The chat + artifact panel view for one session. |
| `(workspace)/sessions/[sessionId]/loading.tsx` | Loading UI while session history is fetched. |
| `api/auth/callback/route.ts` | Server-side Supabase Auth callback handler. |

### Frontend — `components/`

| File | Purpose |
|---|---|
| `layout/app-shell.tsx` | Composes sidebar + top bar + main content area. |
| `layout/top-bar.tsx` | Top navigation bar. |
| `layout/theme-toggle.tsx` | Light/dark theme switch. |
| `auth/login-form.tsx`, `register-form.tsx`, `reset-password-form.tsx` | Auth forms calling `lib/api/auth.ts`. |
| `sessions/session-sidebar.tsx` | Session list panel; drives session navigation. |
| `sessions/session-list-item.tsx` | Single session row (title, timestamp). |
| `sessions/new-session-button.tsx` | Creates a new session and navigates to it. |
| `chat/message-list.tsx` | Renders the ordered message history for the active session. |
| `chat/message-bubble.tsx` | Single message (user or assistant), including inline citation markers. |
| `chat/chat-input.tsx` | Message composer. |
| `chat/streaming-indicator.tsx` | Visual state while a response is streaming (including degraded-mode indication). |
| `chat/skill-indicator.tsx` | Shows which skill handled a given assistant message. |
| `chat/skill-override-selector.tsx` | Manual skill override control (Auto/QA/Research/Ship30). |
| `citations/citation-badge.tsx` | Inline citation marker within a message. |
| `citations/citation-source-panel.tsx` | Expandable panel showing episode name, timestamp, transcript excerpt. |
| `artifacts/artifact-panel.tsx` | Side panel container for the active artifact. |
| `artifacts/artifact-markdown-view.tsx` | Markdown rendering mode. |
| `artifacts/artifact-html-view.tsx` | Sanitized HTML rendering mode. |
| `artifacts/artifact-toolbar.tsx` | Copy and Download-as-Markdown actions. |
| `artifacts/artifact-type-badge.tsx` | Visual label for artifact type (QA answer, research brief, LinkedIn post, thread, article). |

### Frontend — `lib/`, `hooks/`, `types/`

| File | Purpose |
|---|---|
| `lib/utils.ts` | Shared helpers, including the shadcn/ui `cn()` class-merge utility. |
| `lib/api/client.ts` | Base fetch wrapper (auth header injection, error normalization). |
| `lib/api/auth.ts` | Auth API calls (register/login/logout/reset). |
| `lib/api/sessions.ts` | Session/message API calls. |
| `lib/api/skills.ts` | Skill-invocation API calls (message send, manual override param). |
| `lib/api/artifacts.ts` | Artifact fetch/download API calls. |
| `lib/supabase/client.ts` | Browser-side Supabase client instance. |
| `lib/supabase/server.ts` | Server-side Supabase client instance (used in Route Handlers/Server Components). |
| `lib/streaming/sse.ts` | Parses streamed skill responses into incremental UI updates. |
| `lib/validators/auth.ts`, `session.ts` | Form validation schemas. |
| `hooks/use-auth.ts` | Current-user/auth-state hook. |
| `hooks/use-sessions-list.ts` | Fetches/subscribes to the session sidebar list. |
| `hooks/use-session.ts` | Loads a single session's message history and artifacts. |
| `hooks/use-chat-stream.ts` | Manages sending a message and consuming the streamed response. |
| `hooks/use-artifact.ts` | Loads/copies/downloads a single artifact. |
| `types/api.ts` | Types mirroring backend Pydantic response schemas. |
| `types/domain.ts` | Domain entity types (`Session`, `Message`, `Artifact`, `Citation`, etc.), aligned to `DOMAIN_MODEL.md`. |

---

## 4. Recommended Naming Conventions

### Backend (Python / FastAPI)

- **Files**: `snake_case`. Within each domain folder, files are named by **role**, not by domain-prefixed names — `router.py`, `schemas.py`, `service.py`, `repository.py`, `models.py`, `exceptions.py`, `dependencies.py`. Identity comes from the package path (`app.domains.sessions.service`), so avoid stutter like `session_service.py`.
- **Classes**: `PascalCase`. SQLAlchemy models are singular (`Session`, `Message`, `Artifact`, `ResearchBrief`, `Episode`, `TranscriptChunk`, `Citation`) — matching `DOMAIN_MODEL.md` exactly. `RoutingDecision` and `ModelInvocation` are documented entities in `DOMAIN_MODEL.md` but are **not implemented as models in MVP** — they are logged, not persisted (see §3 "Downstream impacts" in the change summary).
- **Database tables**: `snake_case`, plural (`users`, `sessions`, `messages`, `artifacts`, `research_briefs`, `episodes`, `transcript_chunks`, `citations`, `password_reset_tokens`). `routing_decisions` and `model_invocations` are intentionally **not** created in MVP.
- **Pydantic schemas**: suffix by purpose — `{Entity}Create`, `{Entity}Update`, `{Entity}Read` (or `{Entity}Response`), `{Entity}Base` for shared fields.
- **Exceptions**: suffix `Error`, inherit from the domain's local base which inherits shared `app.exceptions.base.AppError` (e.g., `SessionNotFoundError`, `ProviderUnavailableError`).
- **Skill implementations**: one class per skill implementing the `skills/base.py` `Skill` protocol — `QASkill`, `ResearchSkill`, `Ship30Skill`, `ArtifactSkill` — so the router/dispatcher can treat them polymorphically.
- **Provider implementations**: one class per provider implementing `providers/base.py` — `OllamaProvider`, `AnthropicProvider`.
- **Tests**: `test_<module>.py`, colocated in each domain's `tests/` package; cross-domain flow tests live only in top-level `backend/tests/integration/` as `test_<flow>_flow.py`.
- **Environment variables**: `UPPER_SNAKE_CASE`, prefixed by concern — `SUPABASE_URL`, `SUPABASE_SERVICE_KEY`, `OLLAMA_BASE_URL`, `OLLAMA_GENERATION_MODEL`, `ANTHROPIC_API_KEY`.

### Frontend (Next.js / TypeScript)

- **Files**: `kebab-case` for every file — components, hooks, lib modules (`message-bubble.tsx`, `use-chat-stream.ts`, `citation-source-panel.tsx`).
- **Components**: exported component name is `PascalCase`, matching the kebab-case filename (`message-bubble.tsx` → `MessageBubble`).
- **Hooks**: filename and exported function both use the `use-`/`use` prefix (`use-chat-stream.ts` → `useChatStream`).
- **Route segments**: lowercase kebab-case; route groups in parentheses (`(auth)`, `(workspace)`) to structure layouts without affecting the URL; dynamic segments in brackets (`[sessionId]`).
- **Types**: `PascalCase`, and where possible named to mirror the backend schema one-to-one (backend `SessionRead` ↔ frontend `Session` in `types/domain.ts`).
- **shadcn/ui boundary**: generated primitives in `components/ui/` are never hand-edited or mixed with feature logic; feature composition happens exclusively in `components/{chat,sessions,artifacts,citations,auth,layout}/`.
- **Tailwind**: styling goes through `tailwind.config.ts` theme tokens, not ad hoc arbitrary values, to keep the design system consistent across QA answers, research briefs, and generated content views.

### Repository-wide

- Top-level and mid-level folders: `kebab-case` or plain lowercase (`backend`, `frontend`, `docs`).
- Documentation files: `UPPER_SNAKE_CASE.md`, consistent with the existing `PRD.md` / `ARCHITECTURE.md` / `DOMAIN_MODEL.md` / `IMPLEMENTATION_PLAN.md` set.
- No `Dockerfile` / `docker-compose.yml` at this stage — explicitly excluded per `CONTEXT.md` ("No Docker for MVP").
