"""Unit tests against the canonical 542-187 DAG: happy path plus a handful
of hand-picked bad/ambiguous submissions. The full ~30-case golden
regression suite lives in tests/golden/ (built separately, once this
verifier's behavior is settled)."""

import pytest

from studyhelp.schemas.step_schema import Problem
from studyhelp.schemas.verify import ProblemState, StudentStep
from studyhelp.verification.confidence import NON_ADJACENT_MATCH_CONFIDENCE, REJECT_THRESHOLD
from studyhelp.verification.topics.subtraction_borrowing.verifier import (
    SubtractionBorrowingVerifier,
)


@pytest.fixture
def verifier() -> SubtractionBorrowingVerifier:
    return SubtractionBorrowingVerifier()


def test_first_step_correct_matches_frontier(
    verifier: SubtractionBorrowingVerifier, problem_542_187: Problem
) -> None:
    state = ProblemState(problem=problem_542_187)
    step = StudentStep(
        step_type="compare_column",
        fields={
            "column": "units",
            "minuend_digit": 2,
            "subtrahend_digit": 7,
            "borrow_needed": True,
        },
    )
    result = verifier.verify_step(state, step)
    assert result.is_valid is True
    assert result.matched_step_id == "s1_cmp_units"
    assert result.confidence == 1.0
    assert result.error_signal is None


def test_full_correct_walkthrough_reaches_final_answer(
    verifier: SubtractionBorrowingVerifier, problem_542_187: Problem
) -> None:
    submissions = [
        (
            "compare_column",
            {"column": "units", "minuend_digit": 2, "subtrahend_digit": 7, "borrow_needed": True},
        ),
        (
            "borrow",
            {
                "from_column": "tens",
                "from_digit_before": 4,
                "from_digit_after": 3,
                "to_column": "units",
                "to_digit_before": 2,
                "to_digit_after": 12,
            },
        ),
        (
            "subtract_column",
            {"column": "units", "minuend_digit": 12, "subtrahend_digit": 7, "result_digit": 5},
        ),
        (
            "compare_column",
            {"column": "tens", "minuend_digit": 3, "subtrahend_digit": 8, "borrow_needed": True},
        ),
        (
            "borrow",
            {
                "from_column": "hundreds",
                "from_digit_before": 5,
                "from_digit_after": 4,
                "to_column": "tens",
                "to_digit_before": 3,
                "to_digit_after": 13,
            },
        ),
        (
            "subtract_column",
            {"column": "tens", "minuend_digit": 13, "subtrahend_digit": 8, "result_digit": 5},
        ),
        (
            "subtract_column",
            {"column": "hundreds", "minuend_digit": 4, "subtrahend_digit": 1, "result_digit": 3},
        ),
        ("write_final_answer", {"digits": {"hundreds": 3, "tens": 5, "units": 5}, "value": 355}),
    ]
    accepted: list[str] = []
    state = ProblemState(problem=problem_542_187, accepted_step_ids=accepted)
    for step_type, fields in submissions:
        result = verifier.verify_step(state, StudentStep(step_type=step_type, fields=fields))
        assert result.is_valid is True, f"expected valid for {step_type}/{fields}, got {result}"
        assert result.matched_step_id is not None
        accepted.append(result.matched_step_id)
        state = ProblemState(problem=problem_542_187, accepted_step_ids=accepted)
    assert accepted[-1] == "s8_final"


def test_no_borrow_needed_case_does_not_force_a_spurious_borrow(
    verifier: SubtractionBorrowingVerifier,
) -> None:
    """A problem where no column needs borrowing shouldn't have a 'borrow'
    frontier node at all — this fixture-independent check just confirms the
    verifier rejects a gratuitous borrow submission as wrong-step-type-ish
    (no matching candidate) rather than accepting it. Uses a minimal ad hoc
    problem rather than the canonical fixture, since 542-187 always borrows."""
    problem = Problem.model_validate(
        {
            "problem_id": "no-borrow-demo",
            "ncert_ref": {
                "class": 5,
                "chapter": 1,
                "chapter_title": "The Fish Tale",
                "topic": "subtraction_with_borrowing",
            },
            "given": {"minuend": 89, "subtrahend": 45},
            "final_answer": 44,
            "step_graph": [
                {
                    "step_id": "s1",
                    "type": "compare_column",
                    "expected_state": {
                        "column": "units",
                        "minuend_digit": 9,
                        "subtrahend_digit": 5,
                        "borrow_needed": False,
                    },
                    "next": ["s2"],
                },
                {
                    "step_id": "s2",
                    "type": "subtract_column",
                    "expected_state": {
                        "column": "units",
                        "minuend_digit": 9,
                        "subtrahend_digit": 5,
                        "result_digit": 4,
                    },
                    "next": [],
                },
            ],
        }
    )
    state = ProblemState(problem=problem)
    result = verifier.verify_step(
        state,
        StudentStep(
            step_type="borrow",
            fields={
                "from_column": "tens",
                "from_digit_before": 8,
                "from_digit_after": 7,
                "to_column": "units",
                "to_digit_before": 9,
                "to_digit_after": 19,
            },
        ),
    )
    assert result.is_valid is False
    assert result.error_signal is not None
    assert result.error_signal.kind == "wrong_step_type"


