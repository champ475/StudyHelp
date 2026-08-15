"""Walks every seeded decimals problem fixture end-to-end through the real
verifier, submitting each node's own `expected_state` (rendered as the free
text a student would actually type) in canonical order. Strongest available
check that hand-authored fixture arithmetic is self-consistent — mirrors
`test_lcm_hcf_fixtures_walkthrough.py`'s pattern."""

import json
from pathlib import Path

import pytest
import sympy

from studyhelp.schemas.step_schema import Problem, StepNode
from studyhelp.schemas.verify import ProblemState, StudentStep
from studyhelp.verification.topics.decimals.verifier import DecimalsVerifier

FIXTURES_DIR = (
    Path(__file__).parents[3] / "src" / "studyhelp" / "seed" / "fixtures" / "problems" / "ch10_decimals"
)


def _load_all_fixtures() -> list[Problem]:
    return [
        Problem.model_validate(json.loads(path.read_text()))
        for path in sorted(FIXTURES_DIR.glob("*.json"))
    ]


def _as_decimal_text(hundredths: int) -> str:
    whole, frac = divmod(hundredths, 100)
    return f"{whole}.{frac:02d}"


def _render(node: StepNode) -> str:
    if node.type == "align_place_value":
        a = _as_decimal_text(node.expected_state["a_hundredths"])
        b = _as_decimal_text(node.expected_state["b_hundredths"])
        return f"{a}, {b}"
    return _as_decimal_text(node.expected_state["result_hundredths"])


def _canonical_path(problem: Problem) -> list[StepNode]:
    path = [problem.step_graph[0]]
    while path[-1].next:
        node = problem.node(path[-1].next[0])
        assert node is not None, f"dangling next pointer in {problem.problem_id}"
        path.append(node)
    return path


@pytest.mark.parametrize("problem", _load_all_fixtures(), ids=lambda p: p.problem_id)
def test_canonical_path_walks_cleanly_to_final_answer(problem: Problem) -> None:
    verifier = DecimalsVerifier()
    accepted: list[str] = []

    for node in _canonical_path(problem):
        state = ProblemState(problem=problem, accepted_step_ids=accepted)
        text = _render(node)
        result = verifier.verify_step(
            state, StudentStep(step_type="free_text_step", fields={"text": text})
        )
        assert result.is_valid is True, (
            f"{problem.problem_id}/{node.step_id} unexpectedly invalid for '{text}': {result}"
        )
        assert result.matched_step_id == node.step_id, (
            f"{problem.problem_id}/{node.step_id} matched {result.matched_step_id} instead "
            f"(confidence={result.confidence}, error_signal={result.error_signal})"
        )
        accepted.append(node.step_id)

    last_node = problem.node(accepted[-1])
    assert last_node is not None
    assert last_node.type == "write_final_answer"
    assert last_node.expected_state["result_hundredths"] == problem.final_answer["result_hundredths"]
    assert last_node.next == []


@pytest.mark.parametrize("problem", _load_all_fixtures(), ids=lambda p: p.problem_id)
def test_final_answer_matches_raw_arithmetic(problem: Problem) -> None:
    a = sympy.Rational(problem.given["a_hundredths"], 100)
    b = sympy.Rational(problem.given["b_hundredths"], 100)
    op = problem.given["op"]
    expected = a + b if op == "+" else a - b
    actual = sympy.Rational(problem.final_answer["result_hundredths"], 100)
    assert sympy.Eq(expected, actual)
