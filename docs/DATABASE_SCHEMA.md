# Database Schema: Lenny Growth Workspace

| | |
|---|---|
| **Status** | Draft |
| **Version** | 0.2.0 |
| **Owner** | Engineering |
| **Last Updated** | 2026-08-02 |

Related: [CONTEXT.md](../CONTEXT.md) · [PRD.md](./PRD.md) · [ARCHITECTURE.md](./ARCHITECTURE.md) · [DOMAIN_MODEL.md](./DOMAIN_MODEL.md) · [REPOSITORY_STRUCTURE.md](./REPOSITORY_STRUCTURE.md)

This document is the PostgreSQL/Supabase schema for the entities already locked in `DOMAIN_MODEL.md`. It introduces no new entities, no new infrastructure, and no architecture changes. `RoutingDecision` and `ModelInvocation` are intentionally absent — both remain log-only per the prior MVP-simplification decision recorded in `REPOSITORY_STRUCTURE.md`. Auth uses Supabase's built-in `auth.users` as the source of truth; no custom `users` table is created.

---

## 1. Entity Relationship Diagram (text form)

```
auth.users (Supabase-managed — not created by this schema)
    │ 1:1
    ▼
profiles (id = auth.users.id)

profiles (implicit via auth.users.id)
    │ 1:N  (user_id)
    ▼
sessions
    │ 1:N  (session_id)
    ├──────────────────────────────┐
    ▼                              ▼
messages                       artifacts ◄── message_id (producing message)
    │ 1:N  (message_id)             │ 1:1  (artifact_id)
    ▼                              ▼
citations                    research_briefs
    │ N:1  (transcript_chunk_id)
    ▼
transcript_chunks
    │ N:1  (episode_id)
    ▼
episodes

Relationship summary:
  auth.users        1 ──── 1  profiles              (profiles.id → auth.users.id)
  auth.users        1 ──── N  sessions               (sessions.user_id → auth.users.id)
  sessions          1 ──── N  messages                (messages.session_id → sessions.id)
  sessions          1 ──── N  artifacts               (artifacts.session_id → sessions.id)
  messages          1 ──── N  artifacts               (artifacts.message_id → messages.id, producing message)
  messages          1 ──── N  citations                (citations.message_id → messages.id)
  transcript_chunks 1 ──── N  citations                (citations.transcript_chunk_id → transcript_chunks.id)
  episodes          1 ──── N  transcript_chunks        (transcript_chunks.episode_id → episodes.id)
  artifacts          1 ──── 1  research_briefs (opt)   (research_briefs.artifact_id → artifacts.id, specialization)
```

Notes:
- `profiles` has no independent identity — its primary key *is* the Supabase `auth.users.id` (shared-PK 1:1 pattern), not a separate generated UUID.
- `research_briefs` is a specialization row, not a subtype table hierarchy — it extends a specific `artifacts` row (`artifact_type = 'research_brief'`) with brief-specific fields, matching `DOMAIN_MODEL.md` §4.9.
- `episodes` / `transcript_chunks` have no owning user — they are the shared, read-only knowledge corpus populated by offline ingestion (per `DOMAIN_MODEL.md` §6, "Episode Aggregate").
- `messages.role` now supports `user`, `assistant`, **and `system`** (§2 CHANGE 1) — an attribute-level change only; it does not alter the `sessions → messages` relationship shown above.
- `transcript_chunks` now additionally carries `start_timestamp_seconds` / `end_timestamp_seconds` alongside the existing character offsets (§2 CHANGE 2) — also attribute-level only; the `episodes → transcript_chunks → citations` relationship chain is unchanged.

---

## 2. PostgreSQL DDL

