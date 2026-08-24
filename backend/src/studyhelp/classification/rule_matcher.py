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


def _b5_reversed_borrow_judgment(correct: _Fields, student: _Fields) -> bool:
    """`compare_column` step: the child compares the two digits correctly
    but applies the borrow-needed test backwards -- deciding a borrow is
    needed exactly when it isn't (minuend >= subtrahend) and vice versa.
    Only fires when the digits actually differ, so there's no ambiguity
    about which direction is "correct"."""
    minuend = _as_int(student, "minuend_digit")
    subtrahend = _as_int(student, "subtrahend_digit")
    student_borrow_needed = student.get("borrow_needed")
    correct_borrow_needed = correct.get("borrow_needed")
    if minuend is None or subtrahend is None or minuend == subtrahend:
        return False
    if not isinstance(student_borrow_needed, bool) or not isinstance(correct_borrow_needed, bool):
        return False
    reversed_judgment = subtrahend < minuend
    return bool(student_borrow_needed == reversed_judgment and student_borrow_needed != correct_borrow_needed)


def _b6_digit_order_reversed(correct: _Fields, student: _Fields) -> bool:
    """`write_final_answer` step: the per-column result digits were each
    found correctly, but assembled in solving order (units first) rather
    than place-value order (highest place first) -- the student's `value`
    is the correct value's decimal digit string reversed. `write_final_answer`
    is a step_type shared across several topics' schemas that all differ in
    field shape, and `match_buggy_rule` dispatches on step_type alone (no
    topic parameter) -- so this is gated on the `digits` field, which only
    subtraction_borrowing's write_final_answer schema has, to avoid firing
    on another topic's plain `{value: int}` final-answer submission.
    Also guarded to multi-digit, all-distinct-digit correct values so the
    reversal is unambiguous rather than a coincidental match."""
    if "digits" not in correct or "digits" not in student:
        return False
    correct_value = _as_int(correct, "value")
    student_value = _as_int(student, "value")
    if correct_value is None or student_value is None or correct_value < 10:
        return False
    digits = str(correct_value)
    if len(set(digits)) != len(digits):
        return False
    reversed_value = int(digits[::-1])
    return bool(student_value == reversed_value and student_value != correct_value)


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


def _ap1_formula_confusion(correct: _Fields, student: _Fields) -> bool:
    """Area/perimeter formula confusion: on an area problem, the student's
    result matches what the PERIMETER formula would give from their own
    submitted length/width (2*(l+w)) rather than the area formula
    (l*w). Checkable purely from the student's own field pair — no
    cross-step context needed."""
    length = _as_int(student, "length")
    width = _as_int(student, "width")
    result = _as_int(student, "result")
    if length is None or width is None or result is None:
        return False
    naive_perimeter = 2 * (length + width)
    return bool(result == naive_perimeter and result != length * width)


def _ap2_forgot_times_two(correct: _Fields, student: _Fields) -> bool:
    """On a perimeter problem, the student adds length and width once and
    stops, forgetting to double for all four sides."""
    length = _as_int(student, "length")
    width = _as_int(student, "width")
    result = _as_int(student, "result")
    if length is None or width is None or result is None:
        return False
    return bool(result == length + width and result != 2 * (length + width))


def _ap3_area_as_sum(correct: _Fields, student: _Fields) -> bool:
    """On an area problem, the student adds length and width instead of
    multiplying them -- reaching for addition (the more familiar
    operation) rather than the tiling/multiplication idea area actually
    needs. Distinct from AP1 (which uses the full perimeter formula
    2*(l+w)) -- this is the simpler, un-doubled sum."""
    length = _as_int(student, "length")
    width = _as_int(student, "width")
    result = _as_int(student, "result")
    if length is None or width is None or result is None:
        return False
    return bool(result == length + width and result != length * width)


