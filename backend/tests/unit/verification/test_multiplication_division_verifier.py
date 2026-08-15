import json
from pathlib import Path

import pytest

from studyhelp.schemas.step_schema import Problem
from studyhelp.schemas.verify import ProblemState, StudentStep
from studyhelp.verification.topics.multiplication_division.verifier import (
    MultiplicationDivisionVerifier,
)

_FIXTURES_DIR = (
    Path(__file__).parents[3]
    / "src"
    / "studyhelp"
    / "seed"
    / "fixtures"
    / "problems"
    / "ch13_multiplication_division"
)


@pytest.fixture
def verifier() -> MultiplicationDivisionVerifier:
    return MultiplicationDivisionVerifier()


@pytest.fixture
def problem_mult() -> Problem:
    """34 x 6 = 204."""
    data = json.loads((_FIXTURES_DIR / "problem_001_mult_34x6.json").read_text())
    return Problem.model_validate(data)


@pytest.fixture
def problem_div() -> Problem:
    """96 / 8 = 12."""
    data = json.loads((_FIXTURES_DIR / "problem_007_div_96by8.json").read_text())
    return Problem.model_validate(data)


def _text_step(text: str) -> StudentStep:
    return StudentStep(step_type="free_text_step", fields={"text": text})


def test_full_correct_multiplication_walkthrough(
    verifier: MultiplicationDivisionVerifier, problem_mult: Problem
) -> None:
    accepted: list[str] = []
    for text in ["4 x 6 = 24", "3 x 6 + 2 = 20", "204"]:
        state = ProblemState(problem=problem_mult, accepted_step_ids=accepted)
        result = verifier.verify_step(state, _text_step(text))
        assert result.is_valid is True, f"'{text}' unexpectedly rejected: {result.error_signal}"
        assert result.matched_step_id is not None
        accepted.append(result.matched_step_id)
    assert accepted == ["s1_units", "s2_tens", "s3_final"]


def test_full_correct_division_walkthrough(
    verifier: MultiplicationDivisionVerifier, problem_div: Problem
) -> None:
    accepted: list[str] = []
    for text in ["9 / 8 = 1 remainder 1", "16 / 8 = 2 remainder 0", "12"]:
        state = ProblemState(problem=problem_div, accepted_step_ids=accepted)
        result = verifier.verify_step(state, _text_step(text))
        assert result.is_valid is True, f"'{text}' unexpectedly rejected: {result.error_signal}"
        assert result.matched_step_id is not None
        accepted.append(result.matched_step_id)
    assert accepted == ["s1_tens", "s2_units", "s3_final"]


def test_forgot_carry_bug_is_rejected(
    verifier: MultiplicationDivisionVerifier, problem_mult: Problem
) -> None:
    state = ProblemState(problem=problem_mult, accepted_step_ids=["s1_units"])
    result = verifier.verify_step(state, _text_step("3 x 6 + 0 = 18"))
    assert result.is_valid is False
    assert result.error_signal is not None
    assert result.error_signal.nearest_matched_step_id == "s2_tens"


def test_misplaced_remainder_bug_is_rejected(
    verifier: MultiplicationDivisionVerifier, problem_div: Problem
) -> None:
    state = ProblemState(problem=problem_div, accepted_step_ids=["s1_tens"])
    result = verifier.verify_step(state, _text_step("6 / 8 = 0 remainder 6"))
    assert result.is_valid is False
    assert result.error_signal is not None
    assert result.error_signal.nearest_matched_step_id == "s2_units"


def test_malformed_text_reports_malformed(
    verifier: MultiplicationDivisionVerifier, problem_mult: Problem
) -> None:
    state = ProblemState(problem=problem_mult)
    result = verifier.verify_step(state, _text_step("banana"))
    assert result.is_valid is False
    assert result.error_signal is not None
    assert result.error_signal.kind == "malformed"
