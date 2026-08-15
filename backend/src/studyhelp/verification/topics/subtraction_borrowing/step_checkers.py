"""Per-step-type typed field models and field-level comparison for
subtraction-with-borrowing. These types are intentionally topic-local, not
part of the shared `schemas/` package (ARCHITECTURE.md D21) — a future
topic defines its own fields next to its own checkers.
"""

from typing import Any, Literal

from pydantic import BaseModel

from studyhelp.schemas.verify import FieldDiscrepancy

Column = Literal["units", "tens", "hundreds", "thousands", "ten_thousands", "lakhs"]


class CompareColumnFields(BaseModel):
    column: Column
    minuend_digit: int
    subtrahend_digit: int
    borrow_needed: bool


class BorrowFields(BaseModel):
    from_column: Column
    from_digit_before: int
    from_digit_after: int
    to_column: Column
    to_digit_before: int
    to_digit_after: int
    combined_result_digit: int | None = None
    """Present only on alt-path nodes where a student combines borrow +
    subtract into a single widget action (see the canonical fixture's
    `s2b_borrow_and_subtract_units` node)."""


class SubtractColumnFields(BaseModel):
    column: Column
    minuend_digit: int
    subtrahend_digit: int
    result_digit: int


class WriteFinalAnswerFields(BaseModel):
    digits: dict[Column, int]
    value: int


STEP_TYPE_FIELD_MODELS: dict[str, type[BaseModel]] = {
    "compare_column": CompareColumnFields,
    "borrow": BorrowFields,
    "subtract_column": SubtractColumnFields,
    "write_final_answer": WriteFinalAnswerFields,
}


def compare_to_expected(
    expected_state: dict[str, Any], student_fields: dict[str, Any]
) -> tuple[list[FieldDiscrepancy], float]:
    """Field-level comparison against one candidate node's `expected_state`.
    Returns the discrepant fields and an agreement ratio (matching / total)
    — the raw input to the verifier's confidence scoring."""
    discrepancies: list[FieldDiscrepancy] = []
    matched = 0
    for field, expected_value in expected_state.items():
        actual_value = student_fields.get(field)
        if actual_value == expected_value:
            matched += 1
        else:
            discrepancies.append(
                FieldDiscrepancy(field=field, expected=expected_value, actual=actual_value)
            )
    total = len(expected_state)
    agreement = matched / total if total else 1.0
    return discrepancies, agreement
