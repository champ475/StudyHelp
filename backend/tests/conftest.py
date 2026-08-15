import json
from pathlib import Path

import pytest

from studyhelp.schemas.step_schema import Problem

FIXTURE_PATH = (
    Path(__file__).parents[1]
    / "src"
    / "studyhelp"
    / "seed"
    / "fixtures"
    / "problems"
    / "ch1_subtraction_borrowing"
    / "problem_014_542_187.json"
)


@pytest.fixture
def problem_542_187() -> Problem:
    data = json.loads(FIXTURE_PATH.read_text())
    return Problem.model_validate(data)


FRACTIONS_FIXTURE_PATH = (
    Path(__file__).parents[1]
    / "src"
    / "studyhelp"
    / "seed"
    / "fixtures"
    / "problems"
    / "ch_fractions"
    / "problem_003_1_2_plus_1_6.json"
)


@pytest.fixture
def problem_1_2_plus_1_6() -> Problem:
    """1/2 + 1/6 = 2/3 — the one fraction fixture that requires a real
    simplification step, so it exercises the F3-forgot-to-simplify path."""
    data = json.loads(FRACTIONS_FIXTURE_PATH.read_text())
    return Problem.model_validate(data)
