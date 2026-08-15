"""Per-step-type typed field models and field-level comparison for
decimals (NCERT Ch.10, "Tenths and Hundredths") — mirrors
`fractions_addition/step_checkers.py`'s pattern (ARCHITECTURE.md D21).
"""

from typing import Any

from pydantic import BaseModel

from studyhelp.schemas.verify import FieldDiscrepancy


class AlignPlaceValueFields(BaseModel):
    a_hundredths: int
    b_hundredths: int


class ComputeResultFields(BaseModel):
    result_hundredths: int


class WriteFinalAnswerFields(BaseModel):
    result_hundredths: int


STEP_TYPE_FIELD_MODELS: dict[str, type[BaseModel]] = {
    "align_place_value": AlignPlaceValueFields,
    "compute_result": ComputeResultFields,
    "write_final_answer": WriteFinalAnswerFields,
}


def compare_to_expected(
    expected_state: dict[str, Any], student_fields: dict[str, Any]
) -> tuple[list[FieldDiscrepancy], float]:
    """Field-level comparison against one candidate node's `expected_state`
    — identical shape to the other topics' checkers so the verifier's
    exact/near-match resolution logic can stay structurally the same."""
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
