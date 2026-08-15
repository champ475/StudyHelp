import json
from pathlib import Path

import pytest

from studyhelp.schemas.step_schema import Problem
from studyhelp.schemas.verify import ProblemState, StudentStep
from studyhelp.verification.topics.area_perimeter.verifier import AreaPerimeterVerifier

_FIXTURES_DIR = (
    Path(__file__).parents[3]
    / "src"
    / "studyhelp"
    / "seed"
    / "fixtures"
    / "problems"
    / "ch11_area_perimeter"
)


@pytest.fixture
def verifier() -> AreaPerimeterVerifier:
    return AreaPerimeterVerifier()


@pytest.fixture
def problem_area() -> Problem:
    """Area of a 6 x 4 rectangle = 24."""
    data = json.loads((_FIXTURES_DIR / "problem_001_rect_area_6x4.json").read_text())
    return Problem.model_validate(data)


@pytest.fixture
def problem_perimeter() -> Problem:
    """Perimeter of a 6 x 4 rectangle = 20."""
    data = json.loads((_FIXTURES_DIR / "problem_002_rect_perimeter_6x4.json").read_text())
    return Problem.model_validate(data)


def _text_step(text: str) -> StudentStep:
    return StudentStep(step_type="free_text_step", fields={"text": text})


def test_full_correct_area_walkthrough(verifier: AreaPerimeterVerifier, problem_area: Problem) -> None:
    accepted: list[str] = []
    for text in ["6 x 4 = 24", "24"]:
        state = ProblemState(problem=problem_area, accepted_step_ids=accepted)
        result = verifier.verify_step(state, _text_step(text))
        assert result.is_valid is True, f"'{text}' unexpectedly rejected: {result.error_signal}"
        assert result.matched_step_id is not None
        accepted.append(result.matched_step_id)
    assert accepted == ["s1_compute", "s2_final"]


def test_full_correct_perimeter_walkthrough(
    verifier: AreaPerimeterVerifier, problem_perimeter: Problem
) -> None:
    accepted: list[str] = []
    for text in ["2 x (6 + 4) = 20", "20"]:
        state = ProblemState(problem=problem_perimeter, accepted_step_ids=accepted)
        result = verifier.verify_step(state, _text_step(text))
        assert result.is_valid is True, f"'{text}' unexpectedly rejected: {result.error_signal}"
        assert result.matched_step_id is not None
        accepted.append(result.matched_step_id)
    assert accepted == ["s1_compute", "s2_final"]


def test_formula_confusion_bug_is_rejected(
    verifier: AreaPerimeterVerifier, problem_area: Problem
) -> None:
    """Student applies the perimeter formula (2 x (6+4) = 20) on an area problem."""
    state = ProblemState(problem=problem_area)
    result = verifier.verify_step(state, _text_step("6 x 4 = 20"))
    assert result.is_valid is False
    assert result.error_signal is not None
    assert result.error_signal.nearest_matched_step_id == "s1_compute"


def test_forgot_times_two_bug_is_rejected(
    verifier: AreaPerimeterVerifier, problem_perimeter: Problem
) -> None:
    """Student adds length + width once and forgets to double it."""
    state = ProblemState(problem=problem_perimeter)
    result = verifier.verify_step(state, _text_step("2 x (6 + 4) = 10"))
    assert result.is_valid is False
    assert result.error_signal is not None
    assert result.error_signal.nearest_matched_step_id == "s1_compute"


def test_malformed_text_reports_malformed(
    verifier: AreaPerimeterVerifier, problem_area: Problem
) -> None:
    state = ProblemState(problem=problem_area)
    result = verifier.verify_step(state, _text_step("banana"))
    assert result.is_valid is False
    assert result.error_signal is not None
    assert result.error_signal.kind == "malformed"
