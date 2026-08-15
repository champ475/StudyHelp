import json
from pathlib import Path

import pytest

from studyhelp.schemas.step_schema import Problem
from studyhelp.schemas.verify import ProblemState, StudentStep
from studyhelp.verification.topics.fractions_addition.verifier import FractionsAdditionVerifier

_FIXTURES_DIR = (
    Path(__file__).parents[3] / "src" / "studyhelp" / "seed" / "fixtures" / "problems" / "ch_fractions"
)


@pytest.fixture
def verifier() -> FractionsAdditionVerifier:
    return FractionsAdditionVerifier()


@pytest.fixture
def problem_1_4_plus_1_6() -> Problem:
    """1/4 + 1/6 = 5/12 — unlike `problem_1_2_plus_1_6`, neither original
    denominator coincides with the target common denominator (12), so a
    student who re-types the unconverted fractions shares zero fields with
    the expected step and is unambiguously wrong."""
    data = json.loads((_FIXTURES_DIR / "problem_001_1_4_plus_1_6.json").read_text())
    return Problem.model_validate(data)


def _text_step(text: str) -> StudentStep:
    return StudentStep(step_type="fraction_step", fields={"text": text})


def test_first_step_correct_matches_frontier(
    verifier: FractionsAdditionVerifier, problem_1_2_plus_1_6: Problem
) -> None:
    state = ProblemState(problem=problem_1_2_plus_1_6)
    result = verifier.verify_step(state, _text_step("3/6 + 1/6"))
    assert result.is_valid is True
    assert result.matched_step_id == "s1_common_denom"
    assert result.confidence == 1.0
    assert result.parsed_fields == {"left_num": 3, "left_den": 6, "op": "+", "right_num": 1, "right_den": 6}


def test_full_correct_walkthrough_reaches_final_answer(
    verifier: FractionsAdditionVerifier, problem_1_2_plus_1_6: Problem
) -> None:
    accepted: list[str] = []
    for text in ["3/6 + 1/6", "4/6", "2/3", "2/3"]:
        state = ProblemState(problem=problem_1_2_plus_1_6, accepted_step_ids=accepted)
        result = verifier.verify_step(state, _text_step(text))
        assert result.is_valid is True, f"'{text}' unexpectedly rejected: {result.error_signal}"
        assert result.matched_step_id is not None
        accepted.append(result.matched_step_id)
    assert accepted == ["s1_common_denom", "s2_add_numerators", "s3_simplify", "s4_final"]


def test_no_common_denominator_bug_is_rejected(
    verifier: FractionsAdditionVerifier, problem_1_4_plus_1_6: Problem
) -> None:
    state = ProblemState(problem=problem_1_4_plus_1_6)
    result = verifier.verify_step(state, _text_step("1/4 + 1/6"))
    assert result.is_valid is False
    assert result.error_signal is not None
    assert result.error_signal.nearest_matched_step_id == "s1_common_denom"


def test_forgot_to_simplify_is_rejected(
    verifier: FractionsAdditionVerifier, problem_1_2_plus_1_6: Problem
) -> None:
    state = ProblemState(problem=problem_1_2_plus_1_6, accepted_step_ids=["s1_common_denom", "s2_add_numerators"])
    result = verifier.verify_step(state, _text_step("4/6"))
    assert result.is_valid is False
    assert result.error_signal is not None
    assert result.error_signal.nearest_matched_step_id == "s3_simplify"


def test_malformed_text_reports_malformed(
    verifier: FractionsAdditionVerifier, problem_1_2_plus_1_6: Problem
) -> None:
    state = ProblemState(problem=problem_1_2_plus_1_6)
    result = verifier.verify_step(state, _text_step("banana"))
    assert result.is_valid is False
    assert result.error_signal is not None
    assert result.error_signal.kind == "malformed"