def test_non_adjacent_but_valid_match_is_accepted_and_flagged(
    verifier: SubtractionBorrowingVerifier, problem_542_187: Problem
) -> None:
    """Skipping straight to the units-subtraction step after only comparing
    (skipping the borrow submission) exact-matches a real graph node that
    isn't on the current frontier — D11's non-adjacent-but-valid case."""
    state = ProblemState(problem=problem_542_187, accepted_step_ids=["s1_cmp_units"])
    result = verifier.verify_step(
        state,
        StudentStep(
            step_type="subtract_column",
            fields={
                "column": "units",
                "minuend_digit": 12,
                "subtrahend_digit": 7,
                "result_digit": 5,
            },
        ),
    )
    assert result.is_valid is True
    assert result.matched_step_id == "s3_sub_units"
    assert result.confidence == NON_ADJACENT_MATCH_CONFIDENCE
    assert result.error_signal is not None
    assert result.error_signal.note == "non_adjacent_valid_match"


def test_unambiguous_wrong_result_digit_is_rejected(
    verifier: SubtractionBorrowingVerifier, problem_542_187: Problem
) -> None:
    """3 of 4 fields match s3_sub_units exactly; only result_digit is off —
    agreement lands exactly at REJECT_THRESHOLD, the boundary case."""
    state = ProblemState(
        problem=problem_542_187, accepted_step_ids=["s1_cmp_units", "s2_borrow_units"]
    )
    result = verifier.verify_step(
        state,
        StudentStep(
            step_type="subtract_column",
            fields={
                "column": "units",
                "minuend_digit": 12,
                "subtrahend_digit": 7,
                "result_digit": 9,
            },
        ),
    )
    assert result.is_valid is False
    assert result.confidence == pytest.approx(REJECT_THRESHOLD)
    assert result.error_signal is not None
    assert result.error_signal.kind == "field_mismatch"
    assert [d.field for d in result.error_signal.discrepant_fields] == ["result_digit"]
    assert result.error_signal.discrepant_fields[0].expected == 5
    assert result.error_signal.discrepant_fields[0].actual == 9


def test_ambiguous_submission_does_not_interrupt(
    verifier: SubtractionBorrowingVerifier, problem_542_187: Problem
) -> None:
    """Only half the fields agree with any single candidate — too ambiguous
    to confidently call it wrong, so the false-negative bias (D2) kicks in:
    is_valid stays True, but it's logged as a low-confidence passthrough."""
    state = ProblemState(problem=problem_542_187, accepted_step_ids=["s1_cmp_units"])
    result = verifier.verify_step(
        state,
        StudentStep(
            step_type="borrow",
            fields={
                "from_column": "hundreds",
                "from_digit_before": 9,
                "from_digit_after": 8,
                "to_column": "units",
                "to_digit_before": 2,
                "to_digit_after": 12,
            },
        ),
    )
    assert result.is_valid is True
    assert result.confidence < REJECT_THRESHOLD
    assert result.error_signal is not None
    assert result.error_signal.note == "low_confidence_passthrough"


def test_unknown_step_type_is_rejected_regardless_of_confidence_bias(
    verifier: SubtractionBorrowingVerifier, problem_542_187: Problem
) -> None:
    """A structurally nonexistent step type is not an ambiguous math
    judgment — the false-negative bias doesn't apply here."""
    state = ProblemState(problem=problem_542_187)
    result = verifier.verify_step(state, StudentStep(step_type="multiply", fields={}))
    assert result.is_valid is False
    assert result.confidence == 1.0
    assert result.error_signal is not None
    assert result.error_signal.kind == "wrong_step_type"


def test_malformed_input_is_rejected(
    verifier: SubtractionBorrowingVerifier, problem_542_187: Problem
) -> None:
    state = ProblemState(problem=problem_542_187)
    result = verifier.verify_step(
        state,
        StudentStep(
            step_type="borrow",
            fields={
                "from_column": "tens",
                "from_digit_before": "four",  # wrong type, not a real submission
                "from_digit_after": 3,
                "to_column": "units",
                "to_digit_before": 2,
                "to_digit_after": 12,
            },
        ),
    )
    assert result.is_valid is False
    assert result.confidence == 1.0
    assert result.error_signal is not None
    assert result.error_signal.kind == "malformed"


def test_final_answer_matches_and_passes_sympy_cross_check(
    verifier: SubtractionBorrowingVerifier, problem_542_187: Problem
) -> None:
    state = ProblemState(
        problem=problem_542_187,
        accepted_step_ids=[
            "s1_cmp_units",
            "s2_borrow_units",
            "s3_sub_units",
            "s4_cmp_tens",
            "s5_borrow_tens",
            "s6_sub_tens",
            "s7_sub_hundreds",
        ],
    )
    result = verifier.verify_step(
        state,
        StudentStep(
            step_type="write_final_answer",
            fields={"digits": {"hundreds": 3, "tens": 5, "units": 5}, "value": 355},
        ),
    )
    assert result.is_valid is True
    assert result.matched_step_id == "s8_final"