```sql
-- =========================================================
-- 0. Extensions
-- =========================================================
create extension if not exists pgcrypto;   -- gen_random_uuid()
create extension if not exists vector;     -- pgvector

-- =========================================================
-- 1. profiles  (extends auth.users — Supabase Auth is source of truth)
-- =========================================================
create table public.profiles (
    id           uuid primary key references auth.users (id) on delete cascade,
    display_name text,
    created_at   timestamptz not null default now(),
    updated_at   timestamptz not null default now()
);

comment on table public.profiles is
    'Optional profile data extending auth.users. auth.users remains the source of truth for identity/credentials.';

-- Auto-provision a profile row whenever a new Supabase Auth user is created.
create function public.handle_new_user()
returns trigger
language plpgsql
security definer
set search_path = public
as $$
begin
    insert into public.profiles (id) values (new.id);
    return new;
end;
$$;

create trigger on_auth_user_created
after insert on auth.users
for each row execute function public.handle_new_user();

-- =========================================================
-- 2. sessions
-- =========================================================
create table public.sessions (
    id         uuid primary key default gen_random_uuid(),
    user_id    uuid not null references auth.users (id) on delete cascade,
    title      text not null default 'New session',
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

comment on column public.sessions.updated_at is
    'Bumped by the messages_touch_session trigger on every new message; drives session-sidebar recency ordering.';

-- =========================================================
-- 3. messages
-- =========================================================
create table public.messages (
    id         uuid primary key default gen_random_uuid(),
    session_id uuid not null references public.sessions (id) on delete cascade,
    role       text not null check (role in ('user', 'assistant', 'system')),
    content    text not null,
    skill_used text check (skill_used in ('qa', 'research', 'ship30', 'artifact')),
    created_at timestamptz not null default now(),

    -- Unchanged logically by the addition of 'system': skill_used is still
    -- only ever populated for role='assistant'; both 'user' and 'system'
    -- rows must have it null.
    constraint messages_skill_used_only_for_assistant
        check (role = 'assistant' or skill_used is null)
);

comment on column public.messages.role is
    'user | assistant | system. System messages carry router/skill-injected context (prompt-construction notes, routing/hand-off markers, operational breadcrumbs) as first-class, session-scoped conversation turns. See DATABASE_SCHEMA.md CHANGE 1 for rationale.';

comment on column public.messages.skill_used is
    'Which skill produced this message. Always null for role=''user'' or role=''system''. Nullable for role=''assistant'' to allow ungrounded/error responses.';

-- Keep sessions.updated_at accurate for sidebar recency ordering (PRD §6.2).
create function public.touch_session_updated_at()
returns trigger
language plpgsql
as $$
begin
    update public.sessions set updated_at = now() where id = new.session_id;
    return new;
end;
$$;

create trigger messages_touch_session
after insert on public.messages
for each row execute function public.touch_session_updated_at();

-- =========================================================
-- 4. episodes  (offline ingestion pipeline is the only writer)
-- =========================================================
create table public.episodes (
    id           uuid primary key default gen_random_uuid(),
    title        text not null,
    guest_name   text,
    published_at date,
    source_url   text,
    created_at   timestamptz not null default now()
);

-- =========================================================
-- 5. transcript_chunks  (offline ingestion pipeline is the only writer)
-- =========================================================
create table public.transcript_chunks (
    id                       uuid primary key default gen_random_uuid(),
    episode_id               uuid not null references public.episodes (id) on delete cascade,
    content                  text not null,
    embedding                vector(1024) not null,   -- bge-m3 dense embedding dimension — confirm against the deployed Ollama model before first ingestion
    start_offset             integer not null,
    end_offset               integer not null,
    start_timestamp_seconds  integer not null,
    end_timestamp_seconds    integer not null,
    created_at               timestamptz not null default now(),

    constraint transcript_chunks_offsets_valid check (end_offset > start_offset),
    constraint transcript_chunks_timestamps_valid check (
        end_timestamp_seconds > start_timestamp_seconds
        and start_timestamp_seconds >= 0
    )
);

comment on column public.transcript_chunks.start_offset is
    'Character/token offset within the episode transcript text — used for text-level chunk boundaries, not display.';

comment on column public.transcript_chunks.start_timestamp_seconds is
    'Audio-time offset (whole seconds) into the episode. Used to render citation timestamps (e.g., "12:34–13:02"), independent of the text-level start_offset/end_offset pair.';

-- =========================================================
-- 6. citations
-- =========================================================
create table public.citations (
    id                  uuid primary key default gen_random_uuid(),
    message_id          uuid not null references public.messages (id) on delete cascade,
    transcript_chunk_id uuid not null references public.transcript_chunks (id) on delete restrict,
    display_label       text not null,
    created_at          timestamptz not null default now(),

    constraint citations_unique_chunk_per_message unique (message_id, transcript_chunk_id)
);

comment on constraint citations_transcript_chunk_id_fkey on public.citations is
    'ON DELETE RESTRICT deliberately: prevents ingestion re-runs from silently orphaning grounding data behind already-generated answers. See DATABASE_SCHEMA.md §8.';

comment on column public.citations.display_label is
    'Denormalized, human-readable citation text, e.g. "Episode 142 — 12:34–13:02". Composed from episodes.title/guest_name and transcript_chunks.start_timestamp_seconds/end_timestamp_seconds at generation time; stored as a snapshot so display is stable even if the source chunk is later re-ingested.';

-- =========================================================
-- 7. artifacts
-- =========================================================
create table public.artifacts (
    id               uuid primary key default gen_random_uuid(),
    session_id       uuid not null references public.sessions (id) on delete cascade,
    message_id       uuid not null references public.messages (id) on delete cascade,
    artifact_type    text not null check (
        artifact_type in ('qa_answer', 'research_brief', 'linkedin_post', 'x_thread', 'article')
    ),
    content_markdown text not null,
    created_at       timestamptz not null default now()
);

comment on column public.artifacts.content_markdown is
    'Canonical source of truth (ADR-4, ARCHITECTURE.md). HTML rendering is derived at read time — no content_html column.';

-- =========================================================
-- 8. research_briefs  (specializes artifacts where artifact_type = 'research_brief')
-- =========================================================
create table public.research_briefs (
    id          uuid primary key default gen_random_uuid(),
    artifact_id uuid not null unique references public.artifacts (id) on delete cascade,
    topic       text not null,
    summary     text not null,
    created_at  timestamptz not null default now()
);

-- Optional integrity guard: a research_briefs row must point at an artifact
-- whose artifact_type is actually 'research_brief'. Cross-table constraints
-- aren't expressible as a plain CHECK, so this is enforced via trigger.
create function public.enforce_research_brief_artifact_type()
returns trigger
language plpgsql
as $$
declare
    v_type text;
begin
    select artifact_type into v_type from public.artifacts where id = new.artifact_id;
    if v_type is distinct from 'research_brief' then
        raise exception 'research_briefs.artifact_id must reference an artifact with artifact_type = ''research_brief'' (got %)', v_type;
    end if;
    return new;
end;
$$;

create trigger research_briefs_check_artifact_type
before insert or update on public.research_briefs
for each row execute function public.enforce_research_brief_artifact_type();
```

