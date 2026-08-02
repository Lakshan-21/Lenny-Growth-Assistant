# Product Requirements Document: Lenny Growth Workspace

| | |
|---|---|
| **Status** | Draft |
| **Version** | 0.1.0 |
| **Owner** | Product / Engineering |
| **Last Updated** | 2026-08-02 |

---

## 1. Summary

Lenny Growth Workspace is an AI-powered workspace that lets product, growth, and startup professionals explore, question, and repurpose the accumulated knowledge inside **Lenny's Podcast**. Instead of listening to hours of episodes or manually searching transcripts, users converse with a workspace that retrieves grounded answers, synthesizes cross-episode research, and turns insights into publishable content — all inside session-based, artifact-producing chat workspace.

## 2. Problem Statement

Lenny's Podcast has published hundreds of long-form episodes containing dense, tactical advice from operators, founders, and growth leaders. This knowledge is:

- **Hard to search** — buried in unstructured audio/transcript form with no semantic search.
- **Hard to synthesize** — insights on a topic (e.g., "activation metrics") are scattered across dozens of episodes with no way to compare or reconcile guest opinions.
- **Hard to reuse** — practitioners who want to turn a podcast insight into a LinkedIn post, thread, or brief must manually re-listen, extract, and rewrite.

There is no existing tool that lets a user ask a grounded question against the podcast corpus, receive a cited answer, escalate that answer into a structured research brief, and then transform it into ready-to-publish content — in one continuous, session-persisted workflow.

## 3. Goals

- Provide **grounded, cited question-answering** over the full Lenny's Podcast transcript corpus.
- Enable **cross-episode research synthesis** so users can compare and reconcile perspectives across guests and episodes.
- Let users **transform insights into publishable content** (LinkedIn posts, X/Twitter threads, articles) without leaving the workspace.
- Persist all work as **sessions** with full history, so users can resume, branch, and revisit prior exploration.
- Produce durable **artifacts** (Markdown/HTML) that can be copied or downloaded independent of the chat transcript.
- Operate reliably against a **local-first model stack** (Ollama) with **graceful degradation** to a hosted model (Claude) when needed.

## 4. Non-Goals

- Ingesting or indexing podcasts other than Lenny's Podcast (v1 scope is single-corpus).
- Real-time transcription of new episodes as they air (ingestion is a batch/offline pipeline, not covered by this PRD).
- Multi-user real-time collaboration within a single session (sessions are single-owner in v1).
- Publishing directly to LinkedIn/X on the user's behalf (the workspace produces content; publishing is manual/out-of-scope).
- Fine-tuning or training custom models on podcast content.

## 5. Target Users & Personas

| Persona | Description | Primary Jobs-to-be-Done |
|---|---|---|
| **Growth PM** | Product manager researching a specific growth lever (e.g., onboarding, activation) | Ask targeted questions, get cited answers fast |
| **Founder/Operator** | Early-stage founder pattern-matching against operator advice | Cross-episode research briefs, compare guest viewpoints |
| **Content Creator / Marketer** | Writes about product/growth topics for an audience | Turn podcast insights into LinkedIn posts, threads, articles |
| **Analyst/Researcher** | Compiles structured writeups on a theme for internal use | Research briefs with citations, downloadable artifacts |

## 6. Core Capabilities

### 6.1 Authentication
- **Register** — email/password account creation.
- **Login** — authenticated session establishment.
- **Logout** — session/token invalidation.
- **Password Reset** — self-service reset via emailed link/token.

**Acceptance criteria:**
- Users can only access their own sessions and artifacts.
- Passwords are never stored or logged in plaintext.
- Password reset links expire and are single-use.

### 6.2 Session Management
- **Create session** — start a new chat-based workspace session.
- **View session history** — list past sessions with titles/timestamps in a sidebar.
- **Continue previous sessions** — reopen a session and resume with full prior context (messages + artifacts).

**Acceptance criteria:**
- Sessions persist across logout/login.
- Reopening a session restores message history and any attached artifacts in their original state.
- Session list is ordered by recency and supports basic identification (auto-generated title from first message).

### 6.3 QA Skill (Question Answering)
- **RAG over Lenny podcast transcripts** — retrieval-augmented answers grounded in transcript chunks.
- **Inline citations** — every substantive claim links to the source episode/timestamp/segment.
- **Source grounding** — answers must be traceable to retrieved passages; the system should avoid answering from parametric knowledge alone when a factual/attributable claim is being made about podcast content.

**Acceptance criteria:**
- Every QA response includes at least one inline citation when the answer draws on podcast content.
- Citations resolve to identifiable source metadata (episode title, guest, approximate timestamp/segment).
- The system indicates when it cannot find sufficient grounding for a question rather than fabricating an answer.

### 6.4 Research Skill
- **Cross-episode analysis** — retrieve and synthesize relevant passages from multiple episodes on a topic.
- **Research briefs** — structured, multi-section output (e.g., summary, key perspectives by guest, areas of agreement/disagreement, citations).

**Acceptance criteria:**
- A research brief cites multiple distinct episodes when the topic has multi-episode coverage.
- Briefs are structured (headings/sections), not a single undifferentiated paragraph.
- Briefs are produced as artifacts (see 6.6) and attached to the session.

