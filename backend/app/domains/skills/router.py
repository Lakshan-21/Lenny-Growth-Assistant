"""HTTP endpoint that receives a user message for a session and returns the
assistant's reply (REPOSITORY_STRUCTURE.md §3, skills/router.py).

Current scope: `mode="auto"` (or `mode="manual", skill="qa"`) runs the QA
skill (retrieval -> grounded generation -> citations, PRD §6.3).
`mode="manual", skill="ship30"` runs Ship30 instead (PRD §6.5) — transforms
prior session content into a LinkedIn post / X thread / article.
`mode="manual", skill="research"` runs Research instead (PRD §6.4) —
multi-query cross-episode retrieval, synthesized into a structured brief.
The Artifact skill remains unimplemented, so any other explicit `skill`
selection is rejected outright rather than silently answered by QA
anyway, since that would misrepresent what actually ran.

Artifact persistence is generic, not skill-specific: any `SkillResult`
with `artifact_type` set gets persisted as an `Artifact`. Research
additionally sets `research_topic`/`research_summary`, which — and only
when `artifact_type == "research_brief"` — also get persisted as the
`ResearchBrief` specialization row (DOMAIN_MODEL.md §4.9); this one extra
step is unavoidably research-specific, since no other skill has a second
specialization table.

NOTE on route ownership (implementation assumption — see generation
summary): this endpoint is nested under `/sessions/{session_id}/messages`
even though it lives in the `skills` router module, because it owns the
model-invocation concern. `sessions/router.py` owns session CRUD and
artifact read-access only.

NOTE on streaming: ARCHITECTURE.md specifies a streamed (SSE) response for
this endpoint in production. This implementation is non-streaming —
converting to `StreamingResponse` is a follow-up, not required by the
current scope.
"""

from fastapi import APIRouter, Depends, status

from app.domains.artifacts.dependencies import get_artifact_service
from app.domains.artifacts.service import ArtifactService
from app.domains.knowledge.dependencies import get_knowledge_repository
from app.domains.knowledge.repository import KnowledgeRepository
from app.domains.sessions.dependencies import get_owned_session, get_session_service
from app.domains.sessions.models import Session
from app.domains.sessions.schemas import CitationRead, MessageRead
from app.domains.sessions.service import SessionService
from app.domains.skills.base import Skill
from app.domains.skills.dependencies import get_qa_skill, get_research_skill, get_ship30_skill
from app.domains.skills.exceptions import UnroutableMessageError
from app.domains.skills.qa.service import QASkill
from app.domains.skills.research.service import ResearchSkill
from app.domains.skills.schemas import ConversationTurn, SkillContext, SkillInvocationRequest, SkillInvocationResponse
from app.domains.skills.ship30.service import Ship30Skill

router = APIRouter(prefix="/sessions", tags=["skills"])

_IMPLEMENTED_SKILLS = ("qa", "ship30", "research")


