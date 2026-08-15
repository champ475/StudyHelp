import json
from pathlib import Path

import pytest

from studyhelp.schemas.step_schema import Problem
from studyhelp.schemas.verify import ProblemState, StudentStep
from studyhelp.verification.topics.lcm_hcf.verifier import LcmHcfVerifier

_FIXTURES_DIR = (
    Path(__file__).parents[3] / "src" / "studyhelp" / "seed" / "fixtures" / "problems" / "ch6_lcm_hcf"
)


@pytest.fixture
def verifier() -> LcmHcfVerifier:
    return LcmHcfVerifier()


@pytest.fixture
def problem_hcf_12_18() -> Problem:
    data = json.loads((_FIXTURES_DIR / "problem_001_hcf_12_18.json").read_text())
    return Problem.model_validate(data)


@pytest.fixture
def problem_lcm_4_6() -> Problem:
    data = json.loads((_FIXTURES_DIR / "problem_006_lcm_4_6.json").read_text())
    return Problem.model_validate(data)


def _text_step(text: str) -> StudentStep:
    return StudentStep(step_type="free_text_step", fields={"text": text})


def test_full_correct_hcf_walkthrough(verifier: LcmHcfVerifier, problem_hcf_12_18: Problem) -> None:
    accepted: list[str] = []
    for text in ["1,2,3,6", "6"]:
        state = ProblemState(problem=problem_hcf_12_18, accepted_step_ids=accepted)
        result = verifier.verify_step(state, _text_step(text))
        assert result.is_valid is True, f"'{text}' unexpectedly rejected: {result.error_signal}"
        assert result.matched_step_id is not None
        accepted.append(result.matched_step_id)
    assert accepted == ["s1_common_factors", "s2_final"]


def test_full_correct_lcm_walkthrough(verifier: LcmHcfVerifier, problem_lcm_4_6: Problem) -> None:
    accepted: list[str] = []
    for text in ["12,24,36", "12"]:
        state = ProblemState(problem=problem_lcm_4_6, accepted_step_ids=accepted)
        result = verifier.verify_step(state, _text_step(text))
        assert result.is_valid is True, f"'{text}' unexpectedly rejected: {result.error_signal}"
        assert result.matched_step_id is not None
        accepted.append(result.matched_step_id)
    assert accepted == ["s1_common_multiples", "s2_final"]


def test_out_of_order_list_still_matches(verifier: LcmHcfVerifier, problem_hcf_12_18: Problem) -> None:
    state = ProblemState(problem=problem_hcf_12_18)
    result = verifier.verify_step(state, _text_step("6,1,3,2"))
    assert result.is_valid is True
    assert result.matched_step_id == "s1_common_factors"


def test_wrong_final_value_is_rejected(verifier: LcmHcfVerifier, problem_hcf_12_18: Problem) -> None:
    state = ProblemState(problem=problem_hcf_12_18, accepted_step_ids=["s1_common_factors"])
    result = verifier.verify_step(state, _text_step("12"))  # the LCM, not the HCF
    assert result.is_valid is False
    assert result.error_signal is not None
    assert result.error_signal.kind == "field_mismatch"


def test_list_shifted_by_one_bug_is_rejected(verifier: LcmHcfVerifier, problem_lcm_4_6: Problem) -> None:
    state = ProblemState(problem=problem_lcm_4_6)
    result = verifier.verify_step(state, _text_step("24,36,48"))
    assert result.is_valid is False
    assert result.error_signal is not None
    assert result.error_signal.nearest_matched_step_id == "s1_common_multiples"


def test_malformed_text_reports_malformed(verifier: LcmHcfVerifier, problem_hcf_12_18: Problem) -> None:
    state = ProblemState(problem=problem_hcf_12_18)
    result = verifier.verify_step(state, _text_step("banana"))
    assert result.is_valid is False
    assert result.error_signal is not None
    assert result.error_signal.kind == "malformed"
