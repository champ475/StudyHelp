"""Per-step-type typed field models and field-level comparison for
multiplication/division (NCERT Ch.13, "Ways to Multiply and Divide") —
mirrors `decimals/step_checkers.py`'s pattern (ARCHITECTURE.md D21). Every
seeded problem is either a 2-digit x 1-digit multiplication or a 2-digit /
1-digit exact (no-remainder) division — keeps a uniform 3-step DAG depth
across the whole topic rather than branching by digit count.
"""

from typing import Any

from pydantic import BaseModel

from studyhelp.schemas.verify import FieldDiscrepancy


class MultiplyUnitsFields(BaseModel):
    digit: int
    multiplier: int
    product: int


class MultiplyTensFields(BaseModel):
    digit: int
    multiplier: int
    carry_in: int
    product: int


class DivideTensFields(BaseModel):
    dividend_group: int
    divisor: int
    quotient_digit: int
    remainder: int


class DivideUnitsFields(BaseModel):
    dividend_group: int
    divisor: int
    quotient_digit: int
    remainder: int


class WriteFinalAnswerFields(BaseModel):
    value: int


STEP_TYPE_FIELD_MODELS: dict[str, type[BaseModel]] = {
    "multiply_units": MultiplyUnitsFields,
    "multiply_tens": MultiplyTensFields,
    "divide_tens": DivideTensFields,
    "divide_units": DivideUnitsFields,
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
