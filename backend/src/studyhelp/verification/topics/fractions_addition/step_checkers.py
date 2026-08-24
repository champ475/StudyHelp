"""Per-step-type typed field models and field-level comparison for
fractions (NCERT Ch.4, "Parts and Wholes") — mirrors
`subtraction_borrowing/step_checkers.py`'s pattern (ARCHITECTURE.md D21).

Started as addition-only (hence the package's `fractions_addition` name,
kept as-is rather than renamed across the whole codebase for a purely
cosmetic gain — see ARCHITECTURE.md D45); expanded here to also cover
subtraction and comparison of like/unlike-denominator fractions, the rest
of NCERT Ch.4's actual scope.
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


class CompareFractionsFields(BaseModel):
    """Terminal step for a comparison problem — the student states the
    comparison directly using the two *original* fractions (e.g.
    "1/4 < 1/6"), not the rewritten common-denominator pair. Comparison
    problems are a deliberately shorter (1-step) DAG within this topic —
    not every problem in a chapter needs the same procedural depth."""

    left_num: int
    left_den: int
    op: Literal["<", ">", "="]
    right_num: int
    right_den: int


STEP_TYPE_FIELD_MODELS: dict[str, type[BaseModel]] = {
    "rewrite_common_denominator": RewriteCommonDenominatorFields,
    "add_numerators": AddNumeratorsFields,
    "subtract_numerators": AddNumeratorsFields,  # identical num/den shape
    "simplify_fraction": SimplifyFractionFields,
    "write_final_answer": WriteFinalAnswerFields,
    "compare_fractions": CompareFractionsFields,
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
    agreement = round(matched / total, 4) if total else 1.0
    return discrepancies, agreement
