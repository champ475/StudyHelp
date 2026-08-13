"""sympy's role here is deliberately narrow (ARCHITECTURE.md D23): an
independent arithmetic cross-check that doesn't trust the step-graph walk
alone, not the source of procedural correctness (that's the graph/field
matching in `verifier.py` and `step_checkers.py`). Whether a borrow was
needed *at this point in the procedure*, or whether the student borrowed
from the right column, is not a question sympy answers — those are DAG
position and field-matching concerns.
"""

import sympy


def check_final_identity(minuend: int, subtrahend: int, candidate_answer: int) -> bool:
    """Cross-checks a `write_final_answer` step's value against the raw
    arithmetic identity, independent of whatever the step graph claims."""
    return bool(
        sympy.Eq(
            sympy.Integer(minuend) - sympy.Integer(subtrahend), sympy.Integer(candidate_answer)
        )
    )


def check_borrow_arithmetic(
    from_digit_before: int, from_digit_after: int, to_digit_before: int, to_digit_after: int
) -> bool:
    """Used at problem-authoring/seed-validation time (not per-submission —
    the graph's `expected_state` already encodes the right values) to catch
    an internally inconsistent problem fixture before it's ever served."""
    lender_correct = sympy.Eq(sympy.Integer(from_digit_after), sympy.Integer(from_digit_before) - 1)
    receiver_correct = sympy.Eq(sympy.Integer(to_digit_after), sympy.Integer(to_digit_before) + 10)
    return bool(lender_correct) and bool(receiver_correct)


def check_subtract_arithmetic(minuend_digit: int, subtrahend_digit: int, result_digit: int) -> bool:
    """Same authoring-time-validation role as `check_borrow_arithmetic`."""
    return bool(
        sympy.Eq(
            sympy.Integer(result_digit),
            sympy.Integer(minuend_digit) - sympy.Integer(subtrahend_digit),
        )
    )
