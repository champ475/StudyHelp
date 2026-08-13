"""Walks every seeded problem fixture end-to-end through the real verifier,
submitting each node's own `expected_state` in canonical order. This is the
strongest available check that hand-authored fixture arithmetic is actually
self-consistent — it doesn't just eyeball the JSON, it runs it through the
same verify_step() the pipeline uses."""

import json
from pathlib import Path

import pytest

from studyhelp.schemas.step_schema import Problem, StepNode
from studyhelp.schemas.verify import ProblemState, StudentStep
from studyhelp.verification.topics.subtraction_borrowing.verifier import (
    SubtractionBorrowingVerifier,
)

FIXTURES_DIR = (
    Path(__file__).parents[3]
    / "src"
    / "studyhelp"
    / "seed"
    / "fixtures"
    / "problems"
    / "ch1_subtraction_borrowing"
)


def _load_all_fixtures() -> list[Problem]:
    return [
        Problem.model_validate(json.loads(path.read_text()))
        for path in sorted(FIXTURES_DIR.glob("*.json"))
    ]


def _canonical_path(problem: Problem) -> list[StepNode]:
    """Follows the first-listed `next` pointer from the first node — this
    walks only the primary linear solution, skipping any alt-path branches
    (e.g. the combined-step node in the canonical 542-187 fixture)."""
    path = [problem.step_graph[0]]
    while path[-1].next:
        node = problem.node(path[-1].next[0])
        assert node is not None, f"dangling next pointer in {problem.problem_id}"
        path.append(node)
    return path


@pytest.mark.parametrize("problem", _load_all_fixtures(), ids=lambda p: p.problem_id)
def test_canonical_path_walks_cleanly_to_final_answer(problem: Problem) -> None:
    verifier = SubtractionBorrowingVerifier()
    accepted: list[str] = []

    for node in _canonical_path(problem):
        state = ProblemState(problem=problem, accepted_step_ids=accepted)
        result = verifier.verify_step(
            state, StudentStep(step_type=node.type, fields=node.expected_state)
        )
        assert result.is_valid is True, (
            f"{problem.problem_id}/{node.step_id} unexpectedly invalid: {result}"
        )
        assert result.matched_step_id == node.step_id, (
            f"{problem.problem_id}/{node.step_id} matched {result.matched_step_id} instead "
            f"(confidence={result.confidence}, error_signal={result.error_signal})"
        )
        assert result.confidence == 1.0, (
            f"{problem.problem_id}/{node.step_id} matched with confidence {result.confidence}, "
            "expected a clean frontier hit (1.0) since this is the canonical linear path"
        )
        accepted.append(node.step_id)

    last_node = problem.node(accepted[-1])
    assert last_node is not None
    assert last_node.type == "write_final_answer"
    assert last_node.expected_state["value"] == problem.final_answer
    assert last_node.next == []


@pytest.mark.parametrize("problem", _load_all_fixtures(), ids=lambda p: p.problem_id)
def test_final_answer_matches_raw_arithmetic(problem: Problem) -> None:
    minuend = problem.given["minuend"]
    subtrahend = problem.given["subtrahend"]
    assert minuend - subtrahend == problem.final_answer
