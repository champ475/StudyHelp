"""Core state-machine coverage for the dialogue orchestrator, backed by
fakeredis (no real Redis server needed) and the mock LLM provider.
Confirms: turn budget + graceful escalation, the intervention-timing
policy gate, resolution on a correct retry, consecutive-error tracking
(and its reset when the student's mistake moves to a different step), and
that the leakage/readability gates actually reject a bad draft and fall
back to a safe canned message rather than ever returning it.
"""

import fakeredis
import pytest

from studyhelp.classification.classifier import ClassificationResult
from studyhelp.dialogue.orchestrator import (
    _FALLBACK_MESSAGE,
    DialogueTurnResult,
    _protected_values,
    handle_step_submission,
)
from studyhelp.dialogue.state import DialogueStateStore
from studyhelp.dialogue.timing_policy import InterventionPolicy
from studyhelp.llm.client import GenerateResponse
from studyhelp.llm.providers.mock import MockLLMProvider
from studyhelp.schemas.verify import ErrorSignal, VerifyResult

_CORRECT_FIELDS = {"column": "units", "minuend_digit": 12, "subtrahend_digit": 5, "result_digit": 7}
_WRONG_FIELDS = {"column": "units", "minuend_digit": 12, "subtrahend_digit": 5, "result_digit": 3}

_INVALID_RESULT = VerifyResult(
    is_valid=False,
    matched_step_id=None,
    confidence=0.75,
    error_signal=ErrorSignal(kind="field_mismatch", nearest_matched_step_id="s3_sub_units"),
)
_VALID_RESULT = VerifyResult(is_valid=True, matched_step_id="s3_sub_units", confidence=1.0)


@pytest.fixture
def store() -> DialogueStateStore:
    return DialogueStateStore(fakeredis.FakeAsyncRedis(decode_responses=True))


async def test_correct_step_with_no_active_dialogue_is_a_no_op(store: DialogueStateStore) -> None:
    result = await handle_step_submission(
        state_store=store,
        llm_client=MockLLMProvider(),
        session_id="s1",
        problem_id="p1",
        topic="subtraction_with_borrowing",
        step_type="subtract_column",
        correct_fields=_CORRECT_FIELDS,
        student_fields=_CORRECT_FIELDS,
        verify_result=_VALID_RESULT,
        classification=None,
        timing_policy=InterventionPolicy.IMMEDIATE,
        problem_is_complete=False,
    )
    assert result.event == "no_action"


async def test_immediate_policy_intervenes_on_first_wrong_step(store: DialogueStateStore) -> None:
    result = await handle_step_submission(
        state_store=store,
        llm_client=MockLLMProvider(),
        session_id="s1",
        problem_id="p1",
        topic="subtraction_with_borrowing",
        step_type="subtract_column",
        correct_fields=_CORRECT_FIELDS,
        student_fields=_WRONG_FIELDS,
        verify_result=_INVALID_RESULT,
        classification=None,
        timing_policy=InterventionPolicy.IMMEDIATE,
        problem_is_complete=False,
    )
    assert result.event == "explaining"
    assert result.turn_count == 1
    assert result.expects_retry is True
    assert result.message is not None

    saved = await store.get("s1", "p1")
    assert saved is not None
    assert saved.turn_count == 1
    assert len(saved.conversation) == 1


async def test_after_nth_repeat_policy_waits_for_the_second_wrong_attempt(
    store: DialogueStateStore,
) -> None:
    first = await handle_step_submission(
        state_store=store,
        llm_client=MockLLMProvider(),
        session_id="s1",
        problem_id="p1",
        topic="subtraction_with_borrowing",
        step_type="subtract_column",
        correct_fields=_CORRECT_FIELDS,
        student_fields=_WRONG_FIELDS,
        verify_result=_INVALID_RESULT,
        classification=None,
        timing_policy=InterventionPolicy.AFTER_NTH_REPEAT,
        problem_is_complete=False,
    )
    assert first.event == "no_action"
    tracked = await store.get("s1", "p1")
    assert (
        tracked is not None
    )  # consecutive-error count tracked even though no dialogue started yet
    assert tracked.consecutive_errors_on_this_step == 1
    assert tracked.conversation == []  # never shown to the child

    second = await handle_step_submission(
        state_store=store,
        llm_client=MockLLMProvider(),
        session_id="s1",
        problem_id="p1",
        topic="subtraction_with_borrowing",
        step_type="subtract_column",
        correct_fields=_CORRECT_FIELDS,
        student_fields=_WRONG_FIELDS,
        verify_result=_INVALID_RESULT,
        classification=None,
        timing_policy=InterventionPolicy.AFTER_NTH_REPEAT,
        problem_is_complete=False,
    )
    assert second.event == "explaining"


