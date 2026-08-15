"""Walks every seeded area_perimeter problem fixture end-to-end through the
real verifier, submitting each node's own `expected_state` (rendered as the
free text a student would actually type) in canonical order. Strongest
available check that hand-authored fixture arithmetic is self-consistent —
mirrors `test_lcm_hcf_fixtures_walkthrough.py`'s / `test_decimals_fixtures_
walkthrough.py`'s pattern."""

import json
from pathlib import Path

import pytest
import sympy

from studyhelp.schemas.step_schema import Problem, StepNode
from studyhelp.schemas.verify import ProblemState, StudentStep
from studyhelp.verification.topics.area_perimeter.verifier import AreaPerimeterVerifier

FIXTURES_DIR = (
    Path(__file__).parents[3]
    / "src"
    / "studyhelp"
    / "seed"
    / "fixtures"
    / "problems"
    / "ch11_area_perimeter"
)


def _load_all_fixtures() -> list[Problem]:
    return [
        Problem.model_validate(json.loads(path.read_text()))
        for path in sorted(FIXTURES_DIR.glob("*.json"))
    ]


def _render(node: StepNode) -> str:
    if node.type == "compute_area":
        state = node.expected_state
        return f"{state['length']} x {state['width']} = {state['result']}"
    if node.type == "compute_perimeter":
        state = node.expected_state
        return f"2 x ({state['length']} + {state['width']}) = {state['result']}"
    return str(node.expected_state["value"])


def _canonical_path(problem: Problem) -> list[StepNode]:
    path = [problem.step_graph[0]]
    while path[-1].next:
        node = problem.node(path[-1].next[0])
        assert node is not None, f"dangling next pointer in {problem.problem_id}"
        path.append(node)
    return path


@pytest.mark.parametrize("problem", _load_all_fixtures(), ids=lambda p: p.problem_id)
def test_canonical_path_walks_cleanly_to_final_answer(problem: Problem) -> None:
    verifier = AreaPerimeterVerifier()
    accepted: list[str] = []

    for node in _canonical_path(problem):
        state = ProblemState(problem=problem, accepted_step_ids=accepted)
        text = _render(node)
        result = verifier.verify_step(
            state, StudentStep(step_type="free_text_step", fields={"text": text})
        )
        assert result.is_valid is True, (
            f"{problem.problem_id}/{node.step_id} unexpectedly invalid: {result}"
        )
        assert result.matched_step_id == node.step_id, (
            f"{problem.problem_id}/{node.step_id} matched {result.matched_step_id} instead "
            f"(confidence={result.confidence}, error_signal={result.error_signal})"
        )
        accepted.append(node.step_id)

    last_node = problem.node(accepted[-1])
    assert last_node is not None
    assert last_node.type == "write_final_answer"
    assert last_node.expected_state["value"] == problem.final_answer["value"]
    assert last_node.next == []


@pytest.mark.parametrize("problem", _load_all_fixtures(), ids=lambda p: p.problem_id)
def test_final_answer_matches_raw_area_perimeter_arithmetic(problem: Problem) -> None:
    length, width, measure = problem.given["length"], problem.given["width"], problem.given["measure"]
    expected = length * width if measure == "area" else 2 * (length + width)
    assert expected == problem.final_answer["value"]
    assert bool(sympy.Integer(expected) == sympy.Integer(problem.final_answer["value"]))
