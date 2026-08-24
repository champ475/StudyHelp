"""Dialogue-layer sweep across every seeded problem in all 14 topics —
complements `verification/test_skip_ahead_to_final_answer_all_topics.py`'s
verifier-layer sweep. Directly requested: "test all the questions given,
and not hardcode for any specific question."

For each problem's first step, submits a deliberately wrong answer and runs
it through the real orchestrator (`handle_step_submission`) against the
deterministic `MockLLMProvider` (fast, free, no live-API dependency — a
live-Groq spot-check for Bug D's exact scenario already exists in
`test_orchestrator.py`/was confirmed manually per CHANGELOG.md). Two things
this sweep catches that per-topic unit tests (which use 1-2 hand-picked
fixtures) wouldn't: (1) the leakage/readability gates never exhausting all
regeneration attempts and falling back to the generic canned message for
ANY of the 140 problems' first step — every previously-found gate-rejection
bug (Issue A, Bug D's `protected_values: []` gap) would have shown up here
as a `_FALLBACK_MESSAGE`; (2) for the 3 mixed-operation topics
(area_perimeter, multiplication_division, lcm_hcf), that the repeat-attempt
analogy never drifts to the WRONG operation's forbidden words, across every
seeded problem in those topics, not just the one Bug D happened to report.
"""

import json
from pathlib import Path
from typing import Any

import fakeredis
import pytest

from studyhelp.dialogue.orchestrator import _FALLBACK_MESSAGE, handle_step_submission
from studyhelp.dialogue.state import DialogueStateStore
from studyhelp.dialogue.timing_policy import InterventionPolicy
from studyhelp.llm.providers.mock import MockLLMProvider
from studyhelp.schemas.step_schema import Problem
from studyhelp.schemas.verify import ErrorSignal, VerifyResult

FIXTURES_ROOT = (
    Path(__file__).parents[3] / "src" / "studyhelp" / "seed" / "fixtures" / "problems"
)

_ALL_TOPIC_DIRS: list[tuple[str, str]] = [
    ("subtraction_with_borrowing", "ch1_subtraction_borrowing"),
    ("fractions_addition", "ch_fractions"),
    ("lcm_hcf", "ch6_lcm_hcf"),
    ("decimals", "ch10_decimals"),
    ("area_perimeter", "ch11_area_perimeter"),
    ("multiplication_division", "ch13_multiplication_division"),
    ("measurement", "ch14_measurement"),
    ("shapes_angles", "ch2_shapes_angles"),
    ("how_many_squares", "ch3_how_many_squares"),
    ("symmetry", "ch5_symmetry"),
    ("patterns", "ch7_patterns"),
    ("mapping", "ch8_mapping"),
    ("boxes_sketches", "ch9_boxes_sketches"),
    ("smart_charts", "ch12_smart_charts"),
]

def _load_fixtures(dirname: str) -> list[Problem]:
    fixtures_dir = FIXTURES_ROOT / dirname
    return [
        Problem.model_validate(json.loads(path.read_text(encoding="utf-8")))
        for path in sorted(fixtures_dir.glob("*.json"))
    ]


def _all_problem_cases() -> list[tuple[str, Problem]]:
    cases = []
    for topic, dirname in _ALL_TOPIC_DIRS:
        for problem in _load_fixtures(dirname):
            cases.append((topic, problem))
    return cases


def _wrong_student_fields(correct_fields: dict[str, Any]) -> dict[str, Any]:
    """Deliberately wrong version of the first node's `expected_state` —
    good enough for exercising the dialogue path (never re-verified here,
    only `handle_step_submission` is under test, not `verify_step()`)."""
    wrong: dict[str, Any] = {}
    for key, value in correct_fields.items():
        if isinstance(value, int):
            wrong[key] = value + 1
        elif isinstance(value, str) and value not in ("<", ">", "=", "x", "/"):
            wrong[key] = "not_" + value
        else:
            wrong[key] = value
    return wrong


