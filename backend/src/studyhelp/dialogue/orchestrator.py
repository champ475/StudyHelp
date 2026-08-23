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
from collections.abc import Callable
from typing import Any, Literal

from studyhelp.classification.classifier import ClassificationResult
from studyhelp.config import get_settings
from studyhelp.dialogue.leakage_filter import contains_leakage
from studyhelp.dialogue.readability_gate import flesch_kincaid_grade, passes_readability
from studyhelp.dialogue.state import (
    ConversationTurn,
    DialogueState,
    DialogueStateName,
    DialogueStateStore,
)
from studyhelp.dialogue.timing_policy import InterventionPolicy, should_intervene
from studyhelp.llm.analogies import get_analogy
from studyhelp.llm.client import (
    ClassifyCandidate,
    DecideRequest,
    DecideResponse,
    GenerateRequest,
    LLMClient,
)
from studyhelp.logging import get_logger
from studyhelp.schemas.verify import VerifyResult

logger = get_logger(__name__)

MAX_GATE_REGENERATION_ATTEMPTS = 2

REGISTER_SWITCH_REPEAT_THRESHOLD = 2
"""At this many consecutive wrong submissions on the *same step*, the
decide/generate register switches from abstract/numeric re-explanation to a
fixed, topic-appropriate concrete analogy (CLAUDE.md Bug2; `llm/analogies.py`)."""

TOPIC_REGISTER_SWITCH_THRESHOLD = 3
"""At this many times a session has been classified with the *same
misconception*, even across different problems and different steps, the
register also switches to the concrete analogy — broader than
`REGISTER_SWITCH_REPEAT_THRESHOLD`'s single-step scope, for a student who is
generally shaky on a concept rather than stuck on one specific step
(open-ended review finding #2). Set one higher than the same-step threshold:
this signal is noisier (two unrelated slips on two different problems could
otherwise trip it as fast as two genuinely-repeated attempts at one step)."""

_FALLBACK_MESSAGE = "Let's slow down and look at this step together. Take your time, and try it again when you're ready."

_CONCEPT_CHECK_FALLBACK_MESSAGE = (
    "Nice work fixing that! Take a moment to think about why that works, then let's move on "
    "to the next step."
)

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
    # The 7 light-check topics' (and `patterns`' two step types') answer
    # field: a bare word or number rather than one of the numeric keys
    # above (e.g. "acute", "Tuesday", "0" lines of symmetry). Without this,
    # the leakage filter has no protected value at all for any of these
    # step types — `_protected_values()` would silently return empty and
    # every generated message for ~a third of the syllabus would pass the
    # gate unchecked, answer stated outright or not.
    answer = correct_fields.get("answer")
    if isinstance(answer, str) and answer:
        values.append(answer)
    digits = correct_fields.get("digits")
    if isinstance(digits, dict):
        values.extend(v for v in digits.values() if isinstance(v, int))
    return values


def _humanize_worked_example_field(key: str, value: Any) -> str:
    """One short, plain-English sentence for a single `correct_fields`
    entry — used only by `_worked_example_message()`. Common field names
    shared across most topics' `step_checkers.py` models get a natural
    sentence; anything unrecognized still falls back to a plain clause so a
    new topic's field names never break this path (open-ended review
    finding #1: the old version joined every field into one dense
    "key is value, key is value" clause, which read like a debug dump, not
    a patient explanation)."""
    if key == "column":
        return f"This step is in the {value} column."
    if key == "borrow_needed":
        return "Borrowing is needed here." if value else "No borrowing is needed here."
    if key == "minuend_digit":
        return f"The top number here is {value}."
    if key == "subtrahend_digit":
        return f"The number being taken away here is {value}."
    if key == "to_digit_after":
        return f"After borrowing, this digit becomes {value}."
    if key in ("result_digit", "value", "answer"):
        return f"The result here is {value}."
    if key == "op":
        return f"The sign used here is '{value}'."
    if isinstance(value, dict):
        return " ".join(_humanize_worked_example_field(k, v) for k, v in value.items())
    label = key.replace("_", " ")
    return f"The {label} here is {value}."


