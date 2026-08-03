# Product Requirements Document

## Lenny Growth Assistant

| | |
|---|---|
| **Prepared for** | AIVAR Innovations — Product & Engineering Leadership |
| **Prepared by** | Product Management, in partnership with Staff Engineering |
| **Document Owner** | Product Management |
| **Status** | **Approved for Development** |
| **Version** | 1.0 |
| **Date** | 2026-08-01 |
| **Distribution** | Staff Engineers, Product Managers, Design, QA, Executive Sponsors |

> **Document purpose.** This PRD defines the requirements for **Lenny Growth Assistant** prior to the start of engineering work. It is the authoritative source of *what* is being built and *why*; the accompanying architecture, domain-model, and repository-structure documents (to be authored by Staff Engineering following sign-off of this PRD) define *how*. No implementation should begin against a requirement that is not traceable to a section of this document.

---

## Table of Contents

- [Executive Summary](#executive-summary)
- [Problem Statement](#problem-statement)
- [Background](#background)
- [Objectives](#objectives)
- [Success Criteria](#success-criteria)
- [User Personas](#user-personas)
- [User Stories](#user-stories)
- [Functional Requirements](#functional-requirements)
- [Non-Functional Requirements](#non-functional-requirements)
- [Technical Requirements](#technical-requirements)
- [System Constraints](#system-constraints)
- [Risks](#risks)
- [Assumptions](#assumptions)
- [Milestones](#milestones)
- [Acceptance Criteria](#acceptance-criteria)
- [Future Roadmap](#future-roadmap)

---

## Executive Summary

AIVAR Innovations will build **Lenny Growth Assistant**, an AI-powered knowledge workspace over the complete transcript archive of *Lenny's Podcast* — a corpus of long-form interviews with product, growth, and startup operators. The product gives a user three escalating capabilities inside one persistent, session-based workspace: **Ask** a direct question and receive a citation-backed answer grounded strictly in retrieved transcript excerpts; **Research** a broader topic and receive a structured, multi-episode synthesis brief; and **repurpose** either output into publish-ready content (a LinkedIn post, an X/Twitter thread, or a long-form article), respecting each platform's real constraints.

The product's core differentiator is **trust through traceability**: every substantive claim the system makes must be attributable to a specific episode, guest, and timestamp — the system is required to say "I don't have enough information" rather than answer confidently from ungrounded or general knowledge. Engineering will deliver this on a **local-first model stack** (a self-hosted embedding and generation model) with a **hosted secondary model provider** as an automatic, transparent fallback — balancing cost control and data locality against reliability.

This document defines the problem, the requirements, the phased delivery plan, and the acceptance bar for a Minimum Viable Product (MVP) that a Staff Engineering team can scope, estimate, and build against without further product discovery.

## Problem Statement

*Lenny's Podcast* has published hundreds of long-form episodes containing dense, tactical, operator-level advice on product management, growth, and startup building. Today, that knowledge is:

- **Hard to search.** It exists only as unstructured long-form audio/transcript. A user who wants to know "what do guests say about activation metrics" has no way to search across the corpus semantically — only full-text search (if even that) against individual episode pages, one at a time.
- **Hard to synthesize.** Any single topic worth researching — pricing strategy, onboarding, PLG motion design — is scattered across dozens of episodes, voiced by dozens of different guests, with no existing tool that compares, reconciles, or structures those perspectives into one coherent view.
- **Hard to reuse.** A practitioner who wants to turn a podcast insight into a LinkedIn post, a thread, or an internal brief must manually re-listen, extract the relevant portion, and rewrite it in the target format — a slow, repetitive, low-leverage task for content-producing professionals.

No existing tool lets a user ask a grounded question against this specific corpus, receive a cited answer they can verify, escalate that into a structured cross-episode research brief, and transform the result into ready-to-publish content — inside one continuous, persisted workflow. This is the gap Lenny Growth Assistant is chartered to close.

## Background

**Why this corpus, why now.** The podcast's transcript archive represents a large, high-quality, single-domain knowledge base — a favorable shape for retrieval-augmented generation (RAG): topically coherent, richly time-aligned, and produced by credible, named practitioners whose advice carries more weight *because* it's attributable. Recent maturity in open-weight embedding and generation models (servable locally at low marginal cost) makes it practical to build this without per-query API costs dominating the product's unit economics, while hosted frontier models remain available as a reliability backstop rather than the primary cost driver.

**Why a workspace, not a single Q&A box.** Discovery with target users (growth PMs, founders, content creators) surfaced a consistent pattern: a session rarely stays a single question. A user asks something narrow, likes the answer, and wants to go broader ("what do *other* guests say"), and then wants to *use* what they learned rather than just read it. A single-turn Q&A tool would force the user to lose all that context between steps; a persistent, session-based workspace does not.

**Why grounding is non-negotiable.** Target users are making real decisions (pricing, onboarding design, positioning) partly on the strength of this tool's output. An ungrounded or hallucinated answer that *looks* confident is worse than no answer, because it actively misleads a professional acting on it. Product requires that trust be verifiable, not merely claimed — hence the Source Inspection capability being a first-class requirement, not a "nice to have."

## Objectives

| # | Objective | Type |
|---|---|---|
| O1 | Enable grounded, cited question-answering over the full podcast transcript corpus, with zero tolerance for fabricated citations. | Product |
| O2 | Enable cross-episode research synthesis so a user can compare and reconcile multiple guests' perspectives on one topic in a single structured output. | Product |
| O3 | Enable direct transformation of QA/Research output into publish-ready content for at least three target formats (LinkedIn post, X/Twitter thread, long-form article). | Product |
| O4 | Persist all user work as durable, resumable sessions with full history and attached artifacts. | Product |
| O5 | Operate on a local-first model stack for cost control and data locality, with automatic graceful degradation to a hosted provider on failure. | Technical |
| O6 | Ship a working MVP across a bounded, three-phase delivery plan without requiring a full authentication system to unblock internal validation. | Delivery |
| O7 | Establish an information architecture and interaction model general enough that a future fourth or fifth capability can be added without restructuring the existing three. | Technical |

## Success Criteria

| Metric | Definition | Target (MVP) |
|---|---|---|
| **Citation coverage** | % of Ask/Research responses that include at least one valid inline citation when the answer draws on podcast content. | ≥ 95% |
| **Zero-fabrication rate** | % of responses where every citation resolves to a transcript excerpt that was actually retrieved for that request (never model-invented). | 100% (hard requirement, not a target range) |
| **Grounding honesty** | % of under-grounded queries (no sufficiently relevant retrieved content) that receive an explicit "insufficient information" response rather than a fabricated answer. | 100% |
| **Time-to-first-answer** | Wall-clock time from message submission to a rendered Ask response, under normal local-model load. | Perceived-responsive (visible progress feedback within \<1s of submission; full answer typically within single-digit seconds) |
| **Cross-episode coverage** | % of Research briefs on a topic with genuine multi-episode source coverage citing ≥ 2 distinct episodes, when multi-episode coverage exists in the corpus. | ≥ 80% |
| **Session resumption rate** | % of sessions with more than one message across more than one visit (proxy for the workspace's persistence value being used, not just single-shot queries). | Tracked from MVP launch; no fixed target pre-launch, reported at Phase 3 exit |
| **Graceful degradation** | % of local-model-outage windows where a user-facing request still completes successfully via the fallback provider. | 100% (any request that would have succeeded on the primary provider must succeed) |
| **Model output attribution** | % of Ship30-generated content explicitly derived from and traceable to prior session context, when such context exists. | 100% |

## User Personas

### Persona 1 — The Knowledge Worker
**Profile**: Product manager or growth operator with a specific, tactical question.
**Goals**: Get a trustworthy, fast answer without listening to hours of audio.
**Pain points today**: No semantic search over podcast content; manual transcript skimming is slow and unreliable.
**Primary capability**: Ask.
**Success looks like**: A short, cited answer within seconds, with the option to verify the underlying source if the claim matters.

### Persona 2 — The Creator
**Profile**: Content marketer or individual creator writing about product/growth topics for an audience.
**Goals**: Produce credible content backed by real, named-operator insight, in significantly less time than manual research + writing.
**Pain points today**: Sourcing credible quotes/insight is manual and slow; reformatting for each platform (LinkedIn vs. X vs. long-form) is repetitive.
**Primary capability**: Ask/Research → Artifact Generation.
**Success looks like**: A publish-ready draft, correctly formatted for the target platform, derived from real session context.

### Persona 3 — The Researcher
**Profile**: Founder, analyst, or operator compiling a structured view of a topic across many perspectives, not one fact.
**Goals**: Compare and reconcile how multiple guests think about a subject; produce a citable, structured writeup for internal or personal use.
**Pain points today**: No tool aggregates or synthesizes across episodes; manual cross-referencing does not scale past a handful of episodes.
**Primary capability**: Research.
**Success looks like**: A multi-section brief with genuine multi-episode sourcing, each claim traceable.

### Persona 4 — The Professional Learner
**Profile**: A repeat user building a personal, durable library of prior questions, briefs, and generated content over days or weeks.
**Goals**: Return to previous work without losing context; treat the workspace as a growing personal reference, not a one-shot tool.
**Pain points today**: No existing tool persists this kind of exploratory + generative session history in one place.
**Primary capability**: Session Management + Artifact Generation (retrieval of past output).
**Success looks like**: Reopening a session from days prior and finding the exact brief and derived content, still intact and downloadable.

## User Stories

Stories are grouped by capability. Each includes an acceptance note; full Given/When/Then acceptance criteria are consolidated in [Acceptance Criteria](#acceptance-criteria).

### Ask

1. *As a Knowledge Worker*, I want to ask a direct question about the podcast corpus, so that I get a fast, trustworthy answer without manual research.
   *Acceptance note: response must include inline citations whenever it draws on retrieved content.*
2. *As a Knowledge Worker*, I want the system to tell me plainly when it doesn't have enough information, so that I never mistake a guess for a grounded answer.
3. *As any user*, I want to see immediate visual feedback the moment I submit a question — including the very first message in a brand-new session — so that I know the system received my request and is working on it.
4. *As a Knowledge Worker*, I want to open the exact source excerpt behind any citation, so that I can independently verify a claim before acting on it.

### Research

5. *As a Researcher*, I want to switch into a distinct "Research" mode and ask a broader topic, so that I get a structured, multi-episode synthesis instead of a single short answer.
6. *As a Researcher*, I want a research brief to surface where guests agree or disagree, so that I can form my own judgment rather than get a flattened, single-viewpoint summary.
7. *As a Researcher*, I want my research briefs to persist as a distinct, revisitable output separate from the chat transcript, so that a long session doesn't bury a finished brief in scrollback.
8. *As a Researcher*, I want the system to tell me plainly if the corpus doesn't have sufficient multi-episode coverage for my topic, rather than force a brief out of thin or unrelated material.

### Artifact Generation (Ship30)

9. *As a Creator*, I want to transform an existing answer or research brief into a LinkedIn post, X thread, or article, so that I don't have to manually rewrite it for each platform.
10. *As a Creator*, I want each generated format to respect that platform's real constraints (length limits, thread segmentation), so that the output is actually usable without manual cleanup.
11. *As a Creator*, I want to optionally give a framing instruction (tone, angle, what to emphasize) before generating, so that the output matches my intent, not just the source material verbatim.
12. *As a Creator*, I want to download any generated artifact as a portable file, so that I can paste it into my own publishing tool without re-copying from the UI.
13. *As a Creator*, I want to see which specific piece of content is currently generating (not just a generic loading state), so that I can tell what's in progress if I've queued multiple actions mentally.

### Source Inspection

14. *As a Knowledge Worker*, I want every citation to show me the episode, an approximate timestamp, and the actual quoted excerpt, so that I can judge relevance and accuracy myself rather than trust a label alone.
15. *As any user*, I want a one-click path from any cited answer to its exact sources, so that verifying an answer never requires hunting through a separate part of the UI.

### Session Management

16. *As a Professional Learner*, I want every conversation to be saved as a resumable session, so that I can pick up exactly where I left off, potentially days later.
17. *As a Professional Learner*, I want my sessions listed by recency with an automatically generated title, so that I can find past work without having to name and organize it myself.
18. *As a Professional Learner*, I want artifacts I generate to remain attached to the session that produced them, so that I never lose the connection between a piece of content and the research that produced it.

### Landing Page

19. *As a first-time visitor*, I want to understand what the product does and who it's for before I'm dropped into an empty chat box, so that I know how to use it correctly.
20. *As any user*, I want one unambiguous action to enter the workspace from the landing experience, so that getting started never feels like a decision with unclear stakes.
21. *As any user*, I want to be able to return to the landing/introduction experience from inside the workspace, so that I'm never funneled one-way into the product with no way back to reorient.

## Functional Requirements

Requirements are numbered `FR-<area>.<n>` for traceability into engineering task breakdown and test plans. "Shall"/"must" denote mandatory MVP scope; "should" denotes a strong preference that may slip to a later phase without blocking sign-off.

### Ask Mode

| ID | Requirement |
|---|---|
| FR-ASK.1 | The system shall provide a default interaction mode ("Ask") for direct, single-question interactions against the podcast corpus. |
| FR-ASK.2 | For every Ask request, the system shall perform a semantic retrieval pass against the transcript corpus and use only the retrieved excerpts (never general/parametric knowledge) to ground factual claims about podcast content. |
| FR-ASK.3 | The system shall reject candidate source material that falls below a defined relevance threshold, rather than always returning a fixed number of results regardless of actual relevance. |
| FR-ASK.4 | If no retrieved content is sufficiently relevant to the question, the system shall respond with an explicit, plainly-worded statement that it lacks sufficient grounding, and shall not generate a speculative answer. |
| FR-ASK.5 | Even when retrieved content passes the relevance threshold, the system shall include a second, generation-time check for whether that content actually substantiates the specific question asked (as distinct from a merely adjacent topic), and shall decline to answer if it does not. |
| FR-ASK.6 | Every Ask response that draws on retrieved content shall include one or more inline citation markers, each resolvable to a specific source excerpt. |
| FR-ASK.7 | Citations shall be constructed exclusively from the metadata of content actually retrieved for that request — never inferred, paraphrased, or generated as free text by the model. |
| FR-ASK.8 | The system shall display a visible, immediate processing/"thinking" indicator upon message submission, with no exception for the first message of a new session. |
| FR-ASK.9 | The system should support follow-up questions within the same session with awareness of prior conversational turns. |

### Research Mode

| ID | Requirement |
|---|---|
| FR-RES.1 | The system shall provide a distinct, explicitly selectable "Research" mode, separate from Ask, for broader-topic, multi-episode synthesis requests. |
| FR-RES.2 | On a Research request, the system shall expand the user's topic into multiple retrieval queries covering different angles or sub-topics, to achieve broader source coverage than a single query would. |
| FR-RES.3 | The system shall retrieve and deduplicate results across all expanded queries before synthesis, so that near-duplicate results from similar queries do not crowd out genuine multi-episode coverage. |
| FR-RES.4 | The synthesized research brief shall be structured into distinct sections (at minimum: an executive summary, key insights, supporting evidence, and recommended actions), not a single undifferentiated block of text. |
| FR-RES.5 | Where multiple guests offer differing or conflicting perspectives on the topic, the brief shall surface that explicitly rather than flattening it into one voice. |
| FR-RES.6 | The same insufficient-grounding requirement defined for Ask (FR-ASK.4, FR-ASK.5) applies identically to Research: if the corpus does not substantively cover the requested topic, the system shall say so rather than produce a brief from unrelated or thin material. |
| FR-RES.7 | A completed research brief shall be persisted as a durable artifact, distinct and separately accessible from the live chat transcript. |
| FR-RES.8 | The chat transcript shall present only a short summary of a completed Research response (not the full brief), with a clear pointer to where the complete, structured brief can be found. |
| FR-RES.9 | The workspace shall automatically direct the user's attention to the location of a newly completed research brief once synthesis finishes. |

### Artifact Generation

| ID | Requirement |
|---|---|
| FR-ART.1 | The system shall support generating publish-ready content in at least three formats: a LinkedIn post, an X/Twitter thread, and a long-form article. |
| FR-ART.2 | Generation shall be initiated from an existing piece of prior session content (a QA answer or a research brief) — the system shall not offer a way to generate content with no underlying source material. |
| FR-ART.3 | The user shall be able to supply an optional framing instruction (tone, emphasis, angle) alongside the source material for a given generation request. |
| FR-ART.4 | Generated LinkedIn posts shall respect the platform's real maximum length; content exceeding it shall be truncated rather than rejected outright. |
| FR-ART.5 | Generated X/Twitter threads shall be segmented into individual, per-tweet units, each respecting the platform's real per-post character limit. |
| FR-ART.6 | Generated articles shall include a clear top-level title and be organized into distinct sections. |
| FR-ART.7 | Every generated piece of content shall be persisted as a durable, independently retrievable artifact attached to the session. |
| FR-ART.8 | The user shall be able to download any artifact as a portable file for use outside the product. |
| FR-ART.9 | The interface shall indicate, at the specific control the user activated, that a generation is in progress — not only via a generic, undifferentiated loading state. |
| FR-ART.10 | While a generation is in progress, the interface shall prevent the same user from triggering a conflicting, simultaneous generation request from the same control set. |

### Source Inspection

| ID | Requirement |
|---|---|
| FR-SRC.1 | Every citation shall be inspectable by the user, showing at minimum: the source episode's identifying title, an approximate timestamp or location within that episode, and the verbatim excerpt text that grounds the claim. |
| FR-SRC.2 | The user shall be able to reach a given response's sources in a single interaction from the response itself — source inspection shall not require separately searching or re-deriving which sources applied to which answer. |
| FR-SRC.3 | Quoted source excerpts shall be visually distinguishable from the surrounding interface and generated content, so a user can immediately tell "this text is a direct quote" from "this text is the system's own writing." |
| FR-SRC.4 | The system shall never present a citation for content that was not actually retrieved and shown to the model for that specific request. |

### Session Management

| ID | Requirement |
|---|---|
| FR-SESS.1 | The system shall allow a user to create a new session at any time. |
| FR-SESS.2 | The system shall persist full message history for every session, surviving across visits and restarts. |
| FR-SESS.3 | The system shall automatically derive a human-readable session title from the content of the first message, requiring no manual naming step from the user. |
| FR-SESS.4 | The system shall present the user's sessions in a list ordered by most-recent activity. |
| FR-SESS.5 | Reopening any past session shall fully restore its message history and any artifacts generated within it, in their original state. |
| FR-SESS.6 | Artifacts generated within a session shall remain associated with that session and shall not appear detached from the context that produced them. |

### Landing Page

| ID | Requirement |
|---|---|
| FR-LAND.1 | The system shall present a dedicated introductory landing experience as the default entry point, prior to any workspace/chat interface. |
| FR-LAND.2 | The landing experience shall clearly communicate the product's name, its core capabilities, and who it is for, without requiring the user to have already used the product. |
| FR-LAND.3 | The landing experience shall present exactly one primary, unambiguous call-to-action into the workspace. |
| FR-LAND.4 | The user shall be able to navigate from the workspace back to the landing experience at any time, without losing their current session's state. |
| FR-LAND.5 | The landing experience shall carry the product's visual brand identity (name and logo) consistently with how that identity appears inside the workspace. |

## Non-Functional Requirements

### Performance

- **NFR-PERF.1**: The system shall provide visible processing feedback to the user within 1 second of message submission, regardless of total response time.
- **NFR-PERF.2**: Retrieval latency shall scale sub-linearly with corpus growth through the use of an indexed vector-similarity search structure, not a linear scan.
- **NFR-PERF.3**: The model-serving layer shall be configured to avoid unnecessary resource contention between the embedding and generation workloads on constrained local hardware (e.g., a single consumer GPU), since a typical Ask/Research request requires both in sequence.
- **NFR-PERF.4**: Research and Artifact Generation requests, which require multiple model calls, may take materially longer than a single Ask request; this shall be communicated to the user via sustained processing feedback, not silence.

### Reliability

- **NFR-REL.1**: The system shall degrade gracefully to a secondary, hosted model provider if the primary local model provider is unavailable, times out, or fails health checks — without surfacing a hard failure to the user for a request that the secondary provider could serve.
- **NFR-REL.2**: Transient provider-level failures (e.g., timeouts, 5xx responses) shall be retried with bounded backoff before being treated as a provider outage.
- **NFR-REL.3**: Session and artifact data shall be durably persisted such that a service restart never loses committed user work.
- **NFR-REL.4**: A failure in one skill (Ask, Research, or Artifact Generation) shall not degrade or block the availability of the other two.

### Usability

- **NFR-USE.1**: The interface shall require no explanation of the system's internal architecture (retrieval, model routing, grounding checks) for correct use — the only decision exposed to the user shall be Ask vs. Research mode.
- **NFR-USE.2**: All interactive controls shall be operable via keyboard alone, with visible focus indication.
- **NFR-USE.3**: Loading/processing states shall always be attributable to the specific action that triggered them, not presented as an undifferentiated global state.
- **NFR-USE.4**: The product's navigation shall contain no dead ends — every screen the user can reach shall have a clear, discoverable path both deeper into the product and back toward the entry point.

### Maintainability

- **NFR-MAINT.1**: The system's capabilities (Ask, Research, Artifact Generation, and any future capability) shall be structured so that adding a new capability does not require modifying the internal logic of existing ones.
- **NFR-MAINT.2**: All environment-specific configuration (data store connection, model provider endpoints and credentials) shall be externalized from application code, with no secrets committed to source control.
- **NFR-MAINT.3**: Core request-handling logic (retrieval, grounding enforcement, generation dispatch) shall be covered by an automated test suite that does not require a live database or live model provider to execute, so tests remain fast and runnable in any environment.
- **NFR-MAINT.4**: The relevance threshold used to filter retrieved content, and any other empirically-tuned constants, shall be defined in one clearly identified, documented location — not duplicated across the codebase — so they can be revisited as the corpus grows without a multi-file change.

## Technical Requirements

| Area | Requirement |
|---|---|
| **Backend service** | A backend service exposing a typed, documented HTTP API for session, message, and artifact operations. |
| **Data store** | A relational database with native vector-similarity search support, so that transactional data (sessions, messages, artifacts) and retrieval data (embeddings) can be kept in one consistent store rather than two systems requiring separate synchronization. |
| **Frontend client** | A modern, component-based web frontend supporting server-rendered initial load and a responsive, componentized interactive workspace. |
| **Model serving — primary** | A locally-hostable model runtime capable of serving both a text-embedding model and a text-generation model, to keep steady-state inference cost and data locality under the product's control. |
| **Model serving — secondary** | A hosted, managed LLM API integrated as an automatic fallback for text generation only; no fallback path is required for embeddings in MVP scope. |
| **Ingestion pipeline** | An offline, batch-run pipeline capable of parsing time-aligned transcript sources, chunking them into retrievable units, generating embeddings, and loading them into the data store — run independently of the live request path. |
| **Authentication** | An identity/authentication mechanism sufficient to scope every session, message, and artifact to exactly one owning user; a lightweight development-mode bypass is acceptable for internal MVP validation but shall not be enabled in any environment reachable by external users. |
| **Testing** | Automated tests exercising the real API and orchestration logic with test doubles substituted only at the boundaries requiring live infrastructure (database, model providers). |
| **Deployment** | The MVP shall not require container orchestration infrastructure; a documented, reproducible local/manual setup is sufficient for this phase. |

## System Constraints

- **Single corpus, v1.** The system targets *Lenny's Podcast* exclusively; multi-corpus ingestion is explicitly out of scope for this PRD's phases.
- **Batch ingestion only.** Transcript ingestion is an offline, pre-processing step; real-time transcription of newly aired episodes is out of scope.
- **Single-owner sessions.** Sessions are not shared or collaboratively edited by multiple users in real time.
- **No direct publishing.** The system produces publish-ready content; it does not post to LinkedIn, X, or any other platform on the user's behalf. Publishing remains a manual, out-of-product step.
- **No model fine-tuning.** The product relies on prompting and retrieval, not custom model training, in this phase.
- **Consumer-grade local hardware assumption.** The local model-serving requirement (NFR-PERF.3) assumes commodity, not data-center-scale, hardware for the primary provider — informing model-size choices and placement/configuration decisions Staff Engineering will make during implementation.
- **Content licensing.** Transcript content belongs to the podcast and its guests; the product is scoped for internal/educational use of this material, not redistribution of the raw corpus.

## Risks

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Retrieval returns topically-adjacent but not actually relevant content, leading to confidently-worded but ungrounded answers. | Medium | High | A tunable relevance threshold (NFR-MAINT.4) plus a mandatory generation-time self-check (FR-ASK.5) as two independent gates, not one. |
| Local model provider is unreliable or resource-constrained on target hardware, degrading response quality or latency. | Medium | Medium | Mandatory graceful degradation to a hosted secondary provider (NFR-REL.1); explicit performance requirement to avoid resource contention (NFR-PERF.3). |
| Users lose trust after a single hallucinated or fabricated citation. | Low (if grounding requirements are met) | Very High | Zero-fabrication is a hard, non-negotiable success criterion (see Success Criteria), enforced structurally (FR-SRC.4), not left to model behavior alone. |
| Development-mode auth bypass is mistakenly left enabled in a reachable environment. | Low | High | Explicit constraint (Technical Requirements: Authentication) that the bypass must never be enabled outside internal development; must be a build/config-gated, not a runtime-toggle, decision before any external exposure. |
| Corpus coverage is uneven across topics, producing weak or empty Research briefs for under-covered subjects. | Medium | Medium | Explicit, honest insufficient-grounding response required (FR-RES.6) rather than forcing a brief from thin material; success criteria track cross-episode coverage as a monitored metric, not just present/absent. |
| Scope creep across four ambitious capabilities (Ask, Research, Artifact Generation, plus future work) delays MVP delivery. | Medium | Medium | Explicit three-phase milestone plan (see Milestones) sequencing capabilities by user value and technical dependency, with a phase-gated sign-off process. |
| Empirically-tuned parameters (relevance threshold, chunk size) are wrong at initial launch scale and need revision. | High | Low–Medium | Treated as an expected, budgeted post-launch tuning activity, not a launch blocker; single documented location for these constants (NFR-MAINT.4) keeps revision low-cost. |

## Assumptions

- The transcript corpus is available in a machine-readable form with time-aligned segments (or can be reasonably derived into one) prior to ingestion-pipeline development.
- MVP scope is single-tenant per user; no team, organization, or shared-workspace concept is required.
- Target deployment hardware for the primary model provider has sufficient resources to host at least one small embedding model and one mid-sized generation model, even if not simultaneously at full GPU residency for both.
- A hosted LLM API account/credential will be available and budgeted for the fallback path from day one of development, not added later.
- Users derive more trust from a verifiable, cited answer than from an unverifiable but more fluent one — this is treated as a core product bet, and success criteria are built to validate it (citation coverage, zero-fabrication rate) rather than assume it silently.
- Manual, out-of-product publishing (copy/paste or file download) is an acceptable and sufficient distribution mechanism for generated content at MVP scope; no direct platform-publishing integration is expected by target users at this stage.
- Internal stakeholders (Staff Engineering, Product Management, Design, QA) accept a development-mode authentication bypass as sufficient for Phase 1–2 internal validation, with real authentication scheduled explicitly before any external-facing release.

## Milestones

### Phase 1 — Foundation

**Goal**: Prove the core grounded-retrieval loop end-to-end, with a durable, resumable workspace.

**Entry criteria**: This PRD signed off; corpus available for ingestion; local and hosted model provider access confirmed.

**Deliverables**:
- Transcript ingestion pipeline (chunking, embedding, storage).
- Session Management (create, list, resume, persist history) — FR-SESS.1–FR-SESS.6.
- Ask Mode, fully grounded, with citations and insufficient-evidence handling — FR-ASK.1–FR-ASK.9.
- Source Inspection — FR-SRC.1–FR-SRC.4.
- Baseline workspace UI: session sidebar, chat column, sources panel.
- Development-mode authentication sufficient for internal use only.

**Exit criteria**: An internal user can create a session, ask a question, receive a grounded and cited answer (or an honest "insufficient information" response), inspect the underlying source excerpt, and resume that session later with full history intact.

### Phase 2 — Synthesis & Repurposing

**Goal**: Extend the workspace from single-answer QA into structured research and publish-ready content generation.

**Entry criteria**: Phase 1 exit criteria met and validated internally.

**Deliverables**:
- Research Mode: query expansion, multi-episode retrieval and deduplication, structured brief synthesis, chat-summary/full-brief separation — FR-RES.1–FR-RES.9.
- Artifact system: persistence, retrieval, download — FR-ART.7, FR-ART.8.
- Ship30 Artifact Generation: LinkedIn post, X/Twitter thread, and article generation from existing session content, with per-format constraints — FR-ART.1–FR-ART.6, FR-ART.9, FR-ART.10.
- Dedicated Research and Artifacts surfaces in the workspace UI, distinct from the chat transcript and from each other.

**Exit criteria**: An internal user can escalate an Ask answer or a fresh topic into a structured, multi-episode research brief; the brief persists as a distinct, revisitable artifact; and the user can repurpose it into all three supported content formats, each downloadable.

### Phase 3 — Experience & Trust Hardening

**Goal**: Polish the end-to-end experience for a first-time and returning user, and close the highest-priority gaps identified from Phase 1–2 internal validation.

**Entry criteria**: Phase 2 exit criteria met and validated internally.

**Deliverables**:
- Landing Page: introductory experience, branding, single primary CTA, bidirectional navigation with the workspace — FR-LAND.1–FR-LAND.5.
- Consistent, immediate processing feedback across every interaction, explicitly including the first message of a brand-new session (NFR-PERF.1, NFR-USE.3).
- Accessibility pass against NFR-USE.2 (keyboard operability, focus visibility) across all workspace surfaces.
- Performance tuning of the relevance threshold and model-provider placement/configuration based on real usage data gathered during Phase 1–2 internal validation (NFR-PERF.3, NFR-MAINT.4).
- A documented plan (not necessarily implementation) for real, external-facing authentication, gating any future release beyond internal use.

**Exit criteria**: A first-time visitor can understand the product, enter the workspace, and complete an Ask → Research → Artifact Generation flow without confusion or dead ends; every action provides immediate, action-specific feedback; the system is internally validated as ready for a broader, still-internal pilot audience.

## Acceptance Criteria

### Ask

- **Given** a user submits a question in Ask mode, **when** relevant transcript content exists and passes the relevance threshold, **then** the response includes an answer with at least one inline citation, and every citation resolves to content actually retrieved for that request.
- **Given** a user submits a question in Ask mode, **when** no retrieved content passes the relevance threshold, **then** the response is an explicit statement of insufficient information, with zero citations, and no speculative answer text.
- **Given** retrieved content passes the relevance threshold but does not substantively answer the specific question asked, **when** the model judges this at generation time, **then** the response is the same explicit insufficient-information statement, not a stretched or hedged answer.
- **Given** any Ask submission, including the first message of a brand-new session, **when** the request is sent, **then** a visible processing indicator appears within 1 second and remains visible until the response is rendered or an error is shown.

### Research

- **Given** a user submits a topic in Research mode, **when** the corpus has genuine multi-episode coverage of that topic, **then** the resulting brief cites at least two distinct episodes and is organized into the required structured sections.
- **Given** a completed research brief, **when** the user views the chat transcript, **then** only a short summary and a pointer to the full brief are shown there — the complete, structured brief is found in its dedicated location, not duplicated in the transcript.
- **Given** a completed research brief, **when** synthesis finishes, **then** the workspace automatically directs the user's attention to where the full brief can be read.
- **Given** a research topic with insufficient corpus coverage, **when** the system evaluates the retrieved content, **then** the response is an explicit statement that the corpus lacks sufficient information for that topic, not a thin or fabricated brief.

### Artifact (Ship30 Generation)

- **Given** an existing Ask answer or research brief, **when** the user requests LinkedIn post / X thread / article generation, **then** the resulting content is derived from that source material and respects the target format's real constraints (character limits, thread segmentation, title/section structure as applicable).
- **Given** a generation request is in progress, **when** the user views the triggering control, **then** that specific control indicates it is actively generating, and other generation controls in the same set are disabled until it completes.
- **Given** a completed generation, **when** the user views the result, **then** it is available both as a persisted, independently retrievable artifact and as a record in the session's chat history.
- **Given** any persisted artifact, **when** the user requests a download, **then** the exact content of the artifact is provided as a portable file, with no lossy transformation from what was generated.

### Sources

- **Given** a response includes one or more citations, **when** the user chooses to inspect them, **then** each citation displays the source episode's identifying title, an approximate timestamp, and the verbatim excerpt — reachable in a single interaction from the response itself.
- **Given** a quoted source excerpt is displayed, **when** the user views it alongside generated or interface text, **then** it is visually distinguishable as directly quoted material.
- **Given** any citation shown anywhere in the product, **when** it is traced back to its source, **then** it corresponds to content that was genuinely retrieved and shown to the model for that specific request — never a citation for content the model was not given.

### Sessions

- **Given** a user creates a new session, **when** they send their first message, **then** the session is automatically assigned a human-readable title derived from that message, with no manual naming step required.
- **Given** an existing session with prior message history and attached artifacts, **when** the user reopens it (including after a service restart), **then** the full message history and every attached artifact are restored exactly as they were.
- **Given** multiple sessions exist for a user, **when** the user views the session list, **then** it is ordered by most-recent activity, with the most recently active session first.
- **Given** an artifact generated within a specific session, **when** the user views that artifact, **then** its association with the originating session is preserved and discoverable — it is never presented as detached, ownerless content.

## Future Roadmap

Explicitly out of scope for the three phases defined in this PRD, but identified as likely follow-on investment once MVP is validated:

- **Full external-facing authentication** — real account registration, login, logout, and password-reset, replacing the internal development-mode bypass, as a prerequisite for any release beyond an internal pilot audience.
- **Streaming responses** — incremental, token-level rendering of Ask/Research/Artifact Generation output, to improve perceived responsiveness on the two longer-running workflows (Research, longer-form Artifact Generation).
- **Automated intent routing** — inferring which capability (Ask vs. Research, and potentially further capabilities) a message requires, reducing reliance on an explicit mode toggle, while preserving an always-available manual override.
- **Multi-corpus support** — extending ingestion and retrieval beyond a single podcast's transcript archive to additional knowledge sources, once the single-corpus product is validated.
- **Cross-session, persistent citation history** — a durable, browsable library of every citation a user has ever surfaced, independent of which message or session is currently open.
- **Routing-quality and provider-usage analytics** — structured tracking of which capability/provider served each request, to inform both product-quality evaluation and infrastructure cost decisions.
- **Direct publishing integrations** — optional, carefully-scoped direct-to-platform publishing (e.g., LinkedIn, X) as a convenience layer on top of the existing download/copy flow, only if validated user demand justifies the added complexity and platform-API maintenance burden.
- **Mobile and responsive workspace layout** — a deliberately redesigned, narrower-viewport experience for the three-pane workspace, distinct from simply shrinking the desktop layout.
- **Team/organization workspaces** — shared sessions, shared artifact libraries, and collaborative research, if multi-user demand is validated beyond the single-owner-session model assumed in this PRD.