async def test_correct_retry_after_dialogue_resolves_and_clears_state(
    store: DialogueStateStore,
) -> None:
    await handle_step_submission(
        state_store=store,
        llm_client=MockLLMProvider(),
        session_id="s1",
        problem_id="p1",
        topic="subtraction_with_borrowing",
        step_type="subtract_column",
        correct_fields=_CORRECT_FIELDS,
        student_fields=_WRONG_FIELDS,
        verify_result=_INVALID_RESULT,
        classification=None,
        timing_policy=InterventionPolicy.IMMEDIATE,
        problem_is_complete=False,
    )
    assert await store.get("s1", "p1") is not None

    resolved = await handle_step_submission(
        state_store=store,
        llm_client=MockLLMProvider(),
        session_id="s1",
        problem_id="p1",
        topic="subtraction_with_borrowing",
        step_type="subtract_column",
        correct_fields=_CORRECT_FIELDS,
        student_fields=_CORRECT_FIELDS,
        verify_result=_VALID_RESULT,
        classification=None,
        timing_policy=InterventionPolicy.IMMEDIATE,
        problem_is_complete=False,
    )
    assert resolved.event == "resolved"
    assert await store.get("s1", "p1") is None


async def test_resolved_dialogue_includes_a_post_correct_concept_check_message(
    store: DialogueStateStore,
) -> None:
    """Open-ended review finding #3: fixing an error shouldn't just silently
    advance — one follow-up "why does that work?" message should accompany
    the resolution, gated through the same generate() leakage/readability
    pipeline as any other message (`is_concept_check=True`)."""
    await handle_step_submission(
        state_store=store,
        llm_client=MockLLMProvider(),
        session_id="s1",
        problem_id="p1",
        topic="subtraction_with_borrowing",
        step_type="subtract_column",
        correct_fields=_CORRECT_FIELDS,
        student_fields=_WRONG_FIELDS,
        verify_result=_INVALID_RESULT,
        classification=None,
        timing_policy=InterventionPolicy.IMMEDIATE,
        problem_is_complete=False,
    )
    resolved = await handle_step_submission(
        state_store=store,
        llm_client=MockLLMProvider(),
        session_id="s1",
        problem_id="p1",
        topic="subtraction_with_borrowing",
        step_type="subtract_column",
        correct_fields=_CORRECT_FIELDS,
        student_fields=_CORRECT_FIELDS,
        verify_result=_VALID_RESULT,
        classification=None,
        timing_policy=InterventionPolicy.IMMEDIATE,
        problem_is_complete=False,
    )
    assert resolved.event == "resolved"
    assert resolved.expects_retry is False
    assert resolved.message is not None
    assert "why do you think that works" in resolved.message.lower()


async def test_clean_first_try_correct_answer_has_no_concept_check_message(
    store: DialogueStateStore,
) -> None:
    """Bug3 scoping: a submission that was correct on the first try (no
    prior error dialogue for this problem — including a clean skip-ahead
    to the final answer) must take the plain no-op path, with no
    concept-check message and no extra LLM call."""
    result = await handle_step_submission(
        state_store=store,
        llm_client=MockLLMProvider(),
        session_id="s1",
        problem_id="p1",
        topic="subtraction_with_borrowing",
        step_type="subtract_column",
        correct_fields=_CORRECT_FIELDS,
        student_fields=_CORRECT_FIELDS,
        verify_result=_VALID_RESULT,
        classification=None,
        timing_policy=InterventionPolicy.IMMEDIATE,
        problem_is_complete=True,
    )
    assert result.event == "no_action"
    assert result.message is None


async def test_topic_weakness_across_different_steps_and_problems_triggers_analogy_switch(
    store: DialogueStateStore,
) -> None:
    """Open-ended review finding #2 regression: the SAME misconception
    recurring across DIFFERENT steps and DIFFERENT problems — never twice
    in a row on any single step, so `REGISTER_SWITCH_REPEAT_THRESHOLD`
    never fires — must still eventually switch the register once
    `TOPIC_REGISTER_SWITCH_THRESHOLD` is reached."""
    classification = ClassificationResult(
        source="rule",
        misconception_id="subtraction_borrowing.smaller_from_larger",
        bug_code="B1-smaller-from-larger",
        confidence="high",
    )
    last_result: DialogueTurnResult | None = None
    for index, step_id in enumerate(["s3_sub_units", "s4_sub_tens", "s5_sub_hundreds"]):
        wrong_result = VerifyResult(
            is_valid=False,
            matched_step_id=None,
            confidence=0.75,
            error_signal=ErrorSignal(kind="field_mismatch", nearest_matched_step_id=step_id),
        )
        last_result = await handle_step_submission(
            state_store=store,
            llm_client=MockLLMProvider(),
            session_id="s-topic-weak",
            problem_id=f"p{index}",
            topic="subtraction_with_borrowing",
            step_type="subtract_column",
            correct_fields=_CORRECT_FIELDS,
            student_fields=_WRONG_FIELDS,
            verify_result=wrong_result,
            classification=classification,
            timing_policy=InterventionPolicy.IMMEDIATE,
            problem_is_complete=False,
        )
        assert last_result.event == "explaining"
        if index < 2:
            # Different step every time -> the same-step counter never
            # reaches its own threshold on its own.
            assert "trading" not in last_result.message.lower()

    assert last_result is not None
    assert last_result.message is not None
    assert "trading" in last_result.message.lower()  # subtraction's analogy, switched in


