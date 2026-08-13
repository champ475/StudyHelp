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
