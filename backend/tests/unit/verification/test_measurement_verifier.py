import json
from pathlib import Path

import pytest

from studyhelp.schemas.step_schema import Problem
from studyhelp.schemas.verify import ProblemState, StudentStep
from studyhelp.verification.topics.measurement.verifier import MeasurementVerifier

_FIXTURES_DIR = (
    Path(__file__).parents[3] / "src" / "studyhelp" / "seed" / "fixtures" / "problems" / "ch14_measurement"
)


@pytest.fixture
def verifier() -> MeasurementVerifier:
    return MeasurementVerifier()


@pytest.fixture
def problem_multiply() -> Problem:
    """3 km to m = 3000."""
    data = json.loads((_FIXTURES_DIR / "problem_001_3km_to_m.json").read_text())
    return Problem.model_validate(data)


@pytest.fixture
def problem_divide() -> Problem:
    """5000 m to km = 5."""
    data = json.loads((_FIXTURES_DIR / "problem_002_5000m_to_km.json").read_text())
    return Problem.model_validate(data)


def _text_step(text: str) -> StudentStep:
    return StudentStep(step_type="free_text_step", fields={"text": text})


def test_full_correct_multiply_walkthrough(
    verifier: MeasurementVerifier, problem_multiply: Problem
) -> None:
    accepted: list[str] = []
    for text in ["x1000", "3000", "3000"]:
        state = ProblemState(problem=problem_multiply, accepted_step_ids=accepted)
        result = verifier.verify_step(state, _text_step(text))
        assert result.is_valid is True, f"'{text}' unexpectedly rejected: {result.error_signal}"
        assert result.matched_step_id is not None
        accepted.append(result.matched_step_id)
    assert accepted == ["s1_factor", "s2_convert", "s3_final"]


def test_full_correct_divide_walkthrough(
    verifier: MeasurementVerifier, problem_divide: Problem
) -> None:
    accepted: list[str] = []
    for text in ["/1000", "5", "5"]:
        state = ProblemState(problem=problem_divide, accepted_step_ids=accepted)
        result = verifier.verify_step(state, _text_step(text))
        assert result.is_valid is True, f"'{text}' unexpectedly rejected: {result.error_signal}"
        assert result.matched_step_id is not None
        accepted.append(result.matched_step_id)
    assert accepted == ["s1_factor", "s2_convert", "s3_final"]


def test_wrong_direction_bug_is_rejected(
    verifier: MeasurementVerifier, problem_multiply: Problem
) -> None:
    state = ProblemState(problem=problem_multiply)
    result = verifier.verify_step(state, _text_step("/1000"))
    assert result.is_valid is False
    assert result.error_signal is not None
    assert result.error_signal.nearest_matched_step_id == "s1_factor"


def test_wrong_factor_bug_is_rejected(
    verifier: MeasurementVerifier, problem_multiply: Problem
) -> None:
    state = ProblemState(problem=problem_multiply)
    result = verifier.verify_step(state, _text_step("x100"))
    assert result.is_valid is False
    assert result.error_signal is not None
    assert result.error_signal.nearest_matched_step_id == "s1_factor"


def test_malformed_text_reports_malformed(
    verifier: MeasurementVerifier, problem_multiply: Problem
) -> None:
    state = ProblemState(problem=problem_multiply)
    result = verifier.verify_step(state, _text_step("banana"))
    assert result.is_valid is False
    assert result.error_signal is not None
    assert result.error_signal.kind == "malformed"