def _ap5_perimeter_uses_area_formula(correct: _Fields, student: _Fields) -> bool:
    """On a perimeter problem, the student multiplies length by width
    (the area formula) instead of adding and doubling all four sides --
    the mirror image of AP1's formula confusion."""
    length = _as_int(student, "length")
    width = _as_int(student, "width")
    result = _as_int(student, "result")
    if length is None or width is None or result is None:
        return False
    return bool(result == length * width and result != 2 * (length + width))


def _md1_forgot_carry(correct: _Fields, student: _Fields) -> bool:
    """Multiplication `multiply_tens` step: the correct carry from the
    units column was nonzero, but the student states carry_in=0 and
    multiplies the tens digit alone, ignoring the carry entirely."""
    correct_carry = _as_int(correct, "carry_in")
    if not correct_carry:
        return False
    digit = _as_int(student, "digit")
    multiplier = _as_int(student, "multiplier")
    carry_in = _as_int(student, "carry_in")
    product = _as_int(student, "product")
    if digit is None or multiplier is None or carry_in is None or product is None:
        return False
    return bool(carry_in == 0 and product == digit * multiplier)


def _md2_misplaced_remainder(correct: _Fields, student: _Fields) -> bool:
    """Division `divide_units` step: the correct dividend_group combines
    the tens remainder with the units digit (>= 10), but the student uses
    just the bare units digit alone, dropping the remainder from the
    previous column."""
    correct_group = _as_int(correct, "dividend_group")
    student_group = _as_int(student, "dividend_group")
    if correct_group is None or student_group is None or correct_group < 10:
        return False
    return bool(student_group == correct_group % 10 and student_group != correct_group)


def _md4_divide_tens_drops_remainder(correct: _Fields, student: _Fields) -> bool:
    """Division `divide_tens` step: the quotient digit is right, but the
    student reports remainder=0 when the true remainder is nonzero --
    the leftover amount is simply dropped instead of tracked forward to
    combine with the next digit."""
    correct_remainder = _as_int(correct, "remainder")
    if not correct_remainder:
        return False
    student_quotient = _as_int(student, "quotient_digit")
    correct_quotient = _as_int(correct, "quotient_digit")
    student_remainder = _as_int(student, "remainder")
    if student_quotient is None or correct_quotient is None or student_remainder is None:
        return False
    return bool(student_quotient == correct_quotient and student_remainder == 0)


def _me1_wrong_direction(correct: _Fields, student: _Fields) -> bool:
    """Unit conversion `identify_conversion_factor` step: the student picks
    the right factor but the wrong direction (multiplies when the correct
    move was to divide, or vice versa)."""
    correct_direction = correct.get("direction")
    student_direction = student.get("direction")
    correct_factor = _as_int(correct, "factor")
    student_factor = _as_int(student, "factor")
    if correct_direction is None or student_direction is None:
        return False
    if correct_factor is None or student_factor is None:
        return False
    return bool(student_direction != correct_direction and student_factor == correct_factor)


def _me2_wrong_factor(correct: _Fields, student: _Fields) -> bool:
    """Unit conversion `identify_conversion_factor` step: the student has
    the right direction but reaches for a different power-of-ten factor
    (10/100/1000 confusion) than the one this unit pair actually uses."""
    correct_direction = correct.get("direction")
    student_direction = student.get("direction")
    correct_factor = _as_int(correct, "factor")
    student_factor = _as_int(student, "factor")
    if correct_direction is None or student_direction is None:
        return False
    if correct_factor is None or student_factor is None:
        return False
    return bool(
        student_direction == correct_direction
        and student_factor != correct_factor
        and student_factor in (10, 100, 1000)
    )


def _sa1_acute_obtuse_swap(correct: _Fields, student: _Fields) -> bool:
    """Shapes and Angles `answer` step: the student swaps acute and obtuse
    — names the opposite of the two most commonly confused angle types."""
    correct_answer = correct.get("answer")
    student_answer = student.get("answer")
    if not isinstance(correct_answer, str) or not isinstance(student_answer, str):
        return False
    swap = {"acute": "obtuse", "obtuse": "acute"}
    return bool(swap.get(correct_answer.strip().lower()) == student_answer.strip().lower())