### 6.5 Ship30 Skill (Content Generation)
- **LinkedIn posts** — long-form professional post generation from a source insight/brief.
- **X/Twitter threads** — multi-tweet thread generation with per-tweet segmentation.
- **Articles** — longer-form structured article generation.

**Acceptance criteria:**
- Generated content is derived from and attributed to session context (prior QA/Research output) when such context exists.
- Output respects platform constraints (e.g., thread segmentation for X, character-length awareness).
- Each output type is produced as a distinct artifact.

### 6.6 Artifact System
- **Markdown rendering** — artifacts render as formatted Markdown in the UI.
- **HTML rendering** — artifacts can render as sanitized HTML for richer preview.
- **Copy** — one-click copy of artifact content to clipboard.
- **Download** — download artifact as a `.md` file.

**Acceptance criteria:**
- Artifacts are versioned/attached to the session and message that produced them.
- Copy and download always reflect the currently rendered artifact content exactly (no lossy transformation).
- HTML rendering is sanitized to prevent injection of unsafe markup.

### 6.7 Skill Router
- **Auto routing** — the system infers which skill (QA, Research, Ship30, Artifact) should handle a given user message.
- **Manual override** — users can explicitly select a skill, bypassing auto-routing.

**Acceptance criteria:**
- Auto-routing correctly classifies intent for clearly-scoped requests (e.g., "write a LinkedIn post about X" → Ship30).
- Manual override is available from the UI on every message and takes precedence over auto-routing.
- The active skill for a given turn is visible to the user (transparency of routing decision).

## 7. User Stories

1. *As a growth PM*, I want to ask "What do guests say about activation metrics?" and get a cited answer, so I can trust the response is grounded in real episodes.
2. *As a founder*, I want to request a research brief on "pricing strategy for PLG startups," so I can see how different guests' advice compares.
3. *As a content creator*, I want to turn a research brief into a LinkedIn post, so I don't have to rewrite the insight from scratch.
4. *As a returning user*, I want to see my past sessions in a sidebar and reopen one, so I can continue work without losing context.
5. *As a user*, I want to download an artifact as Markdown, so I can paste it into my own notes or CMS.
6. *As a user*, I want to manually pick "Research" instead of relying on auto-routing, when I know exactly what I want.
7. *As a user*, I want the system to keep working (in a degraded mode) if the local model is unavailable, rather than failing outright.

## 8. Non-Functional Requirements

| Category | Requirement |
|---|---|
| **Grounding & Trust** | QA and Research outputs must be traceable to source transcripts via citations; no un-cited factual claims about podcast content. |
| **Availability** | Model layer must degrade gracefully (Ollama → Claude) rather than hard-failing a user-facing request. |
| **Security** | Auth tokens, session data, and artifacts must be scoped per-user with no cross-user data leakage. |
| **Performance** | QA responses should begin streaming within a low-latency budget appropriate for a conversational UI; retrieval must scale with corpus growth via vector indexing (pgvector). |
| **Data Integrity** | Session history and artifacts must be durably persisted (Supabase Postgres) and survive service restarts. |
| **Extensibility** | New skills should be addable to the router without restructuring existing skills. |
| **Auditability** | Routing decisions (auto vs. manual, which skill was invoked) should be recorded per message for debugging and evaluation. |

## 9. Success Metrics

- **Citation coverage**: % of QA/Research responses with at least one valid inline citation.
- **Routing accuracy**: % of auto-routed messages that did not require manual override/correction.
- **Session resumption rate**: % of sessions reopened and continued (vs. abandoned after one turn).
- **Artifact conversion rate**: % of QA/Research sessions that produce a downstream Ship30 artifact.
- **Model availability**: % of requests served successfully (including via degraded fallback) vs. hard failures.

## 10. Risks & Assumptions

| Risk | Mitigation |
|---|---|
| Transcript corpus has gaps/errors (ASR quality) | Source grounding should expose confidence/limits; avoid overclaiming. |
| Local model (Ollama) unavailable or under-resourced | Secondary Claude SDK path with graceful degradation. |
| Router misclassifies intent, frustrating users | Always expose manual override; log routing decisions for iteration. |
| Citation hallucination (model cites content not actually retrieved) | Citations must be generated from retrieval metadata, not free-text generation. |
| Content generation (Ship30) drifts from source material | Ship30 outputs should be explicitly derived from session artifacts/QA context, not ungrounded generation. |

**Assumptions:**
- A transcript ingestion/chunking/embedding pipeline for Lenny's Podcast exists or will be built as a prerequisite (out of scope for this PRD, in scope for architecture).
- Users have individual accounts; there is no anonymous/guest mode in v1.

## 11. Out of Scope (v1)

- Multi-corpus support (podcasts beyond Lenny's).
- Real-time collaborative editing of sessions/artifacts.
- Native publishing integrations (LinkedIn/X APIs).
- Mobile-native apps (web-responsive only).

## 12. Open Questions

- What is the refresh cadence for ingesting new episodes into the corpus?
- Should research briefs support export formats beyond Markdown/HTML (e.g., PDF)?
- What is the retention policy for sessions and artifacts?
- Should manual skill override be sticky per-session or per-message?