---

## 3. Foreign Keys

| Table | Column | References | On Delete | Rationale |
|---|---|---|---|---|
| `profiles` | `id` | `auth.users(id)` | `CASCADE` | Profile has no meaning without the auth identity; Supabase deleting a user should remove the profile row. |
| `sessions` | `user_id` | `auth.users(id)` | `CASCADE` | A user's sessions are owned data; deleting the account removes them (aligns with "no orphaned data" and simplifies GDPR-style deletion). |
| `messages` | `session_id` | `sessions(id)` | `CASCADE` | Messages have no meaning outside their session. |
| `artifacts` | `session_id` | `sessions(id)` | `CASCADE` | Artifacts are session-scoped (PRD §6.6, "attached to sessions"). |
| `artifacts` | `message_id` | `messages(id)` | `CASCADE` | An artifact has no meaning without its producing message. |
| `research_briefs` | `artifact_id` | `artifacts(id)` | `CASCADE` | 1:1 specialization — the brief cannot outlive its artifact. `UNIQUE` enforces the 1:1 cardinality. |
| `transcript_chunks` | `episode_id` | `episodes(id)` | `CASCADE` | A chunk has no meaning without its episode. |
| `citations` | `message_id` | `messages(id)` | `CASCADE` | A citation has no meaning without the message that made the claim. |
| `citations` | `transcript_chunk_id` | `transcript_chunks(id)` | `RESTRICT` | Deliberately *not* cascading — see §8 risk #3. Forces the ingestion pipeline to handle chunk replacement explicitly instead of silently orphaning historical grounding data. |

