"""Per-step-type typed field models and field-level comparison for
fraction addition (like/unlike denominators) — mirrors
`subtraction_borrowing/step_checkers.py`'s pattern (ARCHITECTURE.md D21).
"""

from typing import Any, Literal

from pydantic import BaseModel

from studyhelp.schemas.verify import FieldDiscrepancy


class RewriteCommonDenominatorFields(BaseModel):
    left_num: int
    left_den: int
    op: Literal["+", "-"]
    right_num: int
    right_den: int


class AddNumeratorsFields(BaseModel):
    num: int
    den: int


class SimplifyFractionFields(BaseModel):
    num: int
    den: int


class WriteFinalAnswerFields(BaseModel):
    num: int
    den: int


STEP_TYPE_FIELD_MODELS: dict[str, type[BaseModel]] = {
    "rewrite_common_denominator": RewriteCommonDenominatorFields,
    "add_numerators": AddNumeratorsFields,
    "simplify_fraction": SimplifyFractionFields,
    "write_final_answer": WriteFinalAnswerFields,
}


def compare_to_expected(
    expected_state: dict[str, Any], student_fields: dict[str, Any]
) -> tuple[list[FieldDiscrepancy], float]:
    """Field-level comparison against one candidate node's `expected_state`
    — identical shape to the subtraction topic's checker so the verifier's
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
