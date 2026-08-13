"""Serialization tests for the verifier pipeline-boundary types."""

from studyhelp.schemas.step_schema import Problem
from studyhelp.schemas.verify import (
    ErrorSignal,
    FieldDiscrepancy,
    ProblemState,
    StudentStep,
    VerifyResult,
)


def test_student_step_holds_structured_fields_not_a_string() -> None:
    step = StudentStep(
        step_type="borrow",
        fields={
            "from_column": "tens",
            "from_digit_before": 4,
            "from_digit_after": 3,
            "to_column": "units",
            "to_digit_before": 2,
            "to_digit_after": 12,
        },
    )
    assert step.step_type == "borrow"
    assert step.fields["to_digit_after"] == 12


def test_error_signal_defaults_to_no_discrepancies() -> None:
    signal = ErrorSignal(kind="none")
    assert signal.discrepant_fields == []
    assert signal.nearest_matched_step_id is None
    assert signal.note is None


def test_error_signal_field_mismatch_round_trip() -> None:
    signal = ErrorSignal(
        kind="field_mismatch",
        discrepant_fields=[FieldDiscrepancy(field="result_digit", expected=5, actual=3)],
        nearest_matched_step_id="s3_sub_units",
        note="low_confidence_passthrough",
    )
    dumped = signal.model_dump(mode="json")
    reloaded = ErrorSignal.model_validate(dumped)
    assert reloaded == signal
    assert reloaded.discrepant_fields[0].field == "result_digit"


def test_verify_result_valid_has_no_error_signal_required() -> None:
    result = VerifyResult(is_valid=True, matched_step_id="s1_cmp_units", confidence=1.0)
    assert result.error_signal is None


def test_verify_result_invalid_carries_error_signal() -> None:
    result = VerifyResult(
        is_valid=False,
        matched_step_id=None,
        confidence=0.82,
        error_signal=ErrorSignal(kind="field_mismatch"),
    )
    assert result.error_signal is not None
    assert result.error_signal.kind == "field_mismatch"


def test_problem_state_tracks_accepted_step_ids(problem_542_187: Problem) -> None:
    state = ProblemState(problem=problem_542_187, accepted_step_ids=["s1_cmp_units"])
    assert state.accepted_step_ids == ["s1_cmp_units"]
    assert state.problem.problem_id == "subtraction-borrow-014"


def test_problem_state_defaults_to_no_accepted_steps(problem_542_187: Problem) -> None:
    state = ProblemState(problem=problem_542_187)
    assert state.accepted_step_ids == []
