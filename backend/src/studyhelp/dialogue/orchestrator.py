"""Multi-turn Socratic dialogue orchestrator (technical_architecture.md
§6). Every turn is decide-then-generate (D7): a structured decision object
is produced first, grounded in the verifier's output and the retrieved
misconception, and only then is the child-facing message generated,
conditioned on that decision — never straight from error to message.
Every generated message must clear the leakage filter and readability
gate before it's ever returned to the caller (D8, D9), with a bounded
number of regeneration attempts before falling back to a safe canned
message. Turn budget caps dialogue length with a graceful worked-example
fallback (D14). Re-verification on every retry (D15) happens one layer up
— the caller re-runs `verify_step()` before calling this function again;
this module never re-judges correctness itself.
"""

import dataclasses
from typing import Any, Literal

from studyhelp.classification.classifier import ClassificationResult
from studyhelp.config import get_settings
from studyhelp.dialogue.leakage_filter import contains_leakage
from studyhelp.dialogue.readability_gate import passes_readability
from studyhelp.dialogue.state import (
    ConversationTurn,
    DialogueState,
    DialogueStateName,
    DialogueStateStore,
)
from studyhelp.dialogue.timing_policy import InterventionPolicy, should_intervene
from studyhelp.llm.client import ClassifyCandidate, DecideRequest, GenerateRequest, LLMClient
from studyhelp.logging import get_logger
from studyhelp.schemas.verify import VerifyResult

logger = get_logger(__name__)

MAX_GATE_REGENERATION_ATTEMPTS = 2

_FALLBACK_MESSAGE = "Let's slow down and look at this step together. Take your time, and try it again when you're ready."

DialogueEvent = Literal["no_action", "resolved", "explaining", "escalated"]


@dataclasses.dataclass(frozen=True)
class DialogueTurnResult:
    event: DialogueEvent
    state: DialogueStateName | None
    message: str | None
    turn_count: int
    expects_retry: bool


def _protected_values(correct_fields: dict[str, Any]) -> list[int | str]:
    """Which fields constitute "the answer" depends on the step's own
    shape: `result_digit`/`value`/`to_digit_after` are output-defining;
    input digits (already visible to the student on the widget) aren't
    secret. Topic-agnostic by construction — no field name here is
    specific to a step *type* the way `verification/topics/...` is.
    `op` is the one non-numeric answer (fractions' `compare_fractions`
    step: "<"/">"/"=" is literally the answer to a comparison problem)."""
    values: list[int | str] = []
    for key in (
        "result_digit",
        "value",
        "to_digit_after",
        "num",
        "den",
        "left_num",
        "left_den",
        "right_num",
        "right_den",
    ):
        value = correct_fields.get(key)
        if isinstance(value, int):
            values.append(value)
    op = correct_fields.get("op")
    if isinstance(op, str) and op in ("<", ">", "="):
        values.append(op)
    digits = correct_fields.get("digits")
    if isinstance(digits, dict):
        values.extend(v for v in digits.values() if isinstance(v, int))
    return values


def _worked_example_message(correct_fields: dict[str, Any]) -> str:
    """The one deliberate exception to the leakage filter: turn-budget
    escalation is supposed to reveal the correct step (D14)."""
    details = ", ".join(
        f"{key.replace('_', ' ')} is {value}" for key, value in correct_fields.items()
    )
    return (
        f"Let's work through this step together so you can see exactly how it's done: {details}. "
        "Next time, try this same idea on your own!"
    )