def _sa2_right_straight_swap(correct: _Fields, student: _Fields) -> bool:
    """Shapes and Angles `answer` step: the student swaps right and
    straight -- names the opposite of the two easily-confused named
    angles at 90 degrees and 180 degrees."""
    correct_answer = correct.get("answer")
    student_answer = student.get("answer")
    if not isinstance(correct_answer, str) or not isinstance(student_answer, str):
        return False
    swap = {"right": "straight", "straight": "right"}
    return bool(swap.get(correct_answer.strip().lower()) == student_answer.strip().lower())


def _sym1_assumes_nonzero_symmetry(correct: _Fields, student: _Fields) -> bool:
    """Symmetry `answer` step: the correct line-of-symmetry count is 0
    (an asymmetric shape/letter), but the student assumes every shape has
    at least one line of symmetry and answers 1."""
    correct_answer = correct.get("answer")
    student_answer = student.get("answer")
    if not isinstance(correct_answer, str) or not isinstance(student_answer, str):
        return False
    return bool(correct_answer.strip().lower() == "0" and student_answer.strip().lower() == "1")


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


def _f6_lcm_hcf_list_shifted_by_one(correct: _Fields, student: _Fields) -> bool:
    """LCM/HCF `find_common_values` step: the student's list is the correct
    list shifted by one position — they skip the smallest common
    factor/multiple and tack on one extra at the end, as if counting
    started one step too late (e.g. correct [12,24,36] -> student
    [24,36,48])."""
    correct_values = correct.get("values")
    student_values = student.get("values")
    if not isinstance(correct_values, list) or not isinstance(student_values, list):
        return False
    if len(correct_values) < 2 or len(student_values) != len(correct_values):
        return False
    step = correct_values[1] - correct_values[0]
    expected_shifted = correct_values[1:] + [correct_values[-1] + step]
    return bool(student_values == expected_shifted and student_values != correct_values)


def _f7_lcm_hcf_extra_non_common_value(correct: _Fields, student: _Fields) -> bool:
    """LCM/HCF `find_common_values` step: the student's list contains every
    correct value plus exactly one extra spurious one — typically a value
    that divides (or is a multiple of) only ONE of the two given numbers,
    mistaken for a value common to both."""
    correct_values = correct.get("values")
    student_values = student.get("values")
    if not isinstance(correct_values, list) or not isinstance(student_values, list):
        return False
    if len(student_values) != len(correct_values) + 1:
        return False
    return bool(set(correct_values).issubset(set(student_values)) and student_values != correct_values)


def _dec1_tenths_written_as_hundredths(correct: _Fields, student: _Fields) -> bool:
    """Decimals `align_place_value` step: a number whose true decimal
    representation has one significant digit after the point (a multiple
    of 10 in hundredths, e.g. 3.40) gets padded wrong — the tenths digit is
    written straight after the decimal point (in the hundredths column,
    e.g. "3.04") instead of before it ("3.40"), on either the a or b
    field."""

    def _shifted(correct_value: object) -> int | None:
        if not isinstance(correct_value, int) or correct_value % 10 != 0:
            return None
        whole, tenths_digit = divmod(correct_value, 100)
        tenths_digit //= 10
        return whole * 100 + tenths_digit

    for key in ("a_hundredths", "b_hundredths"):
        shifted = _shifted(correct.get(key))
        if shifted is not None and student.get(key) == shifted and student.get(key) != correct.get(key):
            return True
    return False


