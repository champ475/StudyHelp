"""Per-step-type typed field models and field-level comparison for unit
conversion (NCERT Ch.14, "How Big? How Heavy?" — length/weight/volume) —
mirrors `decimals/step_checkers.py`'s pattern (ARCHITECTURE.md D21).
"""

from typing import Any, Literal

from pydantic import BaseModel

from studyhelp.schemas.verify import FieldDiscrepancy


class IdentifyConversionFactorFields(BaseModel):
    direction: Literal["x", "/"]
    factor: int


class ConvertUnitsFields(BaseModel):
    value: int


class WriteFinalAnswerFields(BaseModel):
    value: int


STEP_TYPE_FIELD_MODELS: dict[str, type[BaseModel]] = {
    "identify_conversion_factor": IdentifyConversionFactorFields,
    "convert_units": ConvertUnitsFields,
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
    agreement = round(matched / total, 4) if total else 1.0
    return discrepancies, agreement
