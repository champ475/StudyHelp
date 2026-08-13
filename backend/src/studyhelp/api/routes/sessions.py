"""Session bootstrap + the full per-step pipeline (verify -> classify ->
orchestrate), streamed via SSE.

Event stream shape, per request:
  - "verdict": structured verifier output (not child-facing prose — no
    gate applies to it, it's a correctness signal, not generated text).
  - "classification": structured diagnostic data (rule/LLM source,
    misconception id) for observability/research logging — also not
    child-facing prose. A real chat UI should not render this event as a
    tutor message; Phase 4's frontend doesn't.
  - "message_chunk": word-chunked pieces of the dialogue turn's message.
    This is the ONLY event carrying LLM-generated child-facing text, and
    it is only ever emitted *after* `handle_step_submission()` has already
    cleared the leakage filter and readability gate — never a speculative
    stream of an unvetted draft (technical_architecture.md §6).
  - "turn_complete": final structured summary of the dialogue turn.

Dev-mode only — no real auth/consent flow yet (ARCHITECTURE.md D18).
Session creation here is a local identity picker for Phase 4, not
something to point at real students.
"""

import dataclasses
import json
import uuid
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from studyhelp.classification.classifier import classify_error
from studyhelp.db.base import get_session
from studyhelp.db.models import ExperimentCondition, SessionModel, User, UserRole
from studyhelp.db.redis import get_redis
from studyhelp.db.repositories.event_repository import log_event
from studyhelp.db.repositories.problem_repository import get_problem
from studyhelp.dialogue.orchestrator import handle_step_submission
from studyhelp.dialogue.state import DialogueStateStore
from studyhelp.dialogue.timing_policy import InterventionPolicy
from studyhelp.llm.client import build_llm_client
from studyhelp.logging import get_logger
from studyhelp.schemas.verify import ProblemState, StudentStep
from studyhelp.verification.interface import registry

router = APIRouter(prefix="/sessions", tags=["sessions"])
logger = get_logger(__name__)


class CreateSessionRequest(BaseModel):
    display_name: str
    experiment_condition: ExperimentCondition | None = None


class CreateSessionResponse(BaseModel):
    session_id: uuid.UUID
    user_id: uuid.UUID


@router.post("", response_model=CreateSessionResponse)
async def create_session(
    request: CreateSessionRequest,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> CreateSessionResponse:
    user = User(id=uuid.uuid4(), role=UserRole.STUDENT, display_name=request.display_name)
    session.add(user)
    await session.flush()

    db_session = SessionModel(
        id=uuid.uuid4(),
        user_id=user.id,
        started_at=datetime.now(UTC),
        experiment_condition=request.experiment_condition,
    )
    session.add(db_session)
    await session.commit()

    return CreateSessionResponse(session_id=db_session.id, user_id=user.id)


class StepSubmissionRequest(BaseModel):
    problem_id: str
    accepted_step_ids: list[str] = Field(default_factory=list)
    student_step: StudentStep
    timing_policy: InterventionPolicy = InterventionPolicy.IMMEDIATE


def _chunk_message(message: str, *, words_per_chunk: int = 3) -> list[str]:
    """Word-chunked "streaming" of an already-fully-vetted message. Once
    real Groq token streaming is wired (Phase 3 follow-up once a key
    exists), this becomes actual token streaming instead of post-hoc
    chunking of a complete string — the SSE event shape doesn't change."""
    words = message.split(" ")
    return [" ".join(words[i : i + words_per_chunk]) for i in range(0, len(words), words_per_chunk)]


def _sse_format(event_name: str, data: dict[str, Any]) -> str:
    return f"event: {event_name}\ndata: {json.dumps(data)}\n\n"


async def _pipeline_events(
    session_id: str, request: StepSubmissionRequest, db: AsyncSession
) -> AsyncIterator[tuple[str, dict[str, Any]]]:
    problem = await get_problem(db, request.problem_id)
    if problem is None:
        yield "error", {"detail": f"Unknown problem '{request.problem_id}'"}
        return

    try:
        verifier = registry.get(problem.ncert_ref.topic)
    except KeyError as exc:
        yield "error", {"detail": str(exc)}
        return

    state = ProblemState(problem=problem, accepted_step_ids=request.accepted_step_ids)
    verify_result = verifier.verify_step(state, request.student_step)

    session_uuid = uuid.UUID(session_id)
    await log_event(
        db,
        event_type="step_submitted",
        session_id=session_uuid,
        problem_id=problem.problem_id,
        payload={
            "student_step": request.student_step.model_dump(),
            "accepted_step_ids": request.accepted_step_ids,
        },
    )
    verdict_event = await log_event(
        db,
        event_type="verdict",
        session_id=session_uuid,
        problem_id=problem.problem_id,
        step_id=verify_result.matched_step_id,
        payload=verify_result.model_dump(mode="json"),
    )
    yield "verdict", verify_result.model_dump(mode="json")

    classification = None
    correct_fields: dict[str, Any] = {}
    target_node = None

    if verify_result.is_valid:
        if verify_result.matched_step_id is not None:
            target_node = problem.node(verify_result.matched_step_id)
            correct_fields = target_node.expected_state if target_node else {}
    else:
        nearest = (
            verify_result.error_signal.nearest_matched_step_id
            if verify_result.error_signal
            else None
        )
        target_node = problem.node(nearest) if nearest else None
        if target_node is not None:
            correct_fields = target_node.expected_state
            discrepant = (
                [d.field for d in verify_result.error_signal.discrepant_fields]
                if verify_result.error_signal
                else []
            )
            classification = await classify_error(
                db,
                build_llm_client(),
                topic=problem.ncert_ref.topic,
                step_type=target_node.type,
                correct_fields=correct_fields,
                student_fields=request.student_step.fields,
                discrepant_fields=discrepant,
                event_id=verdict_event.id,
            )
            yield "classification", dataclasses.asdict(classification)

    problem_is_complete = bool(
        target_node is not None and not target_node.next and verify_result.is_valid
    )
    step_type = target_node.type if target_node is not None else request.student_step.step_type

    state_store = DialogueStateStore(get_redis())
    dialogue_result = await handle_step_submission(
        state_store=state_store,
        llm_client=build_llm_client(),
        session_id=session_id,
        problem_id=problem.problem_id,
        topic=problem.ncert_ref.topic,
        step_type=step_type,
        correct_fields=correct_fields,
        student_fields=request.student_step.fields,
        verify_result=verify_result,
        classification=classification,
        timing_policy=request.timing_policy,
        problem_is_complete=problem_is_complete,
    )

    if dialogue_result.message is not None:
        for chunk in _chunk_message(dialogue_result.message):
            yield "message_chunk", {"text": chunk}

    yield (
        "turn_complete",
        {
            "dialogue_event": dialogue_result.event,
            "turn_count": dialogue_result.turn_count,
            "expects_retry": dialogue_result.expects_retry,
            "message": dialogue_result.message,
        },
    )

    await db.commit()


@router.post("/{session_id}/steps")
async def submit_step(
    session_id: str,
    request: StepSubmissionRequest,
    db: Annotated[AsyncSession, Depends(get_session)],
) -> StreamingResponse:
    async def stream() -> AsyncIterator[str]:
        async for event_name, data in _pipeline_events(session_id, request, db):
            yield _sse_format(event_name, data)

    return StreamingResponse(stream(), media_type="text/event-stream")
