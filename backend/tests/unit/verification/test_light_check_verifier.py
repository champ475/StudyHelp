"""Unit tests for the shared light-check verifier (`_light_check/base.py`).

`patterns` (Ch.7) is the one light-check topic whose problems are a genuine
2-step DAG (`patterns_common_difference` -> `patterns_next_term`), unlike
every other light-check topic's single-step problems — this is the
regression case for CLAUDE.md's open-ended-review Issue B: a student who
answers the *next term* directly, while step 1 still expects the *common
difference*, was flagged wrong outright (frontier-only search), instead of
being accepted as a valid-but-non-adjacent match the way every heavy DAG
topic's verifier already treats a skip-ahead submission (ARCHITECTURE.md
D59/D65).
"""

import pytest

from studyhelp.schemas.step_schema import Problem
from studyhelp.schemas.verify import ProblemState, StudentStep
from studyhelp.verification.confidence import NON_ADJACENT_MATCH_CONFIDENCE
from studyhelp.verification.topics._light_check.base import LightCheckVerifier


@pytest.fixture
def verifier() -> LightCheckVerifier:
    return LightCheckVerifier(topic="patterns")


@pytest.fixture
def pattern_problem() -> Problem:
    """2, 4, 6, 8, ... -> common difference 2, next term 10."""
    return Problem.model_validate(
        {
            "problem_id": "patterns-001",
            "ncert_ref": {
                "class": 5,
                "chapter": 7,
                "chapter_title": "Can You See the Pattern?",
                "topic": "patterns",
            },
            "display_label": "Pattern: 2, 4, 6, 8, ...",
            "given": {"question": "..."},
            "final_answer": {"answer": "10"},
            "step_graph": [
                {
                    "step_id": "s1_diff",
                    "type": "patterns_common_difference",
                    "expected_state": {"answer": "2"},
                    "next": ["s2_next"],
                },
                {
                    "step_id": "s2_next",
                    "type": "patterns_next_term",
                    "expected_state": {"answer": "10"},
                    "next": [],
                },
            ],
            "alt_paths": [],
        }
    )


def _text(value: str) -> StudentStep:
    return StudentStep(step_type="free_text_step", fields={"text": value})


def test_correct_first_step_matches_frontier(
    verifier: LightCheckVerifier, pattern_problem: Problem
) -> None:
    state = ProblemState(problem=pattern_problem)
    result = verifier.verify_step(state, _text("2"))
    assert result.is_valid is True
    assert result.matched_step_id == "s1_diff"
    assert result.confidence == 1.0
    assert result.error_signal is None


def test_full_correct_walkthrough(verifier: LightCheckVerifier, pattern_problem: Problem) -> None:
    accepted: list[str] = []
    for text in ["2", "10"]:
        state = ProblemState(problem=pattern_problem, accepted_step_ids=accepted)
        result = verifier.verify_step(state, _text(text))
        assert result.is_valid is True, f"'{text}' unexpectedly rejected: {result.error_signal}"
        assert result.matched_step_id is not None
        accepted.append(result.matched_step_id)
    assert accepted == ["s1_diff", "s2_next"]


def test_next_term_answered_directly_at_step_one_is_accepted_non_adjacent(
    verifier: LightCheckVerifier, pattern_problem: Problem
) -> None:
    """Bug1/Bug3-class regression (Issue B): the student typed the correct
    *next term* while step 1 still expects the *common difference* — this
    is a valid further-along answer, not a wrong one, and must be accepted
    (surfaced at non-adjacent confidence) rather than flagged wrong."""
    state = ProblemState(problem=pattern_problem)
    result = verifier.verify_step(state, _text("10"))
    assert result.is_valid is True
    assert result.matched_step_id == "s2_next"
    assert result.confidence == pytest.approx(NON_ADJACENT_MATCH_CONFIDENCE)
    assert result.error_signal is not None
    assert result.error_signal.note == "non_adjacent_valid_match"
    matched_node = pattern_problem.node(result.matched_step_id)
    assert matched_node is not None
    assert matched_node.next == []  # terminal -> the orchestrator can end the problem here


def test_genuinely_wrong_answer_is_rejected_against_the_frontier_step(
    verifier: LightCheckVerifier, pattern_problem: Problem
) -> None:
    """A wrong guess that matches neither reachable node's answer must
    still be diagnosed against the step the student is actually on (the
    frontier), not an arbitrary reachable node."""
    state = ProblemState(problem=pattern_problem)
    result = verifier.verify_step(state, _text("3"))
    assert result.is_valid is False
    assert result.error_signal is not None
    assert result.error_signal.nearest_matched_step_id == "s1_diff"
    assert result.error_signal.discrepant_fields[0].expected == "2"