async def handle_step_submission(
    *,
    state_store: DialogueStateStore,
    llm_client: LLMClient,
    session_id: str,
    problem_id: str,
    topic: str,
    step_type: str,
    correct_fields: dict[str, Any],
    student_fields: dict[str, Any],
    verify_result: VerifyResult,
    classification: ClassificationResult | None,
    timing_policy: InterventionPolicy,
    problem_is_complete: bool,
    readability_max_grade: float | None = None,
    turn_budget: int | None = None,
) -> DialogueTurnResult:
    settings = get_settings()
    resolved_max_grade = (
        readability_max_grade
        if readability_max_grade is not None
        else settings.readability_max_grade
    )
    resolved_turn_budget = turn_budget if turn_budget is not None else settings.dialogue_turn_budget

    existing = await state_store.get(session_id, problem_id)

    if verify_result.is_valid:
        was_awaiting_retry = (
            existing is not None and existing.state == DialogueStateName.AWAITING_RETRY
        )
        if existing is not None:
            # Clears both a resolved AwaitingRetry dialogue and any
            # not-yet-escalated ErrorDetected tracking record (below) —
            # either way, a correct step means there's nothing pending.
            await state_store.delete(session_id, problem_id)
        if was_awaiting_retry:
            assert existing is not None
            return DialogueTurnResult(
                event="resolved",
                state=DialogueStateName.RESOLVED,
                message=None,
                turn_count=existing.turn_count,
                expects_retry=False,
            )
        return DialogueTurnResult(
            event="no_action", state=None, message=None, turn_count=0, expects_retry=False
        )

    error_signal = verify_result.error_signal
    nearest = error_signal.nearest_matched_step_id if error_signal else None

    consecutive = (
        existing.consecutive_errors_on_this_step + 1
        if existing is not None and existing.nearest_matched_step_id == nearest
        else 1
    )

    if not should_intervene(
        timing_policy,
        consecutive_errors_on_this_step=consecutive,
        problem_is_complete=problem_is_complete,
    ):
        # Not intervening yet, but the consecutive-error count on this
        # specific step still needs to persist across calls, or a
        # threshold-based policy (AFTER_NTH_REPEAT) could never reach its
        # threshold — every call would see a fresh, empty state and reset
        # to 1. ErrorDetected here is a tracking-only record, never shown
        # to the child (no conversation, turn_count stays 0).
        await state_store.save(
            DialogueState(
                session_id=session_id,
                problem_id=problem_id,
                state=DialogueStateName.ERROR_DETECTED,
                turn_count=0,
                consecutive_errors_on_this_step=consecutive,
                nearest_matched_step_id=nearest,
            )
        )
        return DialogueTurnResult(
            event="no_action", state=None, message=None, turn_count=0, expects_retry=False
        )

    turn_count = (existing.turn_count if existing is not None else 0) + 1

    if turn_count > resolved_turn_budget:
        await state_store.delete(session_id, problem_id)
        logger.info(
            "dialogue_escalated",
            session_id=session_id,
            problem_id=problem_id,
            turn_count=turn_count,
        )
        return DialogueTurnResult(
            event="escalated",
            state=DialogueStateName.ESCALATED,
            message=_worked_example_message(correct_fields),
            turn_count=turn_count,
            expects_retry=False,
        )

    misconception_candidate = None
    if classification is not None and classification.misconception_id is not None:
        misconception_candidate = ClassifyCandidate(
            misconception_id=classification.misconception_id,
            typical_mindset=classification.rationale or "",
        )

    conversation = existing.conversation if existing is not None else []

    decision = await llm_client.decide(
        DecideRequest(
            topic=topic,
            step_type=step_type,
            correct_step=correct_fields,
            student_step=student_fields,
            misconception=misconception_candidate,
            turn_number=turn_count,
        )
    )

    protected_values = _protected_values(correct_fields)
    message: str | None = None
    for attempt in range(MAX_GATE_REGENERATION_ATTEMPTS + 1):
        generated = await llm_client.generate(
            GenerateRequest(
                decision=decision,
                conversation_so_far=[turn.model_dump() for turn in conversation],
                correct_step=correct_fields,
                student_step=student_fields,
            )
        )
        if contains_leakage(generated.message, protected_values):
            logger.warning(
                "dialogue_leakage_filter_rejected",
                session_id=session_id,
                problem_id=problem_id,
                attempt=attempt,
            )
            continue
        if not passes_readability(generated.message, resolved_max_grade):
            logger.warning(
                "dialogue_readability_gate_rejected",
                session_id=session_id,
                problem_id=problem_id,
                attempt=attempt,
            )
            continue
        message = generated.message
        break

    if message is None:
        message = _FALLBACK_MESSAGE
        logger.warning(
            "dialogue_gates_exhausted_fallback_used", session_id=session_id, problem_id=problem_id
        )

    new_conversation = [*conversation, ConversationTurn(role="tutor", text=message)]
    new_state = DialogueState(
        session_id=session_id,
        problem_id=problem_id,
        state=DialogueStateName.AWAITING_RETRY,
        turn_count=turn_count,
        consecutive_errors_on_this_step=consecutive,
        nearest_matched_step_id=nearest,
        misconception_id=classification.misconception_id if classification else None,
        bug_code=classification.bug_code if classification else None,
        conversation=new_conversation,
    )
    await state_store.save(new_state)

    return DialogueTurnResult(
        event="explaining",
        state=DialogueStateName.AWAITING_RETRY,
        message=message,
        turn_count=turn_count,
        expects_retry=True,
    )