async def test_topic_weakness_not_tracked_for_unclassified_novel_errors(
    store: DialogueStateStore,
) -> None:
    """An error with no rule/misconception identifier at all (`source`
    "novel", both ids `None`) has nothing concrete to accumulate against —
    repeating it many times on different steps must not trip the
    topic-broadened switch."""
    novel = ClassificationResult(
        source="novel", misconception_id=None, bug_code=None, confidence="low"
    )
    last_result: DialogueTurnResult | None = None
    for index, step_id in enumerate(["s3", "s4", "s5", "s6"]):
        wrong_result = VerifyResult(
            is_valid=False,
            matched_step_id=None,
            confidence=0.75,
            error_signal=ErrorSignal(kind="field_mismatch", nearest_matched_step_id=step_id),
        )
        last_result = await handle_step_submission(
            state_store=store,
            llm_client=MockLLMProvider(),
            session_id="s-novel-weak",
            problem_id=f"p{index}",
            topic="subtraction_with_borrowing",
            step_type="subtract_column",
            correct_fields=_CORRECT_FIELDS,
            student_fields=_WRONG_FIELDS,
            verify_result=wrong_result,
            classification=novel,
            timing_policy=InterventionPolicy.IMMEDIATE,
            problem_is_complete=False,
        )
    assert last_result is not None
    assert last_result.message is not None
    assert "trading" not in last_result.message.lower()


async def test_turn_budget_exhausted_escalates_with_worked_example(
    store: DialogueStateStore,
) -> None:
    # turn_budget=1: the first wrong submission is turn 1 (<=1, still
    # explains); the second consecutive wrong submission is turn 2 (>1,
    # escalates).
    await handle_step_submission(
        state_store=store,
        llm_client=MockLLMProvider(),
        session_id="s1",
        problem_id="p1",
        topic="subtraction_with_borrowing",
        step_type="subtract_column",
        correct_fields=_CORRECT_FIELDS,
        student_fields=_WRONG_FIELDS,
        verify_result=_INVALID_RESULT,
        classification=None,
        timing_policy=InterventionPolicy.IMMEDIATE,
        problem_is_complete=False,
        turn_budget=1,
    )
    escalated = await handle_step_submission(
        state_store=store,
        llm_client=MockLLMProvider(),
        session_id="s1",
        problem_id="p1",
        topic="subtraction_with_borrowing",
        step_type="subtract_column",
        correct_fields=_CORRECT_FIELDS,
        student_fields=_WRONG_FIELDS,
        verify_result=_INVALID_RESULT,
        classification=None,
        timing_policy=InterventionPolicy.IMMEDIATE,
        problem_is_complete=False,
        turn_budget=1,
    )
    assert escalated.event == "escalated"
    assert escalated.expects_retry is False
    assert escalated.message is not None
    assert (
        "result here is 7" in escalated.message
    )  # the worked example reveals the answer, by design
    assert "You've worked hard" in escalated.message  # warm framing, not a raw field dump
    assert await store.get("s1", "p1") is None  # cleared, not left dangling


async def test_consecutive_error_count_resets_on_a_different_step(
    store: DialogueStateStore,
) -> None:
    error_on_units = VerifyResult(
        is_valid=False,
        matched_step_id=None,
        confidence=0.8,
        error_signal=ErrorSignal(kind="field_mismatch", nearest_matched_step_id="s3_sub_units"),
    )
    error_on_tens = VerifyResult(
        is_valid=False,
        matched_step_id=None,
        confidence=0.8,
        error_signal=ErrorSignal(kind="field_mismatch", nearest_matched_step_id="s6_sub_tens"),
    )

    await handle_step_submission(
        state_store=store,
        llm_client=MockLLMProvider(),
        session_id="s1",
        problem_id="p1",
        topic="t",
        step_type="subtract_column",
        correct_fields=_CORRECT_FIELDS,
        student_fields=_WRONG_FIELDS,
        verify_result=error_on_units,
        classification=None,
        timing_policy=InterventionPolicy.IMMEDIATE,
        problem_is_complete=False,
    )
    second = await handle_step_submission(
        state_store=store,
        llm_client=MockLLMProvider(),
        session_id="s1",
        problem_id="p1",
        topic="t",
        step_type="subtract_column",
        correct_fields=_CORRECT_FIELDS,
        student_fields=_WRONG_FIELDS,
        verify_result=error_on_tens,  # a *different* step this time
        classification=None,
        timing_policy=InterventionPolicy.IMMEDIATE,
        problem_is_complete=False,
    )
    saved = await store.get("s1", "p1")
    assert saved is not None
    assert saved.consecutive_errors_on_this_step == 1  # reset, not 2
    assert second.event == "explaining"


