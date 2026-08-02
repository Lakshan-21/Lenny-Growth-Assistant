"""Initial schema — extensions, all tables, constraints, indexes, triggers, RLS.

Consolidates DATABASE_SCHEMA.md's nine logical migration steps (§7) into a
single initial migration, since this is a not-yet-deployed project (no live
data to migrate incrementally against) — see the generation summary's
implementation assumptions for the full rationale. Internal statement order
still follows DATABASE_SCHEMA.md §7's dependency sequence: profiles ->
sessions -> messages -> episodes -> transcript_chunks -> citations ->
artifacts -> research_briefs, with each table's own indexes and RLS
policies created immediately after it (never deferred to a final step).

Written as literal SQL (op.execute) rather than Alembic's table-building
DSL, for byte-level fidelity to DATABASE_SCHEMA.md — the authoritative,
hand-written source for this schema — and because triggers/RLS have no
native Alembic DSL representation anyway.

Revision ID: 0001
Revises:
Create Date: 2026-08-02
"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # =====================================================================
    # 0. Extensions
    # =====================================================================
    op.execute(sa.text("CREATE EXTENSION IF NOT EXISTS pgcrypto"))
    op.execute(sa.text("CREATE EXTENSION IF NOT EXISTS vector"))

    # =====================================================================
    # 1. profiles
    # =====================================================================
    op.execute(
        sa.text(
            """
            CREATE TABLE public.profiles (
                id           uuid PRIMARY KEY REFERENCES auth.users (id) ON DELETE CASCADE,
                display_name text,
                created_at   timestamptz NOT NULL DEFAULT now(),
                updated_at   timestamptz NOT NULL DEFAULT now()
            )
            """
        )
    )
    op.execute(
        sa.text(
            "COMMENT ON TABLE public.profiles IS "
            "'Optional profile data extending auth.users. auth.users remains "
            "the source of truth for identity/credentials.'"
        )
    )
    op.execute(
        sa.text(
            """
            CREATE FUNCTION public.handle_new_user()
            RETURNS trigger
            LANGUAGE plpgsql
            SECURITY DEFINER
            SET search_path = public
            AS $$
            BEGIN
                INSERT INTO public.profiles (id) VALUES (new.id);
                RETURN new;
            END;
            $$
            """
        )
    )
    op.execute(
        sa.text(
            """
            CREATE TRIGGER on_auth_user_created
            AFTER INSERT ON auth.users
            FOR EACH ROW EXECUTE FUNCTION public.handle_new_user()
            """
        )
    )
    op.execute(sa.text("ALTER TABLE public.profiles ENABLE ROW LEVEL SECURITY"))
    op.execute(
        sa.text(
            'CREATE POLICY "profiles_select_own" ON public.profiles '
            "FOR SELECT USING (id = auth.uid())"
        )
    )
    op.execute(
        sa.text(
            'CREATE POLICY "profiles_update_own" ON public.profiles '
            "FOR UPDATE USING (id = auth.uid())"
        )
    )

    # =====================================================================
    # 2. sessions
    # =====================================================================
    op.execute(
        sa.text(
            """
            CREATE TABLE public.sessions (
                id         uuid PRIMARY KEY DEFAULT gen_random_uuid(),
                user_id    uuid NOT NULL REFERENCES auth.users (id) ON DELETE CASCADE,
                title      text NOT NULL DEFAULT 'New session',
                created_at timestamptz NOT NULL DEFAULT now(),
                updated_at timestamptz NOT NULL DEFAULT now()
            )
            """
        )
    )
    op.execute(
        sa.text(
            "COMMENT ON COLUMN public.sessions.updated_at IS "
            "'Bumped by the messages_touch_session trigger on every new message; "
            "drives session-sidebar recency ordering.'"
        )
    )
    op.create_index(
        "idx_sessions_user_recency", "sessions", ["user_id", sa.text("updated_at DESC")], schema="public"
    )
    op.execute(sa.text("ALTER TABLE public.sessions ENABLE ROW LEVEL SECURITY"))
    op.execute(
        sa.text(
            'CREATE POLICY "sessions_select_own" ON public.sessions '
            "FOR SELECT USING (user_id = auth.uid())"
        )
    )
    op.execute(
        sa.text(
            'CREATE POLICY "sessions_insert_own" ON public.sessions '
            "FOR INSERT WITH CHECK (user_id = auth.uid())"
        )
    )
    op.execute(
        sa.text(
            'CREATE POLICY "sessions_update_own" ON public.sessions '
            "FOR UPDATE USING (user_id = auth.uid())"
        )
    )
    op.execute(
        sa.text(
            'CREATE POLICY "sessions_delete_own" ON public.sessions '
            "FOR DELETE USING (user_id = auth.uid())"
        )
    )

    # =====================================================================
    # 3. messages
    # =====================================================================
    op.execute(
        sa.text(
            """
            CREATE TABLE public.messages (
                id         uuid PRIMARY KEY DEFAULT gen_random_uuid(),
                session_id uuid NOT NULL REFERENCES public.sessions (id) ON DELETE CASCADE,
                role       text NOT NULL,
                content    text NOT NULL,
                skill_used text,
                created_at timestamptz NOT NULL DEFAULT now(),

                CONSTRAINT ck_messages_role
                    CHECK (role IN ('user', 'assistant', 'system')),
                CONSTRAINT ck_messages_skill_used
                    CHECK (skill_used IS NULL OR skill_used IN ('qa', 'research', 'ship30', 'artifact')),
                CONSTRAINT ck_messages_skill_used_only_for_assistant
                    CHECK (role = 'assistant' OR skill_used IS NULL)
            )
            """
        )
    )
    op.execute(
        sa.text(
            "COMMENT ON COLUMN public.messages.role IS "
            "'user | assistant | system. System messages carry router/skill-injected "
            "context (prompt-construction notes, routing/hand-off markers, operational "
            "breadcrumbs) as first-class, session-scoped conversation turns.'"
        )
    )
    op.execute(
        sa.text(
            "COMMENT ON COLUMN public.messages.skill_used IS "
            "'Which skill produced this message. Always null for role=''user'' or "
            "role=''system''. Nullable for role=''assistant'' to allow ungrounded/error "
            "responses.'"
        )
    )
    op.execute(
        sa.text(
            """
            CREATE FUNCTION public.touch_session_updated_at()
            RETURNS trigger
            LANGUAGE plpgsql
            AS $$
            BEGIN
                UPDATE public.sessions SET updated_at = now() WHERE id = new.session_id;
                RETURN new;
            END;
            $$
            """
        )
    )
    op.execute(
        sa.text(
            """
            CREATE TRIGGER messages_touch_session
            AFTER INSERT ON public.messages
            FOR EACH ROW EXECUTE FUNCTION public.touch_session_updated_at()
            """
        )
    )
    op.create_index("idx_messages_session_created", "messages", ["session_id", "created_at"], schema="public")
    op.execute(sa.text("ALTER TABLE public.messages ENABLE ROW LEVEL SECURITY"))
    op.execute(
        sa.text(
            'CREATE POLICY "messages_select_own" ON public.messages '
            "FOR SELECT USING ("
            "  EXISTS ("
            "    SELECT 1 FROM public.sessions s"
            "    WHERE s.id = messages.session_id AND s.user_id = auth.uid()"
            "  )"
            ")"
        )
    )
    op.execute(
        sa.text(
            'CREATE POLICY "messages_insert_own" ON public.messages '
            "FOR INSERT WITH CHECK ("
            "  EXISTS ("
            "    SELECT 1 FROM public.sessions s"
            "    WHERE s.id = messages.session_id AND s.user_id = auth.uid()"
            "  )"
            ")"
        )
    )

    # =====================================================================
    # 4. episodes
    # =====================================================================
    op.execute(
        sa.text(
            """
            CREATE TABLE public.episodes (
                id           uuid PRIMARY KEY DEFAULT gen_random_uuid(),
                title        text NOT NULL,
                guest_name   text,
                published_at date,
                source_url   text,
                created_at   timestamptz NOT NULL DEFAULT now()
            )
            """
        )
    )
    op.execute(sa.text("ALTER TABLE public.episodes ENABLE ROW LEVEL SECURITY"))
    op.execute(
        sa.text(
            'CREATE POLICY "episodes_select_authenticated" ON public.episodes '
            "FOR SELECT TO authenticated USING (true)"
        )
    )

    # =====================================================================
    # 5. transcript_chunks
    # =====================================================================
    op.execute(
        sa.text(
            """
            CREATE TABLE public.transcript_chunks (
                id                      uuid PRIMARY KEY DEFAULT gen_random_uuid(),
                episode_id              uuid NOT NULL REFERENCES public.episodes (id) ON DELETE CASCADE,
                content                 text NOT NULL,
                embedding               vector(1024) NOT NULL,
                start_offset            integer NOT NULL,
                end_offset              integer NOT NULL,
                start_timestamp_seconds integer NOT NULL,
                end_timestamp_seconds   integer NOT NULL,
                created_at              timestamptz NOT NULL DEFAULT now(),

                CONSTRAINT ck_transcript_chunks_offsets_valid
                    CHECK (end_offset > start_offset),
                CONSTRAINT ck_transcript_chunks_timestamps_valid
                    CHECK (end_timestamp_seconds > start_timestamp_seconds AND start_timestamp_seconds >= 0)
            )
            """
        )
    )
    op.execute(
        sa.text(
            "COMMENT ON COLUMN public.transcript_chunks.embedding IS "
            "'bge-m3 dense embedding dimension (1024) — confirm against the deployed "
            "Ollama model before first ingestion.'"
        )
    )
    op.execute(
        sa.text(
            "COMMENT ON COLUMN public.transcript_chunks.start_offset IS "
            "'Character/token offset within the episode transcript text — used for "
            "text-level chunk boundaries, not display.'"
        )
    )
    op.execute(
        sa.text(
            "COMMENT ON COLUMN public.transcript_chunks.start_timestamp_seconds IS "
            "'Audio-time offset (whole seconds) into the episode. Used to render "
            "citation timestamps (e.g., \"12:34-13:02\"), independent of the "
            "text-level start_offset/end_offset pair.'"
        )
    )
    op.create_index(
        "idx_transcript_chunks_episode", "transcript_chunks", ["episode_id"], schema="public"
    )
    op.create_index(
        "idx_transcript_chunks_episode_timestamp",
        "transcript_chunks",
        ["episode_id", "start_timestamp_seconds"],
        schema="public",
    )
    op.execute(
        sa.text(
            "CREATE INDEX idx_transcript_chunks_embedding "
            "ON public.transcript_chunks "
            "USING hnsw (embedding vector_cosine_ops) "
            "WITH (m = 16, ef_construction = 64)"
        )
    )
    op.execute(sa.text("ALTER TABLE public.transcript_chunks ENABLE ROW LEVEL SECURITY"))
    op.execute(
        sa.text(
            'CREATE POLICY "transcript_chunks_select_authenticated" ON public.transcript_chunks '
            "FOR SELECT TO authenticated USING (true)"
        )
    )

    # =====================================================================
    # 6. citations
    # =====================================================================
    op.execute(
        sa.text(
            """
            CREATE TABLE public.citations (
                id                  uuid PRIMARY KEY DEFAULT gen_random_uuid(),
                message_id          uuid NOT NULL REFERENCES public.messages (id) ON DELETE CASCADE,
                transcript_chunk_id uuid NOT NULL REFERENCES public.transcript_chunks (id) ON DELETE RESTRICT,
                display_label       text NOT NULL,
                created_at          timestamptz NOT NULL DEFAULT now(),

                CONSTRAINT uq_citations_message_chunk UNIQUE (message_id, transcript_chunk_id)
            )
            """
        )
    )
    op.execute(
        sa.text(
            "COMMENT ON CONSTRAINT citations_transcript_chunk_id_fkey ON public.citations IS "
            "'ON DELETE RESTRICT deliberately: prevents ingestion re-runs from silently "
            "orphaning grounding data behind already-generated answers. See "
            "DATABASE_SCHEMA.md sec 8.'"
        )
    )
    op.execute(
        sa.text(
            "COMMENT ON COLUMN public.citations.display_label IS "
            "'Denormalized, human-readable citation text, e.g. \"Episode 142 - "
            "12:34-13:02\". Composed from episodes.title/guest_name and "
            "transcript_chunks.start_timestamp_seconds/end_timestamp_seconds at "
            "generation time; stored as a snapshot so display is stable even if the "
            "source chunk is later re-ingested.'"
        )
    )
    op.create_index("idx_citations_chunk", "citations", ["transcript_chunk_id"], schema="public")
    op.execute(sa.text("ALTER TABLE public.citations ENABLE ROW LEVEL SECURITY"))
    op.execute(
        sa.text(
            'CREATE POLICY "citations_select_own" ON public.citations '
            "FOR SELECT USING ("
            "  EXISTS ("
            "    SELECT 1 FROM public.messages m"
            "    JOIN public.sessions s ON s.id = m.session_id"
            "    WHERE m.id = citations.message_id AND s.user_id = auth.uid()"
            "  )"
            ")"
        )
    )
    op.execute(
        sa.text(
            'CREATE POLICY "citations_insert_own" ON public.citations '
            "FOR INSERT WITH CHECK ("
            "  EXISTS ("
            "    SELECT 1 FROM public.messages m"
            "    JOIN public.sessions s ON s.id = m.session_id"
            "    WHERE m.id = citations.message_id AND s.user_id = auth.uid()"
            "  )"
            ")"
        )
    )

    # =====================================================================
    # 7. artifacts
    # =====================================================================
    op.execute(
        sa.text(
            """
            CREATE TABLE public.artifacts (
                id               uuid PRIMARY KEY DEFAULT gen_random_uuid(),
                session_id       uuid NOT NULL REFERENCES public.sessions (id) ON DELETE CASCADE,
                message_id       uuid NOT NULL REFERENCES public.messages (id) ON DELETE CASCADE,
                artifact_type    text NOT NULL,
                content_markdown text NOT NULL,
                created_at       timestamptz NOT NULL DEFAULT now(),

                CONSTRAINT ck_artifacts_artifact_type
                    CHECK (artifact_type IN ('qa_answer', 'research_brief', 'linkedin_post', 'x_thread', 'article'))
            )
            """
        )
    )
    op.execute(
        sa.text(
            "COMMENT ON COLUMN public.artifacts.content_markdown IS "
            "'Canonical source of truth (ADR-4, ARCHITECTURE.md). HTML rendering is "
            "derived at read time -- no content_html column.'"
        )
    )
    op.create_index("idx_artifacts_session_created", "artifacts", ["session_id", "created_at"], schema="public")
    op.create_index("idx_artifacts_message", "artifacts", ["message_id"], schema="public")
    op.execute(sa.text("ALTER TABLE public.artifacts ENABLE ROW LEVEL SECURITY"))
    op.execute(
        sa.text(
            'CREATE POLICY "artifacts_select_own" ON public.artifacts '
            "FOR SELECT USING ("
            "  EXISTS ("
            "    SELECT 1 FROM public.sessions s"
            "    WHERE s.id = artifacts.session_id AND s.user_id = auth.uid()"
            "  )"
            ")"
        )
    )
    op.execute(
        sa.text(
            'CREATE POLICY "artifacts_insert_own" ON public.artifacts '
            "FOR INSERT WITH CHECK ("
            "  EXISTS ("
            "    SELECT 1 FROM public.sessions s"
            "    WHERE s.id = artifacts.session_id AND s.user_id = auth.uid()"
            "  )"
            ")"
        )
    )

    # =====================================================================
    # 8. research_briefs
    # =====================================================================
    op.execute(
        sa.text(
            """
            CREATE TABLE public.research_briefs (
                id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
                artifact_id uuid NOT NULL REFERENCES public.artifacts (id) ON DELETE CASCADE,
                topic       text NOT NULL,
                summary     text NOT NULL,
                created_at  timestamptz NOT NULL DEFAULT now(),

                CONSTRAINT uq_research_briefs_artifact_id UNIQUE (artifact_id)
            )
            """
        )
    )
    op.execute(
        sa.text(
            """
            CREATE FUNCTION public.enforce_research_brief_artifact_type()
            RETURNS trigger
            LANGUAGE plpgsql
            AS $$
            DECLARE
                v_type text;
            BEGIN
                SELECT artifact_type INTO v_type FROM public.artifacts WHERE id = new.artifact_id;
                IF v_type IS DISTINCT FROM 'research_brief' THEN
                    RAISE EXCEPTION
                        'research_briefs.artifact_id must reference an artifact with artifact_type = ''research_brief'' (got %)',
                        v_type;
                END IF;
                RETURN new;
            END;
            $$
            """
        )
    )
    op.execute(
        sa.text(
            """
            CREATE TRIGGER research_briefs_check_artifact_type
            BEFORE INSERT OR UPDATE ON public.research_briefs
            FOR EACH ROW EXECUTE FUNCTION public.enforce_research_brief_artifact_type()
            """
        )
    )
    op.execute(sa.text("ALTER TABLE public.research_briefs ENABLE ROW LEVEL SECURITY"))
    op.execute(
        sa.text(
            'CREATE POLICY "research_briefs_select_own" ON public.research_briefs '
            "FOR SELECT USING ("
            "  EXISTS ("
            "    SELECT 1 FROM public.artifacts a"
            "    JOIN public.sessions s ON s.id = a.session_id"
            "    WHERE a.id = research_briefs.artifact_id AND s.user_id = auth.uid()"
            "  )"
            ")"
        )
    )
    op.execute(
        sa.text(
            'CREATE POLICY "research_briefs_insert_own" ON public.research_briefs '
            "FOR INSERT WITH CHECK ("
            "  EXISTS ("
            "    SELECT 1 FROM public.artifacts a"
            "    JOIN public.sessions s ON s.id = a.session_id"
            "    WHERE a.id = research_briefs.artifact_id AND s.user_id = auth.uid()"
            "  )"
            ")"
        )
    )


def downgrade() -> None:
    # Reverse order of upgrade(). Extensions are deliberately NOT dropped
    # (pgcrypto/vector may be relied on elsewhere in the database; dropping
    # extensions is not part of a clean schema-only downgrade).

    # --- 8. research_briefs ---
    op.execute(sa.text('DROP POLICY IF EXISTS "research_briefs_insert_own" ON public.research_briefs'))
    op.execute(sa.text('DROP POLICY IF EXISTS "research_briefs_select_own" ON public.research_briefs'))
    op.execute(sa.text("DROP TRIGGER IF EXISTS research_briefs_check_artifact_type ON public.research_briefs"))
    op.execute(sa.text("DROP FUNCTION IF EXISTS public.enforce_research_brief_artifact_type()"))
    op.drop_table("research_briefs", schema="public")

    # --- 7. artifacts ---
    op.execute(sa.text('DROP POLICY IF EXISTS "artifacts_insert_own" ON public.artifacts'))
    op.execute(sa.text('DROP POLICY IF EXISTS "artifacts_select_own" ON public.artifacts'))
    op.drop_index("idx_artifacts_message", table_name="artifacts", schema="public")
    op.drop_index("idx_artifacts_session_created", table_name="artifacts", schema="public")
    op.drop_table("artifacts", schema="public")

    # --- 6. citations ---
    op.execute(sa.text('DROP POLICY IF EXISTS "citations_insert_own" ON public.citations'))
    op.execute(sa.text('DROP POLICY IF EXISTS "citations_select_own" ON public.citations'))
    op.drop_index("idx_citations_chunk", table_name="citations", schema="public")
    op.drop_table("citations", schema="public")

    # --- 5. transcript_chunks ---
    op.execute(
        sa.text('DROP POLICY IF EXISTS "transcript_chunks_select_authenticated" ON public.transcript_chunks')
    )
    op.execute(sa.text("DROP INDEX IF EXISTS public.idx_transcript_chunks_embedding"))
    op.drop_index("idx_transcript_chunks_episode_timestamp", table_name="transcript_chunks", schema="public")
    op.drop_index("idx_transcript_chunks_episode", table_name="transcript_chunks", schema="public")
    op.drop_table("transcript_chunks", schema="public")

    # --- 4. episodes ---
    op.execute(sa.text('DROP POLICY IF EXISTS "episodes_select_authenticated" ON public.episodes'))
    op.drop_table("episodes", schema="public")

    # --- 3. messages ---
    op.execute(sa.text('DROP POLICY IF EXISTS "messages_insert_own" ON public.messages'))
    op.execute(sa.text('DROP POLICY IF EXISTS "messages_select_own" ON public.messages'))
    op.drop_index("idx_messages_session_created", table_name="messages", schema="public")
    op.execute(sa.text("DROP TRIGGER IF EXISTS messages_touch_session ON public.messages"))
    op.execute(sa.text("DROP FUNCTION IF EXISTS public.touch_session_updated_at()"))
    op.drop_table("messages", schema="public")

    # --- 2. sessions ---
    op.execute(sa.text('DROP POLICY IF EXISTS "sessions_delete_own" ON public.sessions'))
    op.execute(sa.text('DROP POLICY IF EXISTS "sessions_update_own" ON public.sessions'))
    op.execute(sa.text('DROP POLICY IF EXISTS "sessions_insert_own" ON public.sessions'))
    op.execute(sa.text('DROP POLICY IF EXISTS "sessions_select_own" ON public.sessions'))
    op.drop_index("idx_sessions_user_recency", table_name="sessions", schema="public")
    op.drop_table("sessions", schema="public")

    # --- 1. profiles ---
    op.execute(sa.text('DROP POLICY IF EXISTS "profiles_update_own" ON public.profiles'))
    op.execute(sa.text('DROP POLICY IF EXISTS "profiles_select_own" ON public.profiles'))
    op.execute(sa.text("DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users"))
    op.execute(sa.text("DROP FUNCTION IF EXISTS public.handle_new_user()"))
    op.drop_table("profiles", schema="public")
