"""Bug1/Bug3 regression, generalized from "one problem per topic" (the
scope of every prior round's verification) to every one of the ~140 seeded
problems across all 14 topics — directly requested: "test all the questions
given, and not hardcode for any specific question."

For each seeded problem, submits ONLY the terminal (`write_final_answer` /
last light-check `answer`) node's own correct text, from a fresh
`accepted_step_ids=[]` — exactly what a student who jumps straight to the
final answer, skipping every intermediate step, would type. Asserts the
verifier accepts it (`is_valid=True`) and resolves to the actual terminal
node (`next == []`), never a false "wrong step" or a match against some
earlier node.

Renders each topic's terminal-node text using each topic's own real grammar
(re-derived from `verification/topics/<topic>/free_text_parser.py`'s
documented grammar, not invented here) so a render bug in this test can't
mask a real verifier bug.
"""

import json
from pathlib import Path
from typing import Any

import pytest

from studyhelp.schemas.step_schema import Problem, StepNode
from studyhelp.schemas.verify import ProblemState, StudentStep
from studyhelp.verification.topics._light_check.base import LightCheckVerifier
from studyhelp.verification.topics.area_perimeter.verifier import AreaPerimeterVerifier
from studyhelp.verification.topics.decimals.verifier import DecimalsVerifier
from studyhelp.verification.topics.fractions_addition.verifier import FractionsAdditionVerifier
from studyhelp.verification.topics.lcm_hcf.verifier import LcmHcfVerifier
from studyhelp.verification.topics.measurement.verifier import MeasurementVerifier
from studyhelp.verification.topics.multiplication_division.verifier import (
    MultiplicationDivisionVerifier,
)
from studyhelp.verification.topics.subtraction_borrowing.verifier import (
    SubtractionBorrowingVerifier,
)

FIXTURES_ROOT = (
    Path(__file__).parents[3] / "src" / "studyhelp" / "seed" / "fixtures" / "problems"
)


def _render_bare_int(node: StepNode) -> str:
    return str(node.expected_state["value"])


def _render_decimal(node: StepNode) -> str:
    hundredths = node.expected_state["result_hundredths"]
    return f"{hundredths // 100}.{hundredths % 100:02d}"


def _render_fraction_final(node: StepNode) -> str:
    state = node.expected_state
    if node.type == "compare_fractions":
        return f"{state['left_num']}/{state['left_den']} {state['op']} {state['right_num']}/{state['right_den']}"
    return f"{state['num']}/{state['den']}"


def _render_light_check(node: StepNode) -> str:
    return str(node.expected_state["answer"])


# (topic, fixtures dirname, verifier factory, terminal-node render function)
_HEAVY_DAG_TOPICS: list[tuple[str, str, Any, Any]] = [
    ("subtraction_with_borrowing", "ch1_subtraction_borrowing", SubtractionBorrowingVerifier, _render_bare_int),
    ("fractions_addition", "ch_fractions", FractionsAdditionVerifier, _render_fraction_final),
    ("lcm_hcf", "ch6_lcm_hcf", LcmHcfVerifier, _render_bare_int),
    ("decimals", "ch10_decimals", DecimalsVerifier, _render_decimal),
    ("area_perimeter", "ch11_area_perimeter", AreaPerimeterVerifier, _render_bare_int),
    ("multiplication_division", "ch13_multiplication_division", MultiplicationDivisionVerifier, _render_bare_int),
    ("measurement", "ch14_measurement", MeasurementVerifier, _render_bare_int),
]

_LIGHT_CHECK_TOPICS: list[tuple[str, str]] = [
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


def _terminal_node(problem: Problem) -> StepNode:
    terminal = [n for n in problem.step_graph if not n.next]
    assert len(terminal) == 1, f"{problem.problem_id}: expected exactly one terminal node"
    return terminal[0]


def _heavy_dag_cases() -> list[tuple[str, Problem, Any, Any]]:
    cases = []
    for topic, dirname, verifier_factory, render in _HEAVY_DAG_TOPICS:
        for problem in _load_fixtures(dirname):
            cases.append((topic, problem, verifier_factory, render))
    return cases


def _light_check_cases() -> list[tuple[str, Problem]]:
    cases = []
    for topic, dirname in _LIGHT_CHECK_TOPICS:
        for problem in _load_fixtures(dirname):
            cases.append((topic, problem))
    return cases


@pytest.mark.parametrize(
    "topic,problem,verifier_factory,render",
    _heavy_dag_cases(),
    ids=lambda v: v.problem_id if isinstance(v, Problem) else (v if isinstance(v, str) else ""),
)
def test_heavy_dag_skip_ahead_to_final_answer_is_accepted(
    topic: str, problem: Problem, verifier_factory: Any, render: Any
) -> None:
    verifier = verifier_factory()
    terminal = _terminal_node(problem)
    state = ProblemState(problem=problem, accepted_step_ids=[])
    result = verifier.verify_step(
        state, StudentStep(step_type="free_text_step", fields={"text": render(terminal)})
    )
    assert result.is_valid is True, (
        f"{topic}/{problem.problem_id}: skip-ahead final answer wrongly rejected: {result}"
    )
    matched_id = result.matched_step_id or (
        result.error_signal.nearest_matched_step_id if result.error_signal else None
    )
    assert matched_id == terminal.step_id, (
        f"{topic}/{problem.problem_id}: skip-ahead matched {matched_id!r}, "
        f"expected terminal node {terminal.step_id!r} ({result})"
    )


@pytest.mark.parametrize(
    "topic,problem",
    _light_check_cases(),
    ids=lambda v: v.problem_id if isinstance(v, Problem) else (v if isinstance(v, str) else ""),
)
def test_light_check_skip_ahead_to_final_answer_is_accepted(topic: str, problem: Problem) -> None:
    verifier = LightCheckVerifier(topic=topic)
    terminal = _terminal_node(problem)
    state = ProblemState(problem=problem, accepted_step_ids=[])
    result = verifier.verify_step(
        state,
        StudentStep(step_type="free_text_step", fields={"text": _render_light_check(terminal)}),
    )
    assert result.is_valid is True, (
        f"{topic}/{problem.problem_id}: skip-ahead final answer wrongly rejected: {result}"
    )
    matched_id = result.matched_step_id or (
        result.error_signal.nearest_matched_step_id if result.error_signal else None
    )
    assert matched_id == terminal.step_id, (
        f"{topic}/{problem.problem_id}: skip-ahead matched {matched_id!r}, "
        f"expected terminal node {terminal.step_id!r} ({result})"
    )
