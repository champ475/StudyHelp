"""Buggy-rule matcher: given a (correct_step, student_step) field pair,
tries each registered buggy-rule signature deterministically and returns
the first match. This is the cheap, deterministic, explainable first layer
that runs before any LLM classification call (ARCHITECTURE.md D4) — only
when nothing here matches does classification fall back to the closed-set
LLM path (classifier.py).

Each matcher here is a direct, testable Python predicate — not a generic
formula-string interpreter (no `eval()` of the seeded `signature_matcher`
JSON). The DB/fixture-seeded `signature_matcher` stays the reviewable,
citable declarative artifact (technical_architecture.md §4); this module
is the actual executable implementation of those same four patterns,
scoped specifically to what's checkable from a single (correct, student)
step-field pair without needing broader graph context.
"""

from collections.abc import Callable
from dataclasses import dataclass
from math import gcd
from typing import Any

import sympy

_Fields = dict[str, Any]
_Matcher = Callable[[_Fields, _Fields], bool]


def _as_int(fields: _Fields, key: str) -> int | None:
    value = fields.get(key)
    return value if isinstance(value, int) else None


def _b1_smaller_from_larger(correct: _Fields, student: _Fields) -> bool:
    """DEBUGGY's headline bug: subtracts the smaller digit from the larger
    one regardless of which number it belongs to, skipping the borrow.
    Signature: the student's own minuend digit is smaller than the
    subtrahend digit (i.e. they never borrowed), and their result is the
    reversed difference rather than a borrow-corrected one."""
    minuend = _as_int(student, "minuend_digit")
    subtrahend = _as_int(student, "subtrahend_digit")
    result = _as_int(student, "result_digit")
    if minuend is None or subtrahend is None or result is None:
        return False
    return bool(
        minuend < subtrahend
        and result == subtrahend - minuend
        and result != correct.get("result_digit")
    )


def _b2_no_decrement_after_borrow(correct: _Fields, student: _Fields) -> bool:
    """The receiving column correctly gets +10, but the lending column is
    never decremented — borrows without paying it back."""
    to_before = _as_int(student, "to_digit_before")
    to_after = _as_int(student, "to_digit_after")
    from_before = _as_int(student, "from_digit_before")
    from_after = _as_int(student, "from_digit_after")
    if to_before is None or to_after is None or from_before is None or from_after is None:
        return False
    return bool(to_after == to_before + 10 and from_after == from_before and student != correct)


def _b3_borrow_across_zero(correct: _Fields, student: _Fields) -> bool:
    """The correct borrow targets a zero column (has to cascade past it) —
    the student either doesn't decrement the ultimate lender, or gives the
    zero column 9 instead of the correct +10. Checked *before* B2 in match
    order since B3 is the more specific pattern (zero-column precondition);
    an example satisfying both should be attributed to B3."""
    if correct.get("to_digit_before") != 0:
        return False
    lender_not_decremented = student.get("from_digit_after") == student.get("from_digit_before")
    zero_column_mishandled = student.get("to_digit_after") == 9
    return bool((lender_not_decremented or zero_column_mishandled) and student != correct)


def _b4_stale_borrow_digit(correct: _Fields, student: _Fields) -> bool:
    """A column that already lent once (decremented) is later itself
    borrowed from again; the student re-uses the pre-decrement digit
    instead of the already-decremented value — consistently off by exactly
    the missed decrement (+1 on both the minuend digit used and the
    result)."""
    required = {"minuend_digit", "subtrahend_digit", "result_digit"}
    if not required.issubset(correct) or not required.issubset(student):
        return False
    correct_minuend = _as_int(correct, "minuend_digit")
    correct_result = _as_int(correct, "result_digit")
    if correct_minuend is None or correct_result is None:
        return False
    return bool(
        student["subtrahend_digit"] == correct["subtrahend_digit"]
        and student["minuend_digit"] == correct_minuend + 1
        and student["result_digit"] == correct_result + 1
    )


def _f1_no_common_denominator(correct: _Fields, student: _Fields) -> bool:
    """Classic Class 5 fraction-addition misconception: the student never
    converts to a common denominator at all — the two denominators they
    submit still differ from each other (Ni & Zhou 2005; "whole-number
    bias" literature)."""
    left_den = _as_int(student, "left_den")
    right_den = _as_int(student, "right_den")
    if left_den is None or right_den is None:
        return False
    return bool(left_den != right_den and student != correct)


def _f2_add_across(correct: _Fields, student: _Fields) -> bool:
    """"Freshman's dream": adds numerators AND denominators straight
    across instead of keeping the (already-equal) common denominator —
    the student's denominator is exactly double the correct one, having
    added the common denominator to itself."""
    correct_num = _as_int(correct, "num")
    correct_den = _as_int(correct, "den")
    student_num = _as_int(student, "num")
    student_den = _as_int(student, "den")
    if correct_num is None or correct_den is None or student_num is None or student_den is None:
        return False
    return bool(student_num == correct_num and student_den == correct_den * 2)