---

## 4. Indexes

| Table | Index | Type | Purpose |
|---|---|---|---|
| `sessions` | `(user_id, updated_at desc)` | B-tree | Session sidebar: "my sessions, most recent first" (PRD §6.2). |
| `messages` | `(session_id, created_at)` | B-tree | Ordered message-history retrieval within a session. |
| `artifacts` | `(session_id, created_at)` | B-tree | Listing a session's artifacts (now served via `sessions/router.py` per `REPOSITORY_STRUCTURE.md`). |
| `artifacts` | `(message_id)` | B-tree | Resolving the artifact produced by a given message. |
| `research_briefs` | `(artifact_id)` | B-tree (implicit via `UNIQUE`) | 1:1 lookup from artifact → brief. |
| `transcript_chunks` | `(episode_id)` | B-tree | "All chunks for this episode" (ingestion, debugging, citation display). |
| `transcript_chunks` | `(episode_id, start_timestamp_seconds)` | B-tree *(optional)* | Chronological ordering of chunks within an episode, e.g. for a future full-transcript view; not required by QA/Research retrieval, which goes through the vector index. |
| `transcript_chunks` | `(embedding)` | **HNSW** (`vector_cosine_ops`) | Semantic similarity search — see §5. |
| `citations` | `(message_id, transcript_chunk_id)` | B-tree (implicit via `UNIQUE`) | Dedup + "citations for this message" lookups. |
| `citations` | `(transcript_chunk_id)` | B-tree | Reverse lookup: "which messages cite this chunk" (useful for corpus-quality analytics). |
| `episodes` | `(published_at)` | B-tree *(optional)* | Chronological browsing/filtering if ever exposed; low priority for MVP. |

```sql
create index idx_sessions_user_recency        on public.sessions (user_id, updated_at desc);
create index idx_messages_session_created     on public.messages (session_id, created_at);
create index idx_artifacts_session_created    on public.artifacts (session_id, created_at);
create index idx_artifacts_message            on public.artifacts (message_id);
create index idx_transcript_chunks_episode    on public.transcript_chunks (episode_id);
create index idx_citations_chunk              on public.citations (transcript_chunk_id);

-- Vector index — see §5 for parameter rationale.
create index idx_transcript_chunks_embedding
    on public.transcript_chunks
    using hnsw (embedding vector_cosine_ops)
    with (m = 16, ef_construction = 64);
```

---

## 5. pgvector Recommendations

- **Extension**: `vector` (pgvector) ≥ 0.5.0 — required for HNSW index support on Supabase.
- **Dimension**: `vector(1024)`, matching `bge-m3`'s dense embedding output. **Confirm this against the actual dimension returned by the deployed Ollama `bge-m3` model before the first ingestion run** — a mismatch requires a column type change and full re-embed.
- **Distance metric**: cosine similarity (`vector_cosine_ops`), on the assumption that `bge-m3` embeddings are (approximately) L2-normalized, which is standard for BGE-family models. If ingestion testing shows otherwise, switch to `vector_ip_ops` (inner product) — do not use `vector_l2_ops` unless a specific reason emerges, as cosine/inner-product are the conventional choice for retrieval embeddings.
- **Index type — HNSW over IVFFlat**: recommended because:
  - No need to pre-choose a `lists` parameter based on expected row count (IVFFlat requires this and degrades as the corpus grows past the original estimate).
  - Better recall/latency stability as the corpus grows from an initial ingestion batch (Phase 2 of `IMPLEMENTATION_PLAN.md`) to the full catalog (Phase 9).
  - Trade-off: higher build-time cost and memory usage than IVFFlat. For a single-podcast corpus (hundreds of episodes, not millions of chunks), this is acceptable.