@router.post(
    "/{session_id}/messages",
    response_model=SkillInvocationResponse,
    status_code=status.HTTP_201_CREATED,
)
async def post_message(
    data: SkillInvocationRequest,
    session: Session = Depends(get_owned_session),
    session_service: SessionService = Depends(get_session_service),
    qa_skill: QASkill = Depends(get_qa_skill),
    ship30_skill: Ship30Skill = Depends(get_ship30_skill),
    research_skill: ResearchSkill = Depends(get_research_skill),
    knowledge_repository: KnowledgeRepository = Depends(get_knowledge_repository),
    artifact_service: ArtifactService = Depends(get_artifact_service),
) -> SkillInvocationResponse:
    """Post a user message; answer it via QA, Ship30, or Research; persist
    the resulting message, any artifact it produced, and its citations.

    1. Ownership verified by the `get_owned_session` dependency itself.
    2. Load session history (chronological — `sessions.models.Session
       .messages` is ordered by `created_at`).
    3. Persist the user's message.
    4-5. Run the selected skill (QA by default; Ship30/Research on
       explicit manual selection — see module docstring).
    6. Persist the assistant's reply.
    7. If the skill produced an artifact (`SkillResult.artifact_type`),
       persist it — generic across skills. For a research brief
       specifically, also persist the `ResearchBrief` row. Then persist
       one `Citation` row per source chunk (QA/Research).
    8. Return the reply with its citations and artifact id, if any.

    Transaction safety: steps 3, 6, 7, and citation persistence all only
    `flush()` (see */repository.py) — the whole request commits or rolls
    back together via `app.database.session.get_db`. If retrieval,
    generation, or persistence fails partway through, everything already
    flushed in this request rolls back too — no partial state (a
    reply-less message, or a message without its artifact) is ever left
    stranded.
    """

    if data.mode == "manual" and data.skill not in (None, *_IMPLEMENTED_SKILLS):
        raise UnroutableMessageError(
            f"Manual selection of skill={data.skill!r} is not yet supported — "
            f"only {_IMPLEMENTED_SKILLS} are implemented (mode='auto' runs 'qa' by default)."
        )

    use_ship30 = data.mode == "manual" and data.skill == "ship30"
    use_research = data.mode == "manual" and data.skill == "research"

    if use_ship30 and data.content_type is None:
        raise UnroutableMessageError(
            "skill='ship30' requires a content_type (one of: linkedin_post, x_thread, article)."
        )

    # 2. Load history before persisting the new message, so it isn't
    #    duplicated into the SkillContext built below.
    session_with_history = await session_service.get_session_with_history(
        session_id=session.id, user_id=session.user_id
    )

    # 3. Persist the user's message.
    await session_service.append_message(session_id=session.id, role="user", content=data.content)

    # 4-5. Run the selected skill.
    context = SkillContext(
        session_id=session.id,
        user_id=session.user_id,
        message=data.content,
        history=[
            ConversationTurn(role=message.role, content=message.content)
            for message in session_with_history.messages
        ],
        content_type=data.content_type,
        source_artifact_id=data.source_artifact_id,
    )
    skill: Skill = ship30_skill if use_ship30 else research_skill if use_research else qa_skill
    result = await skill.handle(context)

    # 6. Persist the reply.
    assistant_message = await session_service.append_message(
        session_id=session.id, role="assistant", content=result.content_markdown, skill_used=result.skill
    )

    # 7. Persist the artifact (if any), the ResearchBrief specialization
    #    row (research only), and citations (if any).
    artifact_id = None
    if result.artifact_type is not None:
        artifact = await artifact_service.create(
            session_id=session.id,
            message_id=assistant_message.id,
            artifact_type=result.artifact_type,
            content_markdown=result.content_markdown,
        )
        artifact_id = artifact.id

        if result.artifact_type == "research_brief":
            await artifact_service.create_research_brief(
                artifact=artifact,
                topic=result.research_topic or "",
                summary=result.research_summary or "",
            )

    for citation in result.citations:
        await knowledge_repository.create_citation(
            message_id=assistant_message.id,
            transcript_chunk_id=citation.transcript_chunk_id,
            display_label=citation.display_label,
        )

    # 8. Return it.
    #
    # Explicit DTO construction, not `MessageRead.model_validate
    # (assistant_message)`: `assistant_message` is a freshly-flushed ORM
    # object whose `citations` relationship was never eagerly loaded (the
    # rows were just inserted above via `knowledge_repository
    # .create_citation`, individually, never through this object's ORM
    # collection). Letting Pydantic's `from_attributes` touch `.citations`
    # here would trigger a lazy load on an already-persistent object
    # outside a greenlet context (MissingGreenlet) — the same bug class as
    # the `POST /sessions` fix in `sessions/router.py::create_session`.
    # `result.citations` already has everything `CitationRead` needs
    # (`CitationRef.excerpt` is the retrieved chunk's text, identical to
    # what a DB round-trip through `Citation.transcript_chunk.content`
    # would produce), so it's used directly instead of re-reading the ORM
    # relationship.
    message = MessageRead(
        id=assistant_message.id,
        session_id=assistant_message.session_id,
        role=assistant_message.role,
        content=assistant_message.content,
        skill_used=assistant_message.skill_used,
        created_at=assistant_message.created_at,
        citations=[CitationRead(display_label=c.display_label, excerpt=c.excerpt) for c in result.citations],
    )
    return SkillInvocationResponse(
        skill_used=result.skill,
        routing_mode=data.mode,
        message=message,
        citations=result.citations,
        artifact_id=artifact_id,
    )
