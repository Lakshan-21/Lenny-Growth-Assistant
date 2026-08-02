# Lenny Growth Workspace — Frontend (Phase 1 + Phase 2)

Workspace UI for querying, researching, and repurposing insights from
Lenny's Podcast. Phase 1 covered chat sessions and QA with citations; Phase 2
adds a tabbed right panel (Sources / Artifacts / Research), artifact
browsing/download, a Research mode in the composer, and Ship30 content
generation from any artifact. Built against the existing FastAPI backend —
no backend changes were made for either phase.

## Scope

**Implemented (Phase 1)**

- Session list (sidebar), create session, switch session
- Message history for a session, sending new messages
- Markdown rendering of assistant responses (`react-markdown` + `remark-gfm`,
  no `dangerouslySetInnerHTML`)
- Sources tab with citation excerpts, linked to the message that produced them

**Implemented (Phase 2)**

- Right-panel tabs: Sources / Artifacts / Research
- Artifacts: list, open (inline detail view), download (`.md`), metadata
  (type badge, relative timestamp)
- Research: a mode toggle in the composer (`mode="manual", skill="research"`),
  a dedicated Research tab showing synthesized briefs (a filtered view of the
  same Artifacts list), auto-refresh of the artifacts/research lists after a
  successful run
- Ship30: generate a LinkedIn post / X thread / article from any open
  artifact, with an editable instruction field; the result appears both as a
  new artifact and as a new assistant chat turn (that's how the backend
  persists it)