@pytest.mark.parametrize(
    "topic,problem", _all_problem_cases(), ids=lambda v: v.problem_id if isinstance(v, Problem) else v
)
async def test_first_wrong_step_never_falls_back_to_generic_message(
    topic: str, problem: Problem
) -> None:
    entry_node = problem.step_graph[0]
    store = DialogueStateStore(fakeredis.FakeAsyncRedis(decode_responses=True))
    result = await handle_step_submission(
        state_store=store,
        llm_client=MockLLMProvider(),
        session_id=f"sweep-{problem.problem_id}",
        problem_id=problem.problem_id,
        topic=topic,
        step_type=entry_node.type,
        correct_fields=entry_node.expected_state,
        student_fields=_wrong_student_fields(entry_node.expected_state),
        verify_result=VerifyResult(
            is_valid=False,
            matched_step_id=None,
            confidence=0.5,
            error_signal=ErrorSignal(
                kind="field_mismatch", nearest_matched_step_id=entry_node.step_id
            ),
        ),
        classification=None,
        timing_policy=InterventionPolicy.IMMEDIATE,
        problem_is_complete=False,
        given=problem.given,
    )
    assert result.event == "explaining"
    assert result.message is not None
    assert result.message != _FALLBACK_MESSAGE, (
        f"{topic}/{problem.problem_id}: first wrong step fell back to the generic canned "
        "message — the mock provider's draft failed the leakage/readability gates on every "
        "attempt, which should never happen for a well-formed mock response"
    )


_MIXED_TOPIC_FIRST_NODE_FAMILY: dict[str, dict[str, str]] = {
    "area_perimeter": {"compute_area": "area", "compute_perimeter": "perimeter"},
    "multiplication_division": {"multiply_units": "multiply", "divide_tens": "divide"},
}

_FORBIDDEN_BY_FAMILY: dict[str, tuple[str, ...]] = {
    "area": ("walk", "edge", "perimeter"),
    "perimeter": ("tile",),
    "multiply": ("divide", "quotient", "share"),
    "divide": ("multiply", "product"),
}


@pytest.mark.parametrize(
    "topic,problem",
    [
        (topic, problem)
        for topic, dirname in _ALL_TOPIC_DIRS
        if topic in _MIXED_TOPIC_FIRST_NODE_FAMILY
        for problem in _load_fixtures(dirname)
    ],
    ids=lambda v: v.problem_id if isinstance(v, Problem) else v,
)
async def test_repeated_error_analogy_never_drifts_to_the_other_operation(
    topic: str, problem: Problem
) -> None:
    entry_node = problem.step_graph[0]
    family = _MIXED_TOPIC_FIRST_NODE_FAMILY[topic].get(entry_node.type)
    if family is None:
        pytest.skip(f"{topic}/{problem.problem_id}: first node type {entry_node.type!r} not mapped")
    store = DialogueStateStore(fakeredis.FakeAsyncRedis(decode_responses=True))
    kwargs: dict[str, Any] = dict(
        state_store=store,
        llm_client=MockLLMProvider(),
        session_id=f"sweep-analogy-{problem.problem_id}",
        problem_id=problem.problem_id,
        topic=topic,
        step_type=entry_node.type,
        correct_fields=entry_node.expected_state,
        student_fields=_wrong_student_fields(entry_node.expected_state),
        verify_result=VerifyResult(
            is_valid=False,
            matched_step_id=None,
            confidence=0.5,
            error_signal=ErrorSignal(
                kind="field_mismatch", nearest_matched_step_id=entry_node.step_id
            ),
        ),
        classification=None,
        timing_policy=InterventionPolicy.IMMEDIATE,
        problem_is_complete=False,
        given=problem.given,
    )
    await handle_step_submission(**kwargs)
    second = await handle_step_submission(**kwargs)
    assert second.message is not None
    lowered = second.message.lower()
    for forbidden in _FORBIDDEN_BY_FAMILY[family]:
        assert forbidden not in lowered, (
            f"{topic}/{problem.problem_id} ({family}): repeat-attempt analogy contains "
            f"{forbidden!r}, the OTHER operation's vocabulary: {second.message!r}"
        )