- **Build timing**: for the initial bulk ingestion (Phase 2), load all `transcript_chunks` rows *before* creating the HNSW index (or use `CREATE INDEX CONCURRENTLY` if the table is already live) — building HNSW incrementally row-by-row during a large bulk load is slower than bulk-load-then-index.
- **Query-time tuning**: set `hnsw.ef_search` per query (e.g., `SET LOCAL hnsw.ef_search = 40;`) to trade recall for latency. Start at the pgvector default and tune empirically against the grounding-evaluation set described in `IMPLEMENTATION_PLAN.md` §6.
- **Similarity search strategy**:
  - QA skill: embed the user's question once via `bge-m3`, then `SELECT ... ORDER BY embedding <=> :query_embedding LIMIT :k` against `transcript_chunks`, optionally filtered by metadata (e.g., `episode_id = ANY(:episode_filter)`) pushed into the `WHERE` clause.
  - Research skill: issue multiple retrieval queries (one per sub-topic/angle), then merge and de-duplicate results by `transcript_chunk.id` before synthesis, to get genuine cross-episode coverage rather than near-duplicate top-k from a single query.
  - Keep `k` modest (e.g., 5–10 per query) and rely on the LLM's synthesis step rather than pushing very large `k` values through the vector index.
- **Deferred (see §8)**: no `embedding_model` / version column in MVP. If the embedding model ever changes, plan for a full `transcript_chunks` re-embed rather than in-place mutation.

---

## 6. RLS Recommendations

All tables have RLS **enabled**; policies below use Supabase's `auth.uid()` (resolves to the authenticated user's `auth.users.id` from the request JWT).

```sql
alter table public.profiles          enable row level security;
alter table public.sessions          enable row level security;
alter table public.messages          enable row level security;
alter table public.artifacts         enable row level security;
alter table public.research_briefs   enable row level security;
alter table public.episodes          enable row level security;
alter table public.transcript_chunks enable row level security;
alter table public.citations         enable row level security;

-- ---------------------------------------------------------
-- profiles — self only. Row is created by the handle_new_user
-- trigger (SECURITY DEFINER, owned by a role that bypasses RLS),
-- so no INSERT policy is needed for the authenticated role.
-- ---------------------------------------------------------
create policy "profiles_select_own" on public.profiles
    for select using (id = auth.uid());

create policy "profiles_update_own" on public.profiles
    for update using (id = auth.uid());

-- ---------------------------------------------------------
-- sessions — direct ownership via user_id.
-- ---------------------------------------------------------
create policy "sessions_select_own" on public.sessions
    for select using (user_id = auth.uid());

create policy "sessions_insert_own" on public.sessions
    for insert with check (user_id = auth.uid());

create policy "sessions_update_own" on public.sessions
    for update using (user_id = auth.uid());

create policy "sessions_delete_own" on public.sessions
    for delete using (user_id = auth.uid());

-- ---------------------------------------------------------
-- messages — ownership via parent session. Immutable/append-only:
-- SELECT + INSERT only, no UPDATE/DELETE policy (default-deny).
-- ---------------------------------------------------------
create policy "messages_select_own" on public.messages
    for select using (
        exists (
            select 1 from public.sessions s
            where s.id = messages.session_id and s.user_id = auth.uid()
        )
    );

create policy "messages_insert_own" on public.messages
    for insert with check (
        exists (
            select 1 from public.sessions s
            where s.id = messages.session_id and s.user_id = auth.uid()
        )
    );

-- ---------------------------------------------------------
-- artifacts — ownership via parent session. Immutable/append-only,
-- same pattern as messages.
-- ---------------------------------------------------------
create policy "artifacts_select_own" on public.artifacts
    for select using (
        exists (
            select 1 from public.sessions s
            where s.id = artifacts.session_id and s.user_id = auth.uid()
        )
    );

create policy "artifacts_insert_own" on public.artifacts
    for insert with check (
        exists (
            select 1 from public.sessions s
            where s.id = artifacts.session_id and s.user_id = auth.uid()
        )
    );

-- ---------------------------------------------------------
-- research_briefs — ownership via artifact → session.
-- ---------------------------------------------------------
create policy "research_briefs_select_own" on public.research_briefs
    for select using (
        exists (
            select 1 from public.artifacts a
            join public.sessions s on s.id = a.session_id
            where a.id = research_briefs.artifact_id and s.user_id = auth.uid()
        )
    );

create policy "research_briefs_insert_own" on public.research_briefs
    for insert with check (
        exists (
            select 1 from public.artifacts a
            join public.sessions s on s.id = a.session_id
            where a.id = research_briefs.artifact_id and s.user_id = auth.uid()
        )
    );

-- ---------------------------------------------------------
-- citations — ownership via message → session.
-- ---------------------------------------------------------
create policy "citations_select_own" on public.citations
    for select using (
        exists (
            select 1 from public.messages m
            join public.sessions s on s.id = m.session_id
            where m.id = citations.message_id and s.user_id = auth.uid()
        )
    );

create policy "citations_insert_own" on public.citations
    for insert with check (
        exists (
            select 1 from public.messages m
            join public.sessions s on s.id = m.session_id
            where m.id = citations.message_id and s.user_id = auth.uid()
        )
    );

-- ---------------------------------------------------------
-- episodes / transcript_chunks — shared, read-only knowledge
-- corpus. Readable by any authenticated user; no owner column.
-- Writes are performed only by the offline ingestion pipeline
-- using the Supabase service_role key, which bypasses RLS —
-- so no write policies are defined for the authenticated role.
-- ---------------------------------------------------------
create policy "episodes_select_authenticated" on public.episodes
    for select to authenticated using (true);

create policy "transcript_chunks_select_authenticated" on public.transcript_chunks
    for select to authenticated using (true);
```