def _dec2_decimal_point_shifted(correct: _Fields, student: _Fields) -> bool:
    """Decimals `compute_result` step: the digits are combined correctly in
    magnitude, but the decimal point lands one place too far right — the
    student's result is exactly ten times the correct one."""
    correct_result = _as_int(correct, "result_hundredths")
    student_result = _as_int(student, "result_hundredths")
    if correct_result is None or student_result is None or correct_result == 0:
        return False
    return bool(student_result == correct_result * 10)


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
    _MatcherSpec(
        "lcm_hcf.list_shifted_by_one",
        "LH1-list-shifted-by-one",
        "find_common_values",
        _f6_lcm_hcf_list_shifted_by_one,
    ),
    _MatcherSpec(
        "lcm_hcf.extra_non_common_value",
        "LH2-extra-non-common-value",
        "find_common_values",
        _f7_lcm_hcf_extra_non_common_value,
    ),
    _MatcherSpec(
        "decimals.tenths_written_as_hundredths",
        "DEC1-tenths-written-as-hundredths",
        "align_place_value",
        _dec1_tenths_written_as_hundredths,
    ),
    _MatcherSpec(
        "decimals.decimal_point_shifted",
        "DEC2-decimal-point-shifted",
        "compute_result",
        _dec2_decimal_point_shifted,
    ),
    _MatcherSpec(
        "area_perimeter.formula_confusion",
        "AP1-formula-confusion",
        "compute_area",
        _ap1_formula_confusion,
    ),
    _MatcherSpec(
        "area_perimeter.forgot_times_two",
        "AP2-forgot-times-two",
        "compute_perimeter",
        _ap2_forgot_times_two,
    ),
    _MatcherSpec(
        "multiplication_division.forgot_carry",
        "MD1-forgot-carry",
        "multiply_tens",
        _md1_forgot_carry,
    ),
    _MatcherSpec(
        "multiplication_division.misplaced_remainder",
        "MD2-misplaced-remainder",
        "divide_units",
        _md2_misplaced_remainder,
    ),
    _MatcherSpec(
        "measurement.wrong_direction",
        "ME1-wrong-direction",
        "identify_conversion_factor",
        _me1_wrong_direction,
    ),
    _MatcherSpec(
        "measurement.wrong_factor",
        "ME2-wrong-factor",
        "identify_conversion_factor",
        _me2_wrong_factor,
    ),
    _MatcherSpec(
        "shapes_angles.acute_obtuse_swap",
        "SA1-acute-obtuse-swap",
        "shapes_angles_answer",
        _sa1_acute_obtuse_swap,
    ),
    _MatcherSpec(
        "symmetry.assumes_nonzero_symmetry",
        "SYM1-assumes-nonzero-symmetry",
        "symmetry_answer",
        _sym1_assumes_nonzero_symmetry,
    ),
    _MatcherSpec(
        "subtraction_borrowing.reversed_borrow_judgment",
        "B5-reversed-borrow-judgment",
        "compare_column",
        _b5_reversed_borrow_judgment,
    ),
    _MatcherSpec(
        "subtraction_borrowing.digit_order_reversed",
        "B6-digit-order-reversed",
        "write_final_answer",
        _b6_digit_order_reversed,
    ),
    _MatcherSpec(
        "area_perimeter.area_as_sum",
        "AP3-area-as-sum",
        "compute_area",
        _ap3_area_as_sum,
    ),
    _MatcherSpec(
        "area_perimeter.perimeter_uses_area_formula",
        "AP5-perimeter-uses-area-formula",
        "compute_perimeter",
        _ap5_perimeter_uses_area_formula,
    ),
    _MatcherSpec(
        "multiplication_division.divide_tens_drops_remainder",
        "MD4-divide-tens-drops-remainder",
        "divide_tens",
        _md4_divide_tens_drops_remainder,
    ),
    _MatcherSpec(
        "shapes_angles.right_straight_swap",
        "SA2-right-straight-swap",
        "shapes_angles_answer",
        _sa2_right_straight_swap,
    ),
    _MatcherSpec(
        "decimals.decimal_point_shifted_final",
        "DEC4-decimal-point-shifted-final",
        "write_final_answer",
        _dec2_decimal_point_shifted,
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