async def test_gate_rejection_falls_back_to_safe_message(store: DialogueStateStore) -> None:
    leaky_response = GenerateResponse(
        message="The answer is 7.", expects_retry=True, hint_level=1, concept_flag=None
    )
    result = await handle_step_submission(
        state_store=store,
        llm_client=MockLLMProvider(generate_override=leaky_response),
        session_id="s1",
        problem_id="p1",
        topic="subtraction_with_borrowing",
        step_type="subtract_column",
        correct_fields=_CORRECT_FIELDS,
        student_fields=_WRONG_FIELDS,
        verify_result=_INVALID_RESULT,
        classification=None,
        timing_policy=InterventionPolicy.IMMEDIATE,
        problem_is_complete=False,
    )
    assert result.message == _FALLBACK_MESSAGE
    assert result.message != leaky_response.message


async def test_misconception_from_classification_reaches_the_decide_call(
    store: DialogueStateStore,
) -> None:
    classification = ClassificationResult(
        source="rule",
        misconception_id="subtraction_borrowing.smaller_from_larger",
        bug_code="B1-smaller-from-larger",
        confidence="high",
    )
    await handle_step_submission(
        state_store=store,
        llm_client=MockLLMProvider(),
        session_id="s1",
        problem_id="p1",
        topic="subtraction_with_borrowing",
        step_type="subtract_column",
        correct_fields=_CORRECT_FIELDS,
        student_fields=_WRONG_FIELDS,
        verify_result=_INVALID_RESULT,
        classification=classification,
        timing_policy=InterventionPolicy.IMMEDIATE,
        problem_is_complete=False,
    )
    saved = await store.get("s1", "p1")
    assert saved is not None
    assert saved.misconception_id == "subtraction_borrowing.smaller_from_larger"
    assert saved.bug_code == "B1-smaller-from-larger"


async def test_repeated_error_on_same_step_switches_to_concrete_analogy(
    store: DialogueStateStore,
) -> None:
    """Bug2 regression: getting the *same* step wrong a second time in a
    row must switch the tutor's register to the topic's fixed concrete
    analogy (`llm/analogies.py`, `REGISTER_SWITCH_REPEAT_THRESHOLD`), not
    just repeat another abstract/numeric nudge."""
    first = await handle_step_submission(
        state_store=store,
        llm_client=MockLLMProvider(),
        session_id="s1",
        problem_id="p1",
        topic="subtraction_with_borrowing",
        step_type="subtract_column",
        correct_fields=_CORRECT_FIELDS,
        student_fields=_WRONG_FIELDS,
        verify_result=_INVALID_RESULT,
        classification=None,
        timing_policy=InterventionPolicy.IMMEDIATE,
        problem_is_complete=False,
    )
    assert first.message is not None
    assert "trading" not in first.message.lower()

    second = await handle_step_submission(
        state_store=store,
        llm_client=MockLLMProvider(),
        session_id="s1",
        problem_id="p1",
        topic="subtraction_with_borrowing",
        step_type="subtract_column",
        correct_fields=_CORRECT_FIELDS,
        student_fields=_WRONG_FIELDS,
        verify_result=_INVALID_RESULT,
        classification=None,
        timing_policy=InterventionPolicy.IMMEDIATE,
        problem_is_complete=False,
    )
    assert second.event == "explaining"
    assert second.message is not None
    assert "trading" in second.message.lower()  # subtraction's analogy: trading coins


def test_protected_values_covers_light_check_word_answers() -> None:
    """The 7 light-check topics' (and `patterns`' two step types')
    `expected_state` is `{"answer": <word or number>}` — none of the
    numeric-keyed fields `_protected_values` otherwise looks for. Without
    explicit "answer" handling, this returns `[]` and the leakage filter
    has nothing to check a generated message against for ~a third of the
    syllabus."""
    assert _protected_values({"answer": "acute"}) == ["acute"]
    assert _protected_values({"answer": "0"}) == ["0"]
    assert _protected_values({}) == []