def _f4_subtract_across(correct: _Fields, student: _Fields) -> bool:
    """Same "freshman's dream" overgeneralization as F2, on a
    `subtract_numerators` step: the student combines (adds) the
    denominators together instead of keeping the shared common
    denominator, regardless of the operation being subtraction."""
    correct_num = _as_int(correct, "num")
    correct_den = _as_int(correct, "den")
    student_num = _as_int(student, "num")
    student_den = _as_int(student, "den")
    if correct_num is None or correct_den is None or student_num is None or student_den is None:
        return False
    return bool(student_num == correct_num and student_den == correct_den * 2)


def _f5_compares_numerators_only(correct: _Fields, student: _Fields) -> bool:
    """Whole-number bias applied to comparison: the student compares the
    two original numerators directly (bigger numerator = bigger fraction)
    and ignores that the denominators differ, landing on the comparison
    that would be correct only if the denominators matched."""
    left_num = _as_int(student, "left_num")
    right_num = _as_int(student, "right_num")
    correct_op = correct.get("op")
    student_op = student.get("op")
    if left_num is None or right_num is None or correct_op is None or student_op is None:
        return False
    if student_op == correct_op:
        return False
    naive_op = "<" if left_num < right_num else ">" if left_num > right_num else "="
    return bool(student_op == naive_op)


def _f3_forgot_to_simplify(correct: _Fields, student: _Fields) -> bool:
    """The value is right but the student re-submits the unsimplified
    fraction as if it were already in lowest terms — the concept of
    "simplify" (find and divide out the common factor) hasn't been
    internalized, only the arithmetic that produced the sum."""
    correct_num = _as_int(correct, "num")
    correct_den = _as_int(correct, "den")
    student_num = _as_int(student, "num")
    student_den = _as_int(student, "den")
    if correct_num is None or correct_den is None or student_num is None or student_den is None:
        return False
    if student_den == 0:
        return False
    equal_value = sympy.Eq(sympy.Rational(student_num, student_den), sympy.Rational(correct_num, correct_den))
    not_reduced = gcd(student_num, student_den) != 1
    return bool(equal_value) and not_reduced


@dataclass(frozen=True)
class _MatcherSpec:
    buggy_rule_id: str
    bug_code: str
    applies_to: str
    matcher: _Matcher


_MATCHERS: list[_MatcherSpec] = [
    _MatcherSpec(
        "subtraction_borrowing.stale_borrow_digit",
        "B4-stale-borrow-digit",
        "subtract_column",
        _b4_stale_borrow_digit,
    ),
    _MatcherSpec(
        "subtraction_borrowing.smaller_from_larger",
        "B1-smaller-from-larger",
        "subtract_column",
        _b1_smaller_from_larger,
    ),
    _MatcherSpec(
        "subtraction_borrowing.borrow_across_zero",
        "B3-borrow-across-zero",
        "borrow",
        _b3_borrow_across_zero,
    ),
    _MatcherSpec(
        "subtraction_borrowing.no_decrement_after_borrow",
        "B2-no-decrement-after-borrow",
        "borrow",
        _b2_no_decrement_after_borrow,
    ),
    _MatcherSpec(
        "fractions_addition.no_common_denominator",
        "F1-no-common-denominator",
        "rewrite_common_denominator",
        _f1_no_common_denominator,
    ),
    _MatcherSpec(
        "fractions_addition.add_across",
        "F2-add-across",
        "add_numerators",
        _f2_add_across,
    ),
    _MatcherSpec(
        "fractions_addition.forgot_to_simplify",
        "F3-forgot-to-simplify",
        "simplify_fraction",
        _f3_forgot_to_simplify,
    ),
    _MatcherSpec(
        "fractions_addition.subtract_across",
        "F4-subtract-across",
        "subtract_numerators",
        _f4_subtract_across,
    ),
    _MatcherSpec(
        "fractions_addition.compares_numerators_only",
        "F5-compares-numerators-only",
        "compare_fractions",
        _f5_compares_numerators_only,
    ),
]


@dataclass(frozen=True)
class RuleMatch:
    buggy_rule_id: str
    bug_code: str


def match_buggy_rule(
    step_type: str, correct_fields: _Fields, student_fields: _Fields
) -> RuleMatch | None:
    """First match wins, deterministically. Returns `None` if no known
    buggy-rule signature matches — the caller falls back to the closed-set
    LLM classifier."""
    for spec in _MATCHERS:
        if spec.applies_to != step_type:
            continue
        if spec.matcher(correct_fields, student_fields):
            return RuleMatch(buggy_rule_id=spec.buggy_rule_id, bug_code=spec.bug_code)
    return None
