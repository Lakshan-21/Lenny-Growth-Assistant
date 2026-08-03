# Agent Development History

## Lenny Growth Assistant

> **A note on sourcing, before anything else.** This document was assembled by directly inspecting this repository — its code comments, its documentation trail, and its commit history — plus the first-hand record of the AI-assisted development sessions that produced it. It does **not** index a folder of raw, per-turn Claude/Codex/Cursor transcript files, because no such files are checked into this repository (see [Folder Structure Explanation](#folder-structure-explanation) for exactly what exists here and why). Every problem, investigation, and fix described below is traceable to a real artifact in the codebase — a comment, a constant, a docstring, a diff — cited by file where possible. Where a detail could not be independently verified against the code, it is not included.

---

## Table of Contents

- [Overview](#overview)
- [Why Agent Transcripts Are Included](#why-agent-transcripts-are-included)
- [Development Timeline](#development-timeline)
- [Major Decisions](#major-decisions)
- [Failed Attempts](#failed-attempts)
- [Performance Investigation](#performance-investigation)
- [UX Evolution](#ux-evolution)
- [Lessons Learned](#lessons-learned)
- [Folder Structure Explanation](#folder-structure-explanation)

---

## Overview

Lenny Growth Assistant was built through a series of AI-assisted (Claude Code) engineering sessions — architecture and planning documents drafted first, followed by backend and frontend implementation, followed by a sustained round of bug-hunting, performance tuning, and UX iteration once the MVP was runnable end-to-end against a real corpus and a real local model stack. This document is the project's own record of that process: not a marketing retrospective, but the same kind of engineering log a team would keep by hand if an AI pair-programmer hadn't already left the reasoning embedded directly in the code.

That embedding is real and worth naming explicitly: this codebase's comments are unusually dense with *why*, not just *what* — an empirically-derived similarity threshold with the actual sampled distances that produced it (`knowledge/repository.py`), a GPU-placement fix with the actual before/after latency numbers that justified it (`config/settings.py`, `providers/ollama/embeddings.py`), a rendering bug explained down to the specific CSS layout mechanism that caused it (`citation-card.tsx`). This document exists to pull that scattered, code-level history into one continuous narrative, so a new engineer (or a future agent session) doesn't have to reconstruct it by reading every file.

## Why Agent Transcripts Are Included

Three reasons, specific to how this project was actually built:

1. **The reasoning is as valuable as the code.** Several of this project's most important fixes — the retrieval distance threshold, the two-stage grounding enforcement, the Ollama GPU-placement change — are not obvious from reading the final code alone. The *investigation* that led to them (what was tried first, what evidence changed the diagnosis) is exactly the kind of institutional knowledge that normally lives only in a Slack thread or a departed engineer's memory. Here, it's durable and inspectable.
2. **AI-assisted development needs the same audit trail human development does.** A Staff Engineer reviewing this codebase should be able to answer "why is this threshold 0.48 and not something else" or "why does this one endpoint bypass the router class that looks like it should own routing" without guessing. Documenting the agent-driven decisions that produced these specifics is a transparency requirement, not an optional artifact.
3. **It prevents re-litigating settled decisions.** Several design choices in this codebase look, at first glance, like they could be simplified or "fixed" (the dead `SkillRouter` class; the `service_role`-only database connection; the CPU-forced embedding model). Each was a deliberate, reasoned tradeoff made after investigation, documented here so a future session doesn't spend time re-discovering — or worse, silently reversing — a decision that was already made for a documented reason.

## Development Timeline

Reconstructed from the documentation trail (`CONTEXT.md`, `docs/*.md`, this repository's commit history) and the AI-assisted implementation/hardening sessions that followed:

| Stage | What happened |
|---|---|
| **1. Architecture & planning** | Locked architecture decisions (`CONTEXT.md`), and initial PRD/architecture/domain-model/schema/repository-structure documents drafted *before* implementation began, establishing the vertical-slice backend, the four-skill model, and the local-first-with-fallback model strategy. Committed as the repository's initial commit. |
| **2. MVP implementation** | Backend (FastAPI, vertical-slice domains) and frontend (Next.js workspace) built out to the point of a working, end-to-end QA/Research/Ship30 flow against a real ingested transcript corpus and a real local Ollama instance. Committed as the project's MVP commits. |
| **3. Retrieval correctness investigation** | With the corpus actually ingested and real queries running, a specific failure mode surfaced: topically-adjacent-but-uncovered queries (e.g., asking about personal branding against a corpus with no personal-branding episodes) retrieved and confidently cited clearly irrelevant chunks. Diagnosed via temporary structured logging inserted directly into the retrieval path. See [Failed Attempts → Retrieval Issues](#retrieval-issues). |
| **4. Grounding-enforcement hardening** | The retrieval fix alone was not sufficient — a chunk could pass the new distance threshold and still not substantively answer the specific question asked. A second, generation-time enforcement layer was added to both QA and Research. See [Failed Attempts → Research Hallucination Issue](#research-hallucination-issue). |
| **5. Research UX redesign** | The Research skill's full multi-section brief was, at this point, rendered directly into the chat transcript — making the dedicated Research tab redundant. Redesigned so the chat shows only a summary and the tab holds the full brief. See [UX Evolution → Research Redesign](#research-redesign). |
| **6. Artifacts/Research tab separation** | Once Research had its own tab, the shared artifact list needed to stop mixing research briefs in with Ship30 outputs — split into two filtered, differently-rendered presentations of one underlying data source. |
| **7. Sources/Artifacts panel legibility fixes** | Citation excerpts and artifact preview rows were cramped and, in one specific case, visibly overflowing their container. Diagnosed down to a CSS layout interaction, fixed, and the panel widened. See [Failed Attempts → Source Panel Issues](#source-panel-issues). |
| **8. Ollama latency/performance investigation** | Real-world response latency on local hardware was measured and found to include a large, avoidable reload penalty on every single QA/Research request. Root-caused to GPU model-eviction thrashing between the embedding and generation models. See [Performance Investigation](#performance-investigation). |
| **9. First-message thinking-state fix** | A UX bug specific to a brand-new session's very first message — no loading feedback appeared for the entire request. Diagnosed to a conditional-rendering gap. See [Failed Attempts → Thinking State Issue](#thinking-state-issue). |
| **10. Landing page introduction** | The application's root route, which previously redirected straight into an empty workspace, was replaced with a dedicated Hero Landing Page. |
| **11. Branding & workspace navigation** | The workspace header's placeholder logo (a plain colored div) was replaced with the real brand asset, enlarged slightly, and made clickable — completing a symmetric navigation loop between the landing page and the workspace. |
| **12. Documentation hardening** | `README.md`, `design.md`, `docs/PRD.md`, and `docs/ARCHITECTURE.md` were authored (or, for the PRD/architecture docs, rewritten) by directly re-inspecting the actual running codebase rather than the original pre-development plans, so the documentation set reflects what was actually built — including honestly documenting where the running system diverges from the original plan (no streaming, no working auth, an unused routing-engine class). |

## Major Decisions

| Decision | Reasoning | Where it lives |
|---|---|---|
| **Vertical-slice backend, not layered MVC** | Each domain owns its full stack (router, service, repository, models). Adding a capability touches one folder, not five shared layers. | `backend/app/domains/*` |
| **A cosine-distance relevance threshold on every similarity search** | An unbounded `ORDER BY ... LIMIT k` always returns exactly `k` rows regardless of actual relevance — the root cause of the retrieval issue below. | `knowledge/repository.py::_MAX_COSINE_DISTANCE` |
| **Two independent grounding gates (retrieval threshold + generation-time self-check)** | Neither alone is sufficient — see [Research Hallucination Issue](#research-hallucination-issue). | `skills/schemas.py::INSUFFICIENT_EVIDENCE_MARKER`, used identically in `qa/service.py` and `research/service.py` |
| **Citations built only from retrieval metadata, never model text** | Removes an entire class of hallucinated-citation risk by construction, not by validation. | `skills/qa/citation_builder.py` |
| **`OLLAMA_EMBEDDING_FORCE_CPU=true` by default** | Eliminates measured GPU model-eviction thrashing between the embedding and generation models on constrained hardware. | `config/settings.py`, `providers/ollama/embeddings.py` |
| **Research's chat message and its artifact carry different content** | Prevents the same full brief from being duplicated in both the chat transcript and the Research tab. | `skills/research/service.py::_render_chat_summary_markdown` / `_render_brief_markdown` |
| **`DEV_AUTH_BYPASS` instead of building full auth before other capabilities** | Let sessions, retrieval, skills, and artifacts be built and validated against a real, ownership-scoped identity without a full Supabase Auth integration first — an explicit, scoped, and documented shortcut, not an oversight. | `auth/dependencies.py` |
| **`skill_router.py`'s classification engine was designed but never wired in** | The simpler, fully explicit `mode`/`skill` conditional in `skills/router.py` was judged sufficient for the actual scope shipped; the more ambitious auto-classifying router was left as a documented, unused alternative rather than deleted or silently abandoned. | `skills/skill_router.py` vs. `skills/router.py` |
| **Markdown as the only canonical artifact representation** | Guarantees Copy/Download always match what's rendered; HTML is always a derived, sanitized view, never a second independently-stored copy. | `artifacts/renderers/html_renderer.py` |

## Failed Attempts

Each of the following documents a real problem encountered during development, using the same problem/investigation/fix structure a hand-kept engineering log would use — reconstructed from the specific evidence (constants, comments, code structure) each fix left behind in the codebase.

### Retrieval Issues

#### Problem
A query on a topic the corpus did not actually cover (the reconstructed example: "personal branding strategies," against a corpus with no personal-branding episodes ingested at the time) did not produce an honest "I don't know" — it retrieved and confidently answered from chunks about an adjacent but different topic (coaching, career growth, values).

#### Investigation
Temporary, explicit diagnostic logging was added directly into the retrieval path — both at the query level (`RetrievalService.search`, logging the query text and requested `top_k`) and at the per-result level (`KnowledgeRepository.similarity_search`, logging each candidate chunk's id, cosine distance, episode, timestamps, and a content preview). This made it possible to see, for a real failing query, exactly which chunks were being returned and how far away they actually were in embedding space — rather than reasoning abstractly about the retrieval algorithm.

#### Failed Approaches
The retrieval query, as originally implemented, was a plain `ORDER BY embedding <=> :query_embedding LIMIT :top_k` with no distance filter. This is a reasonable-looking, standard top-k vector search — and it is precisely the design that caused the bug: an unbounded `ORDER BY ... LIMIT` **always** returns exactly `top_k` rows, no matter how distant the closest available candidates actually are. For an off-topic query against an under-covered corpus, the "top 6 nearest chunks" were still confidently returned and handed to the model as if they were relevant, because nothing in the query said otherwise.

#### Root Cause
The retrieval layer had no concept of "not relevant enough" — only "nearest available." Distance alone was never checked against any cutoff; a chunk at cosine distance 0.65 was returned with exactly the same unconditional confidence as a chunk at 0.35.

#### Final Fix
Sampling real queries against the corpus via the diagnostic logging above revealed a genuine, empirical separation: on-topic chunks landed at cosine distance roughly 0.34–0.48; a topically-adjacent-but-uncovered query landed at roughly 0.49–0.54; a fully unrelated query landed at roughly 0.62–0.68. A hard cutoff, `_MAX_COSINE_DISTANCE = 0.48`, was added to the similarity-search query itself (`WHERE distance <= 0.48`), sitting in the empirical gap between the first two clusters. This is documented in the code as a first cut derived from a single-episode sample, explicitly flagged for revisiting as ingestion coverage grows — a real, working fix, not a permanently-correct constant.

### Research Hallucination Issue

#### Problem
Even after the retrieval distance threshold above, a research brief (and, identically, a QA answer) could still be generated confidently from source material that didn't actually substantiate the specific topic asked — because the threshold can only measure "is this nearby in embedding space," not "does this specifically answer what was asked." A broad, adjacent theme (e.g., coaching generally) can sit close enough in embedding space to a narrower, different question (e.g., personal branding specifically) to pass a similarity cutoff while still not actually covering it.

#### Investigation
Once the retrieval-layer fix above was in place, the same class of failure was found to still be reproducible — a query that passed the new distance threshold could still produce a fluent but ungrounded answer, because the model was never explicitly told to judge relevance for itself; it was only ever asked to answer from whatever excerpts it was handed.

#### Failed Approaches
The retrieval distance threshold alone was the first and, initially, presumed-sufficient fix. It closed the "clearly irrelevant" failure mode but not the "plausible enough to pass a similarity cutoff, still doesn't actually answer this" one — a strictly harder problem, because it requires judging topical fit against the *specific* question asked, not just embedding-space proximity, and no distance-based filter can make that distinction.

#### Root Cause
Similarity search can only ever answer "is this text near that text in vector space." It has no way to know whether "near" is actually "on-topic for this exact question" — that judgment requires reading and reasoning about the specific question versus the specific excerpts, which only the generation model itself can do.

#### Final Fix
A second, independent enforcement gate was added at generation time, identically in both the QA and Research prompts: the model is explicitly instructed to first judge whether the retrieved excerpts substantively address the exact question or topic asked (not merely a related or broader theme), and — if they don't — to respond with a single, exact, unnatural sentinel string (`INSUFFICIENT_EVIDENCE_MARKER`) and nothing else. Both `qa/service.py` and `research/service.py` check for this literal string in the completion, before any citations are built, and substitute the same honest "insufficient information" response used for the empty-retrieval case. The sentinel is deliberately not a natural-language phrase specifically so a substring check against it can never false-positive against a genuine answer.

### UX Issues

*(Covering the Research-duplication and Artifacts/Research-separation issues; the Sources-panel and Thinking-state issues are detailed in their own subsections below given their distinct technical root causes.)*

#### Problem
A completed Research response rendered its entire structured, multi-section brief directly into the chat transcript — the same content a user had just read in full was also sitting, unchanged, in the dedicated Research tab.

#### Investigation
The issue surfaced from actually using the Research tab as a feature: it never told a user anything they hadn't already seen, because the chat transcript already contained the complete brief. A tab that never reveals new information fails at its one job.

#### Failed Approaches
The original design used one shared Markdown string for both the chat-facing message and the persisted artifact — a natural first implementation, since the two really are "the same output" conceptually, and reusing one string avoided (what looked like) needless duplication of the synthesis logic.

#### Root Cause
"The same output" was the wrong mental model. The chat transcript and the Research tab serve two different jobs — a running conversational log versus a durable, structured reference — and a single shared body of content cannot serve both without one of the two becoming redundant.

#### Final Fix
The Research skill's synthesis step now produces two distinct Markdown bodies from one generation pass: a short chat-facing summary (title, executive summary, and an explicit pointer to the Research tab) and a complete, separate artifact body (all four structured sections plus a citations appendix). The same underlying tension, once recognized, was applied to the Artifacts/Research tab split as well — one shared list-fetching mechanism, rendering two purpose-built, mutually-exclusive views (a generic file-preview row for Ship30 output, a title/summary/source-count row for research briefs) rather than one undifferentiated list mixing both content types.

### Source Panel Issues

#### Problem
Citation excerpts and artifact preview rows felt cramped in the right panel, and — more specifically — an excerpt's containing card was observed visibly overflowing past the right edge of its panel, rather than wrapping.

#### Investigation
The overflow was traced to a specific label inside a citation card, styled with a standard text-truncation utility, sitting inside a shared scrollable list component.

#### Failed Approaches
The initial implementation used a conventional single-line truncation utility (`white-space: nowrap` plus an ellipsis) on the citation label — a completely standard, normally-correct way to clip a long line of text to one line.

#### Root Cause
The scrollable list component's internal viewport renders as `display: table`, whose width is computed from its content's *unwrapped, natural* width. A `nowrap` descendant fed its full, un-wrapped width back into that table-layout width calculation — inflating the width of the *entire card*, not just the label, and forcing it past the edge of a fixed-width panel. A `min-width: 0` on ancestor elements, the usual fix for flex-based overflow, does not help here, because table-layout auto-sizing isn't governed by flex-shrink rules at all.

#### Final Fix
Two changes, applied together: the truncation technique was switched from `white-space: nowrap`-based truncation to CSS line-clamping (which clips visually without ever reporting an unwrapped natural width) everywhere the same scrollable-list-plus-fixed-width-panel pattern recurred — citation cards, generic artifact rows, and research-brief rows alike, not just the one component where the bug was first noticed. Separately, and for legibility rather than correctness, the right panel's fixed width was increased so that quoted source excerpts — this app's most content-dense, read-focused material — had genuine room to breathe.

### Thinking State Issue

#### Problem
Sending the very first message in a brand-new session showed no loading/processing feedback for the entire duration of the request — the UI appeared to do nothing until the answer simply appeared. Every message after the first, in the same session, worked correctly.

#### Investigation
The chat page's content area was governed by a single ternary: render an empty-state placeholder if the session had zero messages, otherwise render the message list. The message list was the only component in the tree that ever rendered a loading indicator.

#### Failed Approaches
The ternary — `session.messages.length === 0 ? <EmptyState /> : <MessageList />` — was a reasonable, minimal way to express "show a helpful placeholder before any conversation exists." It simply never accounted for the specific in-between state of "a message has been sent, but the server hasn't yet responded (and the session's cached message list hasn't yet been refetched to reflect it)."

#### Root Cause
For a brand-new session's first message, `session.messages` is genuinely still empty for the entire duration of the request — the local list of messages only gets refreshed after the response comes back. The ternary therefore kept the empty-state placeholder mounted for the whole request, and the only component capable of showing a loading indicator never got a chance to mount. From the second message onward, the session's message list was already non-empty, so the same gap simply never appeared.

#### Final Fix
A single added clause to the same condition — the message list now renders whenever the session already has messages, **or** a send is currently in flight — so a pending request always has somewhere to show its loading state, regardless of whether the session was empty at the moment the request began.

## Performance Investigation

### Latency benchmark

Real, measured latency numbers (not estimates) for loading each model on the local Ollama instance used during development, under warm-vs-reload conditions:

| Model | Warm (already resident) | Reload (evicted, then re-requested) |
|---|---|---|
| `bge-m3` (embedding, 566M parameters) | ~2.5s | ~14s |
| `llama3.1` (generation) | ~3.3s | ~22s |

### Ollama analysis

On a GPU too small to hold both the embedding and generation models resident in VRAM simultaneously, every switch between them evicted whichever model wasn't currently in use — and QA/Research requests always call embed-then-generate in immediate sequence within the same request, meaning this eviction-and-reload cycle was paid on essentially **every single request**, not just occasionally.

### Embedding placement optimization

The fix does not try to make both models fit — it changes *where* the smaller model runs. `bge-m3` is small enough (566M parameters) to run acceptably on CPU, while `llama3.1` genuinely benefits from the GPU. Setting Ollama's per-request `options.num_gpu = 0` specifically for embedding calls forces `bge-m3` onto CPU, leaving the GPU exclusively resident to the generation model — eliminating the eviction cycle entirely rather than merely shortening it. This is implemented as a configuration toggle (`OLLAMA_EMBEDDING_FORCE_CPU`, defaulting to `true`) rather than a hardcoded behavior, specifically because it is a genuine tradeoff: on hardware with enough VRAM for both models simultaneously, forcing embeddings onto CPU would very plausibly be *slower*, not faster — the fix is correct for the constrained hardware it was diagnosed against, not universally correct for every deployment target.

## UX Evolution

### Research Redesign
See [UX Issues → Problem/Root Cause/Final Fix](#ux-issues) above for the full technical account. In UX terms, this was the project's clearest instance of recognizing that "where something is shown" is a real design decision, not an afterthought — a summary belongs where the conversation is happening; the full structured output belongs in a dedicated home built to hold it.

### Landing Page
The application's root route originally redirected straight into the workspace, dropping a first-time visitor directly into an empty chat composer with no framing of what the product was or who it was for. This was replaced with a dedicated Hero Landing Page — logo, product name, a headline, a description naming the product's core capabilities, and a single, unambiguous "Go To Chat" call to action — separating *orientation* from *usage* without adding friction to reach the workspace (still one click, same as the redirect it replaced). The workspace's own header logo was, in the same body of work, made clickable and enlarged, so navigation between the two became a closed loop rather than a one-way funnel.

### Sources Panel
Covered in full under [Source Panel Issues](#source-panel-issues) above. The evolution here is really two separate improvements bundled together: a structural CSS bug fix (the `truncate`-inside-a-table-layout overflow) and an independent, judgment-based sizing decision (widening the panel because its content — quoted source material — deserved more room to be read comfortably). Treating these as two distinct issues, rather than one "fix the panel" task, is what made the fix apply correctly everywhere the same underlying layout pattern recurred, not just in the one spot it was first noticed.

## Lessons Learned

1. **Temporary, targeted diagnostic logging inserted directly into the suspect code path was faster and more conclusive than reasoning about the retrieval algorithm abstractly.** Seeing the actual cosine distances of actual failing queries is what produced the specific, defensible `0.48` threshold — a number that could not have been guessed correctly from first principles alone.
2. **A similarity threshold and a model self-check solve genuinely different problems, and neither substitutes for the other.** The retrieval-issue fix and the hallucination-issue fix look superficially similar (both are "grounding enforcement") but they catch different failure classes — one measures embedding-space proximity, the other measures whether a specific question is actually answered. Both were necessary; the second was only discovered *because* the first, alone, still let some ungrounded answers through.
3. **A CSS bug in one component is often a structural bug waiting to recur wherever the same layout pattern is reused.** The truncation/overflow fix had to be applied to every component sharing the same fixed-width-panel-plus-scrollable-list pattern, not just the one where it was first noticed, or it would have resurfaced with the next component built the same way.
4. **The first user interaction deserves first-interaction-level fix priority, not "it's an edge case" triage.** A loading-state bug that only ever affects a brand-new session's very first message is, in effect, a first-impressions bug — it was fixed with a one-line, minimal change rather than deferred.
5. **An empirically-tuned constant should be committed to the codebase together with the evidence that produced it, not just the final number.** The `0.48` threshold and the CPU-forcing default are both far more useful to a future engineer with their supporting numbers/observations attached in-place than as bare, unexplained values.
6. **A decision that looks incomplete or inconsistent from the outside (a routing-engine class that's never called; an artifact skill that always raises `NotImplementedError`) is only a real problem if it's undocumented.** Once the reasoning and status are recorded, these become legitimate, inspectable scope boundaries rather than latent bugs waiting to confuse the next reader.
7. **Local-first performance tuning is hardware-relative, not universal.** The GPU-placement fix is correct for the specific constrained hardware it was diagnosed against, and is deliberately exposed as a toggle rather than baked in as an assumption — a fix earned through investigation should be applied as a resolvable configuration, not a silent, unquestionable default.

## Folder Structure Explanation

```
agent-transcripts/
└── README.md    # This file — the curated development history.
```

**What is here**: one file, this one — a narrative reconstruction of the project's real development history, sourced from the codebase's own comments, its documentation trail, and its commit history, cross-checked for accuracy against the actual, current source rather than any prior plan or draft.

**What is deliberately not here, and why**: raw, per-turn Claude/Codex/Cursor session transcripts (the literal request/response/tool-call logs an agent session produces) are not checked into this repository. Three reasons:

1. **Signal-to-noise.** A raw agent transcript includes every tool call, every intermediate file read, every dead end explored and abandoned mid-session — almost all of which is working noise, not decision history. The curated narrative above extracts the parts worth keeping (the problem, the investigation, the fix, the reasoning) without the surrounding volume.
2. **Local-environment specificity.** Raw transcripts reference local file paths, tool names, and session-specific IDs tied to the machine and harness they were produced on — details that are not meaningful or portable to a reader of this repository.
3. **The reasoning was already durably captured at the source.** Because this project's code comments document *why* as thoroughly as they do, the highest-value content of any given session's transcript is already preserved in the file it produced — this README exists to connect those scattered, code-level explanations into one continuous story, which is more useful to a future reader than the raw conversation that produced each individual piece of it.

If raw transcripts are added to this repository in the future, the intended convention is one file per development session, named by date and topic (e.g. `2026-08-02-retrieval-threshold-investigation.md`), with this README updated to index them rather than restate their contents — this file should remain the readable entry point, not a duplicate of whatever raw logs eventually sit alongside it.