**Explicitly out of scope for Phase 2** (not implemented): authentication,
streaming, router auto-classification (skill selection is always explicit —
QA by default, or the user's Research/Ship30 choice), advanced styling
polish.

## Stack

Next.js 15 (App Router) · TypeScript (strict) · Tailwind CSS v3 · shadcn/ui
(New York style, Radix primitives incl. Tabs) · TanStack Query v5 ·
react-markdown

## Design system

Claude-inspired, not a literal clone: a warm cream/terracotta palette (HSL
CSS variables in `app/globals.css`, with a `.dark` variant), Inter for UI
chrome, and Source Serif 4 reserved specifically for quoted transcript
excerpts in the Sources tab — the one place this app quotes source material
verbatim. Assistant messages render like a document (no bubble), matching
Claude.ai's actual style; user messages sit in a soft right-aligned bubble.
Numbered terracotta citation markers connect a chat answer to its sources.
Phase 2 reuses this system as-is (new tabs, badges, and the artifact detail
view all draw from the same tokens and primitives) rather than introducing a
second visual language.

## Folder structure

```
frontend/
├── app/
│   ├── layout.tsx                  # Root layout, fonts, <Providers>
│   ├── page.tsx                    # "/" → redirects to "/sessions"
│   ├── providers.tsx                # QueryClientProvider
│   ├── globals.css                  # Design tokens, markdown-body styles
│   └── (workspace)/
│       ├── layout.tsx               # 3-pane shell: sidebar / chat / right panel
│       └── sessions/
│           ├── page.tsx             # "/sessions" empty state
│           └── [sessionId]/
│               └── page.tsx         # Chat page for one session
├── components/
│   ├── ui/                          # shadcn primitives (button, textarea, tabs, ...)
│   ├── sessions/                    # Sidebar, session list item, new-session button
│   ├── chat/                        # Message list/bubble, chat input (+ Research toggle), empty state
│   ├── citations/                   # Sources tab, citation card
│   ├── artifacts/                   # Artifacts tab, list item, detail view, Ship30 actions
│   ├── research/                    # Research tab (filtered artifacts list)
│   └── right-panel/                 # Tabs shell wrapping Sources/Artifacts/Research
├── hooks/
│   ├── use-sessions.ts              # List + create session
│   ├── use-session.ts               # Get one session
│   ├── use-send-message.ts          # Send message mutation (QA or Research mode)
│   ├── use-artifacts.ts             # List artifacts for a session
│   ├── use-generate-ship30.ts       # Generate LinkedIn/X-thread/article from an artifact
│   └── use-right-panel.tsx          # Cross-tree right-panel state (active tab + citations)
├── lib/
│   ├── api/                         # Typed fetch client + endpoint wrappers (sessions, skills, artifacts)
│   ├── artifact-labels.ts           # Artifact type → display label map
│   ├── query-client.ts
│   └── utils.ts                     # cn(), formatRelativeTime()
├── types/domain.ts                  # Types mirroring backend Pydantic schemas
├── eslint.config.mjs
├── tailwind.config.ts
└── .env.local.example
```

## How Phase 2 maps to the backend

No backend changes were made — Phase 2 is entirely a new frontend surface
over endpoints that already existed:

| Frontend feature | Backend endpoint |
|---|---|
| Artifacts list | `GET /sessions/{id}/artifacts` |
| Artifact download | `GET /sessions/{id}/artifacts/{artifact_id}/download` |
| Research mode | `POST /sessions/{id}/messages` with `mode="manual", skill="research"` |
| Ship30 generation | `POST /sessions/{id}/messages` with `mode="manual", skill="ship30", content_type, source_artifact_id` |

"Open artifact" renders `content_markdown` client-side (the same
`react-markdown` pipeline used for chat messages) rather than calling a
dedicated get-by-id endpoint — the list response already carries full
content, so a second fetch would just be redundant.

## Run instructions

**Prerequisites**: Node.js 20+, the backend running locally with
`DEV_AUTH_BYPASS=true` (still no login UI — see backend README).

```bash
cd frontend
npm install
cp .env.local.example .env.local   # defaults to http://localhost:8000
npm run dev
```

Open http://localhost:3000 — it redirects to `/sessions`.

Other scripts:

```bash
npm run build       # production build
npm run start        # serve the production build
npm run lint          # ESLint (flat config, next/core-web-vitals + next/typescript)
npm run typecheck   # tsc --noEmit
```

## Trying the Phase 2 workflows

1. **Artifacts**: start a session, ask a question or two, open the
   **Artifacts** tab — QA answers don't produce artifacts (only Research and
   Ship30 outputs do; QA's citations live in the Sources tab instead), so
   this tab stays empty until you run one of those.
2. **Research**: in the composer, click **Research** (next to **Ask**), type
   a topic, and send. The right panel jumps to the **Research** tab once the
   brief is synthesized. Research briefs also show up in **Artifacts**.
3. **Ship30**: open any artifact (a research brief, or a prior Ship30
   output), scroll to **Repurpose this with Ship30**, optionally edit the
   instruction, and click LinkedIn / X thread / Article. The new piece
   appears as both a new artifact and a new assistant message in the chat.

## Verification performed

- `npm install` — clean install (Phase 2 adds one dependency,
  `@radix-ui/react-tabs`)
- `npm run typecheck` — no errors
- `npm run lint` — no errors
- `npm run build` — production build succeeds; all 4 routes compile
  (`/`, `/sessions`, `/sessions/[sessionId]`, `/_not-found`)
- **Not performed**: a live click-through against a running backend, or
  screenshots. This sandbox has no backend instance running (Postgres +
  Ollama aren't up) and no browser-automation tool available to drive one.
  Everything above reflects real command output, not a claim about runtime
  behavior beyond what static compilation can prove — please run `npm run
  dev` against your own backend to confirm the workflows in the previous
  section before relying on this.

## Known limitations

- **Citations are session-local, not persisted** (unchanged from Phase 1).
  `GET /sessions/{id}` doesn't return citations for historical messages —
  only the live `POST /messages` response carries them. Session-local, not
  a backend gap this frontend phase is scoped to fix.
- **No streaming.** Sends block on the full response, including Research
  (which can take noticeably longer — multiple retrieval calls plus
  synthesis) and Ship30 generations.
- **No auth UI.** Relies on the backend's `DEV_AUTH_BYPASS`.
- **QA answers are never artifacts.** By backend design (`qa/service.py`
  never sets `artifact_type`), so a QA answer never appears in the
  Artifacts tab and can't be selected as a Ship30 source in this UI — only
  Research briefs and prior Ship30 outputs can. (The backend also supports
  omitting `source_artifact_id` entirely, which falls back to the session's
  last assistant message, but this UI always passes the explicit id of the
  artifact you have open, so that fallback path is never exercised here.)
