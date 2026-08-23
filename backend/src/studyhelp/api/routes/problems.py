"""Dev/test surface for the verifier pipeline — round-trips a step through
Postgres end-to-end (DB-load -> verify_step() -> events rows) with zero LLM
involvement anywhere in the path. Not a real student-facing endpoint yet;
that's the dialogue-orchestrator-backed API built in Phase 3.
"""

from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from studyhelp.db.base import get_session
from studyhelp.db.models import StepType as StepTypeRow
from studyhelp.db.repositories.event_repository import log_event
from studyhelp.db.repositories.problem_repository import get_problem, list_problems
from studyhelp.logging import get_logger
from studyhelp.protected_fields import PROTECTED_INT_KEYS, PROTECTED_STR_VALUES_BY_KEY
from studyhelp.schemas.step_schema import AltPath, NcertRef, Problem
from studyhelp.schemas.verify import ProblemState, StudentStep, VerifyResult
from studyhelp.verification.interface import registry

router = APIRouter(prefix="/problems", tags=["problems"])
logger = get_logger(__name__)


class ProblemSummaryOut(BaseModel):
    """One row of the catalog list -- deliberately thin (no step graph, no
    `given`) so browsing 140 problems doesn't pull the full DAG for each."""

    problem_id: str
    ncert_ref: NcertRef
    display_label: str


@router.get("", response_model=list[ProblemSummaryOut])
async def list_problems_public(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> list[ProblemSummaryOut]:
    summaries = await list_problems(session)
    return [
        ProblemSummaryOut(
            problem_id=s.problem_id, ncert_ref=s.ncert_ref, display_label=s.display_label
        )
        for s in summaries
    ]


class PublicStepNode(BaseModel):
    """Deliberately omits `expected_state` — a raw `Problem` includes every
    step's correct values, and this endpoint is reachable from the
    browser. Exposing it would let a student read every answer straight
    out of devtools, directly undermining the leakage filter's whole
    purpose (D8). The frontend only needs step *types* and the DAG shape
    to know which widget to render next; it must never see expected
    values ahead of the student submitting a guess.

    `hint` is the step type's `step_types.description` (seed-authored,
    topic-agnostic) -- what makes the universal `FreeTextStepper` (D43)
    able to show a meaningful placeholder/label for *any* topic's step
    without the frontend knowing anything about that topic."""

    step_id: str
    type: str
    next: list[str]
    hint: str


class PublicProblem(BaseModel):
    problem_id: str
    ncert_ref: NcertRef
    display_label: str
    given: dict[str, Any]
    step_graph: list[PublicStepNode]
    alt_paths: list[AltPath]


def _public_given(problem: Problem) -> dict[str, Any]:
    """Redacts any `Problem.given` key whose value is ALSO answer-bearing,
    before `given` ever reaches this browser-reachable endpoint.

    Found live (CLAUDE.md full-system audit, same session as Bug D):
    `measurement`'s `given` dict includes `direction`/`factor`, which are
    *also* the exact `expected_state` of that problem's first step
    (`identify_conversion_factor`) — every measurement problem shipped the
    answer to its own first step in this endpoint's plain JSON response,
    readable straight out of the browser's network tab on page load, no
    LLM or dialogue turn involved at all.

    Can't simply drop every key named in `PROTECTED_INT_KEYS` wholesale —
    `given.value` (e.g. "3" in "3 km to m") is legitimate, non-secret input
    under the SAME key name that means "the answer" inside a step's
    `expected_state` (e.g. `write_final_answer`'s `value: 3000`); blanket
    key-name redaction would silently strip real, needed input. Instead,
    redact a `given` key only when it's a `PROTECTED_INT_KEYS`/
    `PROTECTED_STR_VALUES_BY_KEY` field AND its value is IDENTICAL to that
    same key's value in some step's own `expected_state` elsewhere in this
    problem — a provable duplicate of a real answer, not a coincidentally
    reused key name."""
    protected_pairs: set[tuple[str, object]] = set()
    for node in problem.step_graph:
        for key, value in node.expected_state.items():
            if (key in PROTECTED_INT_KEYS and isinstance(value, int)) or (
                key in PROTECTED_STR_VALUES_BY_KEY
                and isinstance(value, str)
                and value in PROTECTED_STR_VALUES_BY_KEY[key]
            ):
                protected_pairs.add((key, value))
    return {
        key: value
        for key, value in problem.given.items()
        if (key, value) not in protected_pairs
    }


async def _step_type_hints(session: AsyncSession, topic: str) -> dict[str, str]:
    stmt = select(StepTypeRow.step_type_key, StepTypeRow.description).where(
        StepTypeRow.topic == topic
    )
    rows = (await session.execute(stmt)).all()
    return {key: description for key, description in rows}


@router.get("/{problem_id}", response_model=PublicProblem)
async def get_problem_public(
    problem_id: str, session: Annotated[AsyncSession, Depends(get_session)]
) -> PublicProblem:
    problem = await get_problem(session, problem_id)
    if problem is None:
        raise HTTPException(status_code=404, detail=f"Unknown problem '{problem_id}'")
    hints = await _step_type_hints(session, problem.ncert_ref.topic)
    return PublicProblem(
        problem_id=problem.problem_id,
        ncert_ref=problem.ncert_ref,
        display_label=problem.display_label,
        given=_public_given(problem),
        step_graph=[
            PublicStepNode(
                step_id=node.step_id,
                type=node.type,
                next=node.next,
                hint=hints.get(node.type, ""),
            )
            for node in problem.step_graph
        ],
        alt_paths=problem.alt_paths,
    )


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