def _worked_example_message(correct_fields: dict[str, Any]) -> str:
    """The one deliberate exception to the leakage filter: turn-budget
    escalation is supposed to reveal the correct step (D14). Not
    LLM-generated (no gate applies), so this stays fully deterministic —
    but it's still the child's last message on this step, so it should
    read like a patient walkthrough, not a raw field dump."""
    sentences = [
        _humanize_worked_example_field(key, value) for key, value in correct_fields.items()
    ]
    walkthrough = " ".join(sentences)
    return (
        "You've worked hard on this one, so let's finish it together, one part at a time. "
        f"{walkthrough} "
        "Now you've seen exactly how it works. Try a step like this on your own next time!"
    )


async def _run_gated_generate(
    *,
    llm_client: LLMClient,
    build_request: Callable[[str | None], GenerateRequest],
    protected_values: list[int | str],
    resolved_max_grade: float,
    session_id: str,
    problem_id: str,
) -> str | None:
    """Shared leakage/readability regeneration loop (D8/D9) behind both the
    normal explaining-turn generate() call and the post-resolution concept
    check below — same gates, same bounded-retry behavior, one place to get
    it right. Returns `None` if every attempt was rejected, letting the
    caller fall back to its own safe canned message."""
    regeneration_feedback: str | None = None
    for attempt in range(MAX_GATE_REGENERATION_ATTEMPTS + 1):
        generated = await llm_client.generate(build_request(regeneration_feedback))
        if contains_leakage(generated.message, protected_values):
            # Logging the rejected draft itself (truncated) and the exact
            # protected values it was checked against is what actually
            # makes a gate rejection debuggable after the fact — a bare
            # "rejected" line with no content proved useless when this was
            # first investigated live (CLAUDE.md open-ended-review Issue A).
            logger.warning(
                "dialogue_leakage_filter_rejected",
                session_id=session_id,
                problem_id=problem_id,
                attempt=attempt,
                protected_values=protected_values,
                rejected_message=generated.message[:300],
            )
            # Restating the exact protected values here too (on top of
            # them already being in "protected_values" on every attempt)
            # is deliberate reinforcement, not redundancy: the rejected
            # draft already had them in context and still collided —
            # usually via an unrelated demo example reusing a small
            # protected number by coincidence (confirmed live,
            # fractions_addition, CLAUDE.md open-ended-review Issue A) —
            # so the retry needs a concrete, hard-to-miss "these exact
            # ones" list, not just a repeat of the general rule.
            regeneration_feedback = (
                "Your previous draft accidentally included one of these exact protected values "
                f"somewhere in the text, possibly inside a demo example: {protected_values}. Ask "
                "a guiding question instead, and if you use a demonstration example, pick "
                "different numbers than every one of those."
            )
            continue
        if not passes_readability(generated.message, resolved_max_grade):
            logger.warning(
                "dialogue_readability_gate_rejected",
                session_id=session_id,
                problem_id=problem_id,
                attempt=attempt,
                max_grade=resolved_max_grade,
                actual_grade=flesch_kincaid_grade(generated.message),
                rejected_message=generated.message[:300],
            )
            regeneration_feedback = (
                "Your previous draft was too complex for a 10-year-old to read comfortably. "
                "Rewrite it using shorter sentences and simpler, more common words."
            )
            continue
        return generated.message
    return None


