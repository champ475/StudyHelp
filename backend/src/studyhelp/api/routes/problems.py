"""Dev/test surface for the verifier pipeline — round-trips a step through
Postgres end-to-end (DB-load -> verify_step() -> events rows) with zero LLM
involvement anywhere in the path. Not a real student-facing endpoint yet;
that's the dialogue-orchestrator-backed API built in Phase 3.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from studyhelp.db.base import get_session
from studyhelp.db.repositories.event_repository import log_event
from studyhelp.db.repositories.problem_repository import get_problem
from studyhelp.logging import get_logger
from studyhelp.schemas.verify import ProblemState, StudentStep, VerifyResult
from studyhelp.verification.interface import registry

router = APIRouter(prefix="/problems", tags=["problems"])
logger = get_logger(__name__)


class VerifyStepRequest(BaseModel):
    accepted_step_ids: list[str] = Field(default_factory=list)
    student_step: StudentStep


@router.post("/{problem_id}/verify-step", response_model=VerifyResult)
async def verify_step(
    problem_id: str,
    request: VerifyStepRequest,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> VerifyResult:
    problem = await get_problem(session, problem_id)
    if problem is None:
        raise HTTPException(status_code=404, detail=f"Unknown problem '{problem_id}'")

    try:
        verifier = registry.get(problem.ncert_ref.topic)
    except KeyError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    logger.info(
        "step_submitted",
        problem_id=problem_id,
        step_type=request.student_step.step_type,
        accepted_step_ids=request.accepted_step_ids,
    )
    await log_event(
        session,
        event_type="step_submitted",
        problem_id=problem_id,
        payload={
            "student_step": request.student_step.model_dump(),
            "accepted_step_ids": request.accepted_step_ids,
        },
    )

    state = ProblemState(problem=problem, accepted_step_ids=request.accepted_step_ids)
    result = verifier.verify_step(state, request.student_step)

    logger.info(
        "verdict",
        problem_id=problem_id,
        is_valid=result.is_valid,
        matched_step_id=result.matched_step_id,
        confidence=result.confidence,
    )
    await log_event(
        session,
        event_type="verdict",
        problem_id=problem_id,
        step_id=result.matched_step_id,
        payload=result.model_dump(mode="json"),
    )

    await session.commit()
    return result
