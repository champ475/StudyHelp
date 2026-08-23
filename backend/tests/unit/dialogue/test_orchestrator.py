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
from studyhelp.llm.client import (
    ClassifyRequest,
    ClassifyResponse,
    DecideRequest,
    DecideResponse,
    GenerateRequest,
    GenerateResponse,
)
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
    assert "why that works" in resolved.message.lower()
    # Reflective, not interrogative (open-ended-review Issue C: no input
    # box exists for a reply, so this must never read as a question the
    # student is expected to answer before continuing).
    assert "?" not in resolved.message


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


class _CapturingLLMClient:
    """A fake `LLMClient` (not `MockLLMProvider`, which the leakage bug
    below doesn't reproduce against — its templates never contain digits)
    that records every `GenerateRequest` it receives. Used to prove the
    orchestrator actually threads `protected_values` into the request on
    every attempt, not just the gate check — CLAUDE.md open-ended-review
    Issue A: live testing against the real Groq model found demo-example
    numbers coincidentally colliding with a problem's own small protected
    values (fractions "1/4 + 1/6", protected [3, 12, 2, 12], a "1/2 + 1/3"
    demo leaking via the bare "3"), because the model had to infer which
    numbers in `correct_step` were secret rather than being told outright."""

    def __init__(self, first_message: str, retry_message: str) -> None:
        self.first_message = first_message
        self.retry_message = retry_message
        self.generate_requests: list[GenerateRequest] = []

    async def classify(self, request: ClassifyRequest) -> ClassifyResponse:
        return ClassifyResponse(misconception_id=None, rationale="n/a")

    async def decide(self, request: DecideRequest) -> DecideResponse:
        return DecideResponse(
            error_type="procedural", remediation_strategy="x", instructional_intent="y"
        )

    async def generate(self, request: GenerateRequest) -> GenerateResponse:
        self.generate_requests.append(request)
        message = (
            self.first_message if request.regeneration_feedback is None else self.retry_message
        )
        return GenerateResponse(
            message=message, expects_retry=True, hint_level=1, concept_flag=None
        )


async def test_generate_request_carries_the_exact_gate_protected_values(
    store: DialogueStateStore,
) -> None:
    """The `GenerateRequest` sent on the very first attempt (not just after
    a rejection) must already carry the same `protected_values` list the
    leakage gate itself checks against — the model needs this to avoid a
    collision in the first place, not just after being told about one."""
    fields = {"left_num": 3, "left_den": 12, "op": "+", "right_num": 2, "right_den": 12}
    client = _CapturingLLMClient(
        first_message="This step just needs a careful look, nothing more to say here.",
        retry_message="unused",
    )
    result = await handle_step_submission(
        state_store=store,
        llm_client=client,  # type: ignore[arg-type]
        session_id="s1",
        problem_id="p1",
        topic="fractions_addition",
        step_type="rewrite_common_denominator",
        correct_fields=fields,
        student_fields={"left_num": 1, "left_den": 4, "op": "+", "right_num": 1, "right_den": 6},
        verify_result=_INVALID_RESULT,
        classification=None,
        timing_policy=InterventionPolicy.IMMEDIATE,
        problem_is_complete=False,
    )
    assert result.event == "explaining"
    assert len(client.generate_requests) == 1
    assert sorted(client.generate_requests[0].protected_values, key=str) == sorted(
        _protected_values(fields), key=str
    )


async def test_leaked_demo_number_is_rejected_and_retry_recovers(
    store: DialogueStateStore,
) -> None:
    """A draft that reuses a protected value inside an unrelated demo
    example (the exact live-confirmed failure mode) is still rejected by
    the gate — and a genuinely different retry can still succeed, rather
    than guaranteeing three rejections in a row the way a model that
    ignores `regeneration_feedback` entirely would (this is why
    `MockLLMProvider` alone can't reproduce or verify a fix for this: its
    templates never vary per attempt)."""
    fields = {"left_num": 3, "left_den": 12, "op": "+", "right_num": 2, "right_den": 12}
    client = _CapturingLLMClient(
        first_message="Think about a demo like 1/2 + 1/3 to see the idea, then try your own.",
        retry_message="Let's look at this a new way. What do you notice about your two numbers?",
    )
    result = await handle_step_submission(
        state_store=store,
        llm_client=client,  # type: ignore[arg-type]
        session_id="s1",
        problem_id="p1",
        topic="fractions_addition",
        step_type="rewrite_common_denominator",
        correct_fields=fields,
        student_fields={"left_num": 1, "left_den": 4, "op": "+", "right_num": 1, "right_den": 6},
        verify_result=_INVALID_RESULT,
        classification=None,
        timing_policy=InterventionPolicy.IMMEDIATE,
        problem_is_complete=False,
    )
    assert result.event == "explaining"
    assert result.message == client.retry_message
    assert result.message != _FALLBACK_MESSAGE
    assert len(client.generate_requests) == 2
    # The regeneration feedback on the retry names the exact protected
    # values, not just a generic "don't leak" instruction.
    assert client.generate_requests[1].regeneration_feedback is not None
    assert "3" in client.generate_requests[1].regeneration_feedback