async def _generate_concept_check_message(
    *,
    llm_client: LLMClient,
    topic: str,
    correct_fields: dict[str, Any],
    student_fields: dict[str, Any],
    conversation: list[ConversationTurn],
    resolved_max_grade: float,
    session_id: str,
    problem_id: str,
) -> str:
    """One follow-up message after a student's retry resolves an error
    dialogue (open-ended review finding #3): a short, warm, REFLECTIVE
    aside about why the fix works — not a question requiring a typed reply
    (there is no input box for one; the student just proceeds to the next
    real step regardless — CLAUDE.md open-ended-review Issue C, a direct
    "why does that work?" left the student stuck looking at an
    unanswerable question) — and not another remediation turn either:
    there's no error left to diagnose, so this deliberately skips a real
    `decide()` call (decide-then-generate, D7, exists to ground remediation
    in a real error + misconception; there isn't one here) and instead
    builds the `DecideResponse` directly in application code, the same way
    `_worked_example_message()` is a deterministic non-LLM fallback for a
    different case. Still goes through `generate()` and the same
    leakage/readability gates as any other child-facing message — falls
    back to a safe canned message if every attempt is rejected, exactly
    like the main explaining path."""
    decision = DecideResponse(
        error_type="conceptual",
        remediation_strategy=(
            "The student just answered this exact step correctly after getting it wrong "
            "earlier — this is not a new mistake. Warmly acknowledge the fix in one short "
            "clause, then invite the student to think for a moment about why the corrected "
            "approach works, phrased as a reflective aside, not a question — there is no way "
            "for the student to type a reply to this, they will simply move on to the next step."
        ),
        instructional_intent=(
            "Help the student articulate why their now-correct step works, to consolidate the "
            "concept rather than just the arithmetic."
        ),
    )
    protected_values = _protected_values(correct_fields)
    message = await _run_gated_generate(
        llm_client=llm_client,
        build_request=lambda feedback: GenerateRequest(
            decision=decision,
            conversation_so_far=[turn.model_dump() for turn in conversation],
            correct_step=correct_fields,
            student_step=student_fields,
            topic=topic,
            protected_values=protected_values,
            is_concept_check=True,
            regeneration_feedback=feedback,
        ),
        protected_values=protected_values,
        resolved_max_grade=resolved_max_grade,
        session_id=session_id,
        problem_id=problem_id,
    )
    if message is None:
        logger.warning(
            "concept_check_gates_exhausted_fallback_used",
            session_id=session_id,
            problem_id=problem_id,
        )
        return _CONCEPT_CHECK_FALLBACK_MESSAGE
    return message


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
            # One follow-up "why does that work?" turn before moving on
            # (open-ended review finding #3) — scoped deliberately to real
            # mid-problem error recovery only (an existing AwaitingRetry
            # dialogue to resolve), never to a submission that was correct
            # on the first try (including a clean skip-ahead to the final
            # answer, Bug3): those never had `existing` in the first place
            # and take the plain "no_action" path below untouched.
            concept_check_message = await _generate_concept_check_message(
                llm_client=llm_client,
                topic=topic,
                correct_fields=correct_fields,
                student_fields=student_fields,
                conversation=existing.conversation,
                resolved_max_grade=resolved_max_grade,
                session_id=session_id,
                problem_id=problem_id,
            )
            return DialogueTurnResult(
                event="resolved",
                state=DialogueStateName.RESOLVED,
                message=concept_check_message,
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

    # Broader-than-one-step register signal (open-ended review finding #2):
    # a session-scoped count of how many times this exact misconception has
    # now recurred, across any problem/step, not just this one. Only
    # tracked when classification actually produced an identifier — a
    # "novel"/unclassified error (no rule match, LLM said "none of these")
    # has nothing concrete to accumulate against.
    misconception_key = None
    if classification is not None:
        misconception_key = classification.misconception_id or classification.bug_code
    topic_repeat_count = (
        await state_store.increment_topic_weakness(session_id, topic, misconception_key)
        if misconception_key is not None
        else 1
    )

    analogy_hint = (
        get_analogy(topic)
        if consecutive >= REGISTER_SWITCH_REPEAT_THRESHOLD
        or topic_repeat_count >= TOPIC_REGISTER_SWITCH_THRESHOLD
        else None
    )

    decision = await llm_client.decide(
        DecideRequest(
            topic=topic,
            step_type=step_type,
            correct_step=correct_fields,
            student_step=student_fields,
            misconception=misconception_candidate,
            turn_number=turn_count,
            repeat_count=consecutive,
            analogy_hint=analogy_hint,
        )
    )

    protected_values = _protected_values(correct_fields)
    message = await _run_gated_generate(
        llm_client=llm_client,
        build_request=lambda feedback: GenerateRequest(
            decision=decision,
            conversation_so_far=[turn.model_dump() for turn in conversation],
            correct_step=correct_fields,
            student_step=student_fields,
            topic=topic,
            protected_values=protected_values,
            repeat_count=consecutive,
            analogy_hint=analogy_hint,
            regeneration_feedback=feedback,
        ),
        protected_values=protected_values,
        resolved_max_grade=resolved_max_grade,
        session_id=session_id,
        problem_id=problem_id,
    )

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
