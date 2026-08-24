"""Each matcher must match its own seeded example_pair (closes the loop
with the Phase 1 buggy_rule_library fixtures) and must NOT match any of
the other three bugs' example pairs — the cross-matrix is what actually
proves the signatures are distinguishing, not just individually plausible.
"""

import pytest

from studyhelp.classification.rule_matcher import match_buggy_rule
from studyhelp.seed.loader import load_buggy_rules

RULES = {rule.id: rule for rule in load_buggy_rules()}


@pytest.mark.parametrize("buggy_rule_id", list(RULES.keys()))
def test_matcher_matches_its_own_example_pair(buggy_rule_id: str) -> None:
    rule = RULES[buggy_rule_id]
    match = match_buggy_rule(
        rule.example_pair.correct_step.step_type,
        rule.example_pair.correct_step.fields,
        rule.example_pair.student_step.fields,
    )
    assert match is not None, f"{buggy_rule_id}'s own example_pair should match its rule"
    assert match.buggy_rule_id == buggy_rule_id


@pytest.mark.parametrize("buggy_rule_id", list(RULES.keys()))
def test_matcher_does_not_match_other_bugs_examples(buggy_rule_id: str) -> None:
    """Cross-matrix: run every OTHER bug's example pair through
    match_buggy_rule and confirm none of them get attributed to
    `buggy_rule_id`'s pattern by coincidence."""
    for other_id, other_rule in RULES.items():
        if other_id == buggy_rule_id:
            continue
        match = match_buggy_rule(
            other_rule.example_pair.correct_step.step_type,
            other_rule.example_pair.correct_step.fields,
            other_rule.example_pair.student_step.fields,
        )
        assert match is None or match.buggy_rule_id != buggy_rule_id, (
            f"{other_id}'s example incorrectly matched {buggy_rule_id}'s pattern"
        )


def test_no_match_on_a_correct_submission() -> None:
    correct_fields = {
        "column": "units",
        "minuend_digit": 12,
        "subtrahend_digit": 5,
        "result_digit": 7,
    }
    assert match_buggy_rule("subtract_column", correct_fields, dict(correct_fields)) is None


def test_no_match_for_unrelated_step_type() -> None:
    assert match_buggy_rule("compare_column", {}, {}) is None


def test_every_example_pair_is_attributed_to_exactly_its_own_rule() -> None:
    """Belt-and-suspenders: each example, run through match_buggy_rule
    once, resolves to exactly the rule it was seeded for — no silent
    misattribution to a different bug."""
    for buggy_rule_id, rule in RULES.items():
        match = match_buggy_rule(
            rule.example_pair.correct_step.step_type,
            rule.example_pair.correct_step.fields,
            rule.example_pair.student_step.fields,
        )
        assert match is not None
        assert match.buggy_rule_id == buggy_rule_id
        assert match.bug_code == rule.bug_code


# --- New matcher functions (misconception-bank expansion) -----------------
# These aren't backed by a buggy_rule_library fixture (that library is out
# of scope for this expansion), so they're exercised directly here rather
# than through the RULES-parametrized tests above: one correct+buggy pair
# that should trigger a match, and one case that should not.


def test_b5_reversed_borrow_judgment() -> None:
    correct = {"column": "units", "minuend_digit": 7, "subtrahend_digit": 3, "borrow_needed": False}
    buggy_student = {"column": "units", "minuend_digit": 7, "subtrahend_digit": 3, "borrow_needed": True}
    match = match_buggy_rule("compare_column", correct, buggy_student)
    assert match is not None
    assert match.buggy_rule_id == "subtraction_borrowing.reversed_borrow_judgment"

    correct_student = {"column": "units", "minuend_digit": 7, "subtrahend_digit": 3, "borrow_needed": False}
    assert match_buggy_rule("compare_column", correct, correct_student) is None

    # Equal digits: no ambiguity to reverse, should never match.
    tied = {"column": "units", "minuend_digit": 5, "subtrahend_digit": 5, "borrow_needed": False}
    assert match_buggy_rule("compare_column", tied, tied) is None


def test_b6_digit_order_reversed() -> None:
    correct = {"digits": {"hundreds": 3, "tens": 5, "units": 2}, "value": 352}
    buggy_student = {"digits": {"hundreds": 2, "tens": 5, "units": 3}, "value": 253}
    match = match_buggy_rule("write_final_answer", correct, buggy_student)
    assert match is not None
    assert match.buggy_rule_id == "subtraction_borrowing.digit_order_reversed"

    correct_student = {"digits": {"hundreds": 3, "tens": 5, "units": 2}, "value": 352}
    assert match_buggy_rule("write_final_answer", correct, correct_student) is None

    # Cross-topic guard: `write_final_answer` is shared by several topics
    # whose schema is just {"value": int} with no `digits` field (e.g.
    # area_perimeter, lcm_hcf, measurement, multiplication_division) --
    # a numeric digit-reversal coincidence there must NOT be attributed to
    # this subtraction-borrowing-specific bug.
    no_digits_correct = {"value": 352}
    no_digits_student = {"value": 253}
    assert match_buggy_rule("write_final_answer", no_digits_correct, no_digits_student) is None


def test_ap3_area_as_sum() -> None:
    correct = {"length": 4, "width": 6, "result": 24}
    buggy_student = {"length": 4, "width": 6, "result": 10}
    match = match_buggy_rule("compute_area", correct, buggy_student)
    assert match is not None
    assert match.buggy_rule_id == "area_perimeter.area_as_sum"

    correct_student = {"length": 4, "width": 6, "result": 24}
    assert match_buggy_rule("compute_area", correct, correct_student) is None


def test_ap5_perimeter_uses_area_formula() -> None:
    correct = {"length": 4, "width": 6, "result": 20}
    buggy_student = {"length": 4, "width": 6, "result": 24}
    match = match_buggy_rule("compute_perimeter", correct, buggy_student)
    assert match is not None
    assert match.buggy_rule_id == "area_perimeter.perimeter_uses_area_formula"

    correct_student = {"length": 4, "width": 6, "result": 20}
    assert match_buggy_rule("compute_perimeter", correct, correct_student) is None


def test_md4_divide_tens_drops_remainder() -> None:
    correct = {"dividend_group": 7, "divisor": 3, "quotient_digit": 2, "remainder": 1}
    buggy_student = {"dividend_group": 7, "divisor": 3, "quotient_digit": 2, "remainder": 0}
    match = match_buggy_rule("divide_tens", correct, buggy_student)
    assert match is not None
    assert match.buggy_rule_id == "multiplication_division.divide_tens_drops_remainder"

    correct_student = {"dividend_group": 7, "divisor": 3, "quotient_digit": 2, "remainder": 1}
    assert match_buggy_rule("divide_tens", correct, correct_student) is None


def test_sa2_right_straight_swap() -> None:
    correct = {"answer": "right"}
    buggy_student = {"answer": "straight"}
    match = match_buggy_rule("shapes_angles_answer", correct, buggy_student)
    assert match is not None
    assert match.buggy_rule_id == "shapes_angles.right_straight_swap"

    correct_student = {"answer": "right"}
    assert match_buggy_rule("shapes_angles_answer", correct, correct_student) is None


def test_dec4_decimal_point_shifted_final() -> None:
    correct = {"result_hundredths": 465}
    buggy_student = {"result_hundredths": 4650}
    match = match_buggy_rule("write_final_answer", correct, buggy_student)
    assert match is not None
    assert match.buggy_rule_id == "decimals.decimal_point_shifted_final"

    correct_student = {"result_hundredths": 465}
    assert match_buggy_rule("write_final_answer", correct, correct_student) is None