**Ownership enforcement summary**:

| Resource | Ownership path | Enforced by |
|---|---|---|
| `profiles` | direct (`id`) | RLS `id = auth.uid()` |
| `sessions` | direct (`user_id`) | RLS `user_id = auth.uid()` |
| `messages` | `session_id → sessions.user_id` | RLS `EXISTS` via `sessions` |
| `artifacts` | `session_id → sessions.user_id` | RLS `EXISTS` via `sessions` |
| `research_briefs` | `artifact_id → artifacts.session_id → sessions.user_id` | RLS `EXISTS` via `artifacts` + `sessions` |
| `citations` | `message_id → messages.session_id → sessions.user_id` | RLS `EXISTS` via `messages` + `sessions` |
| `episodes` / `transcript_chunks` | none (shared corpus) | RLS: any authenticated read; writes via `service_role` only |

**Operational dependency (flagged, not solved here — see §8 risk #2)**: these policies only take effect if the querying Postgres connection carries the requesting user's identity as `auth.uid()`. If the FastAPI backend connects using the Supabase `service_role` key for its own database access (common for a custom backend rather than the Supabase auto-generated REST API), RLS is bypassed for that connection and ownership enforcement falls entirely on the application-layer checks already required by `ARCHITECTURE.md` §6. The team should explicitly decide whether the backend forwards/sets the user's JWT per request (so RLS is the enforced boundary) or treats RLS as defense-in-depth behind application-layer checks.

---

## 7. Migration Order

Dependency-respecting order, mapped to `IMPLEMENTATION_PLAN.md` phases. RLS is enabled and policies are created **in the same migration as each table**, not deferred to a final step, so no table ever exists unprotected.

| # | Migration | Depends on | Implementation Plan Phase |
|---|---|---|---|
| 1 | Extensions (`pgcrypto`, `vector`) | — | Phase 0 — Foundations |
| 2 | `profiles` + `handle_new_user` trigger + RLS | `auth.users` (pre-existing) | Phase 0 — Foundations |
| 3 | `sessions` + RLS | `auth.users` | Phase 1 — Auth & Session Management |
| 4 | `messages` + `touch_session_updated_at` trigger + RLS | `sessions` | Phase 1 — Auth & Session Management |
| 5 | `episodes` + RLS | — | Phase 2 — Transcript Ingestion & Retrieval |
| 6 | `transcript_chunks` + HNSW index + RLS | `episodes` | Phase 2 — Transcript Ingestion & Retrieval |
| 7 | `citations` + RLS | `messages`, `transcript_chunks` | Phase 3 — QA Skill |
| 8 | `artifacts` + RLS | `sessions`, `messages` | Phase 4 — Artifact System |
| 9 | `research_briefs` + `enforce_research_brief_artifact_type` trigger + RLS | `artifacts` | Phase 6 — Research Skill |

These can be implemented as either Supabase CLI SQL migrations or raw-SQL Alembic revisions under `backend/app/database/migrations/versions/` (per `REPOSITORY_STRUCTURE.md`) — no new tooling is implied either way; RLS/trigger DDL is plain SQL and can be embedded in either mechanism.

**Impact of CHANGE 1 / CHANGE 2 on this table**: no new migration steps and no reordering. Neither change has been implemented yet (design-stage only), so both are amendments folded directly into their existing migration: the `'system'` role value is part of migration **#4** (`messages`), and `start_timestamp_seconds`/`end_timestamp_seconds` are part of migration **#6** (`transcript_chunks`). If either migration had already shipped, these would instead need to be separate `ALTER TABLE` follow-up migrations — worth remembering once the schema moves from design to implementation.

---

## 8. Schema Risks & Tradeoffs

1. **`CHECK` constraints instead of native Postgres `ENUM` types** (`role`, `skill_used`, `artifact_type`). Chosen for extensibility — adding a new artifact type or skill is a single `ALTER TABLE ... DROP CONSTRAINT / ADD CONSTRAINT` migration, avoiding Postgres's transactional restrictions on `ALTER TYPE ... ADD VALUE`. Tradeoff: slightly weaker DB-level type safety; the literal value sets must stay in sync with `DOMAIN_MODEL.md` §5 by convention, not by the type system.

2. **RLS effectiveness depends on backend connection strategy.** If the FastAPI backend uses the Supabase `service_role` key for its own Postgres access, RLS is bypassed for all backend-issued queries, and ownership enforcement is entirely application-layer (already mandated by `ARCHITECTURE.md` §6, so no regression — but it means the RLS policies in §6 only provide their intended DB-layer guarantee if the backend explicitly propagates the user's JWT per request). This is an operational decision the team should make explicitly before launch, not a schema defect.

   **Resolved for MVP: Option A — `service_role` connection, application-layer enforcement primary, RLS as defense-in-depth.** The FastAPI backend connects with the Supabase `service_role` key; every domain's `service.py`/`repository.py` explicitly scopes queries by the authenticated `user_id` (already required regardless of which option was chosen). RLS policies in §6 stay defined and enabled exactly as written — they cost nothing to keep and immediately protect any future direct-to-Supabase client path (e.g., a later real-time feature) without extra work. Rationale, specifically for this project's constraints:
   - **Internship assignment**: a single, inspectable enforcement layer (Python service code) is easier to reason about, demonstrate, and grade than logic split across FastAPI dependencies *and* SQL policies that must independently stay correct and in sync.
   - **MVP delivery speed**: Option B requires propagating the verified user JWT into every pooled Postgres connection per request (e.g., `SET LOCAL request.jwt.claims`) so `auth.uid()` resolves correctly — nontrivial to get right with an async connection pool, and pure plumbing that adds no user-facing capability.
   - **Implementation simplicity**: application-layer ownership checks are unit-testable in isolation; they don't require spinning up Postgres with real RLS policies and a simulated JWT to verify authorization logic.
   - **No schema or architecture change required** — this is a connection-strategy decision for the backend, not a change to any DDL in this document; `CONTEXT.md`'s auth architecture (Supabase Auth as source of truth) is unaffected.

3. **`citations.transcript_chunk_id` uses `ON DELETE RESTRICT`, not `CASCADE`.** This protects historical grounding data (a citation attached to an already-generated answer) from silently disappearing if the ingestion pipeline re-chunks or deletes an episode's transcript. Tradeoff: the ingestion pipeline cannot blindly `DELETE ... WHERE episode_id = ...` and re-insert on re-ingestion if any chunk has been cited — it must either avoid hard-deleting cited chunks or migrate/repoint citations first. Recommended ingestion pattern: treat `transcript_chunks` as append-only/versioned rather than delete-and-replace.

4. **No `content_html` column on `artifacts`.** HTML is derived from `content_markdown` at render time (per ADR-4 in `ARCHITECTURE.md`), keeping a single source of truth and guaranteeing Copy/Download always match what's rendered. Tradeoff: every HTML view incurs a render/sanitize step rather than reading a precomputed value — acceptable at MVP scale; revisit only if this becomes a measured bottleneck.

5. **No embedding-model/version column on `transcript_chunks` in MVP.** `DOMAIN_MODEL.md` §4.7 already flags that embeddings must be regenerated if the embedding model changes; without a version marker, a future `bge-m3` upgrade or model swap requires either a full re-embed-and-replace of the table or an out-of-band tracking mechanism. Deferred here to avoid adding attributes beyond what's currently specified — flagged as a near-term follow-up to revisit before the first embedding-model change, not before.

6. **`RoutingDecision` and `ModelInvocation` remain unimplemented**, per the prior MVP-simplification decision (`REPOSITORY_STRUCTURE.md`). If/when persisted later, both are purely additive migrations (new table + FK to `messages`) with zero impact on this schema — no retrofitting required.

7. **Fixed `vector(1024)` dimension.** Tied to `bge-m3`'s dense embedding output. If the embedding provider or model ever changes to a different output dimension, the column type must change (`ALTER COLUMN embedding TYPE vector(N)`), which forces a full re-embed of the corpus — same underlying risk as #5, called out separately because it's a schema-level (not just operational) constraint.

8. **`messages` and `artifacts` are treated as immutable/append-only** — RLS defines `SELECT`/`INSERT` policies only, no `UPDATE`/`DELETE`, which default-denies those operations at the DB layer regardless of what the application attempts. This matches the "chat transcript + generated artifact" mental model in the PRD, but means corrections (e.g., "regenerate this artifact") must be modeled as new rows rather than in-place edits. Worth confirming this matches the intended product UX before implementation.

9. **`profiles` is intentionally minimal** (`id`, `display_name`, timestamps). The PRD does not yet specify profile fields beyond auth identity (email/password already live in `auth.users`), so the table is kept thin rather than speculatively adding fields — consistent with "do not introduce new entities."

10. **`system`-role messages have no dedicated schema guardrails beyond the role check.** Nothing stops the application from writing an unbounded number of system messages into a session (e.g., one per retrieval call), which would bloat `messages.content` for that session and clutter the transcript-reconstruction view described in CHANGE 1. This is intentionally left as an application-layer discipline question (what counts as a system message worth persisting vs. what belongs only in structured application logs), not a schema constraint — the team should establish that convention before the router/skills start writing them.

11. **Timestamp fields depend on the ingestion source actually providing time-aligned segments.** `start_timestamp_seconds`/`end_timestamp_seconds` are `NOT NULL`, which assumes every transcript source used by the Phase 2 ingestion pipeline (`IMPLEMENTATION_PLAN.md`) carries time-aligned segments (true for ASR-generated podcast transcripts, the expected source per `PRD.md` §2). If a transcript source ever lacks timing data, ingestion for that source would fail the `NOT NULL` constraint rather than degrade silently — treated as a feature (fail loudly) rather than a bug, but worth confirming against the actual transcript source format before Phase 2 begins.
