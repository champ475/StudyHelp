import json
from pathlib import Path

import pytest

from studyhelp.schemas.step_schema import Problem
from studyhelp.schemas.verify import ProblemState, StudentStep
from studyhelp.verification.confidence import NON_ADJACENT_MATCH_CONFIDENCE
from studyhelp.verification.topics.decimals.verifier import DecimalsVerifier

_FIXTURES_DIR = (
    Path(__file__).parents[3]
    / "src"
    / "studyhelp"
    / "seed"
    / "fixtures"
    / "problems"
    / "ch10_decimals"
)


@pytest.fixture
def verifier() -> DecimalsVerifier:
    return DecimalsVerifier()


@pytest.fixture
def problem_add() -> Problem:
    """3.40 + 1.25 = 4.65"""
    data = json.loads((_FIXTURES_DIR / "problem_001_3_40_plus_1_25.json").read_text())
    return Problem.model_validate(data)


@pytest.fixture
def problem_sub() -> Problem:
    """12.75 - 4.30 = 8.45"""
    data = json.loads((_FIXTURES_DIR / "problem_003_12_75_minus_4_30.json").read_text())
    return Problem.model_validate(data)


def _text_step(text: str) -> StudentStep:
    return StudentStep(step_type="free_text_step", fields={"text": text})


def test_full_correct_addition_walkthrough(
    verifier: DecimalsVerifier, problem_add: Problem
) -> None:
    accepted: list[str] = []
    for text in ["3.40, 1.25", "4.65", "4.65"]:
        state = ProblemState(problem=problem_add, accepted_step_ids=accepted)
        result = verifier.verify_step(state, _text_step(text))
        assert result.is_valid is True, f"'{text}' unexpectedly rejected: {result.error_signal}"
        assert result.matched_step_id is not None
        accepted.append(result.matched_step_id)
    assert accepted == ["s1_align", "s2_compute", "s3_final"]


def test_full_correct_subtraction_walkthrough(
    verifier: DecimalsVerifier, problem_sub: Problem
) -> None:
    accepted: list[str] = []
    for text in ["12.75, 4.30", "8.45", "8.45"]:
        state = ProblemState(problem=problem_sub, accepted_step_ids=accepted)
        result = verifier.verify_step(state, _text_step(text))
        assert result.is_valid is True, f"'{text}' unexpectedly rejected: {result.error_signal}"
        assert result.matched_step_id is not None
        accepted.append(result.matched_step_id)
    assert accepted == ["s1_align", "s2_compute", "s3_final"]


def test_decimal_point_shifted_bug_is_rejected(
    verifier: DecimalsVerifier, problem_add: Problem
) -> None:
    state = ProblemState(problem=problem_add, accepted_step_ids=["s1_align"])
    result = verifier.verify_step(state, _text_step("46.50"))
    assert result.is_valid is False
    assert result.error_signal is not None
    assert result.error_signal.nearest_matched_step_id == "s2_compute"


def test_tenths_written_as_hundredths_bug_is_rejected(
    verifier: DecimalsVerifier, problem_add: Problem
) -> None:
    state = ProblemState(problem=problem_add)
    result = verifier.verify_step(state, _text_step("3.04, 1.25"))
    assert result.is_valid is False
    assert result.error_signal is not None
    assert result.error_signal.nearest_matched_step_id == "s1_align"


def test_malformed_text_reports_malformed(verifier: DecimalsVerifier, problem_add: Problem) -> None:
    state = ProblemState(problem=problem_add)
    result = verifier.verify_step(state, _text_step("banana"))
    assert result.is_valid is False
    assert result.error_signal is not None
    assert result.error_signal.kind == "malformed"


def test_direct_final_answer_from_the_start_is_accepted_non_adjacent(
    verifier: DecimalsVerifier, problem_add: Problem
) -> None:
    """Bug1 regression: a student who skips straight to the correct final
    answer (no align/compute steps submitted yet) must not be flagged
    wrong just because it isn't the prescribed next step (ARCHITECTURE.md
    D59) — accepted, but surfaced at NON_ADJACENT_MATCH_CONFIDENCE so it's
    still visible for review, same as SubtractionBorrowingVerifier."""
    state = ProblemState(problem=problem_add, accepted_step_ids=[])
    result = verifier.verify_step(state, _text_step("4.65"))
    assert result.is_valid is True
    assert result.matched_step_id == "s3_final"
    assert result.confidence == pytest.approx(NON_ADJACENT_MATCH_CONFIDENCE)
    assert result.error_signal is not None
    assert result.error_signal.note == "non_adjacent_valid_match"


def test_direct_final_answer_reaches_a_terminal_node_with_no_next_step(
    verifier: DecimalsVerifier, problem_add: Problem
) -> None:
    """Bug3 regression: the matched node for a skip-ahead final answer must
    itself be terminal (`next == []`) so the orchestrator's
    `problem_is_complete` check (api/routes/sessions.py) can end the
    problem right there instead of forcing the remaining predefined steps."""
    state = ProblemState(problem=problem_add, accepted_step_ids=[])
    result = verifier.verify_step(state, _text_step("4.65"))
    assert result.matched_step_id is not None
    matched_node = problem_add.node(result.matched_step_id)
    assert matched_node is not None
    assert matched_node.next == []
