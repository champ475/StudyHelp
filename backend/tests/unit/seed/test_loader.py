"""Pure-Python checks on the seed fixtures: they parse/validate cleanly,
and the cross-references between step_types / misconception_bank /
buggy_rule_library are internally consistent. DB upsert itself is exercised
by an integration test (needs a real Postgres)."""

from studyhelp.seed.loader import (
    load_buggy_rules,
    load_misconceptions,
    load_problems,
    load_step_types,
)


def test_step_types_load_and_cover_every_registered_step_type() -> None:
    step_types = load_step_types()
    keys = {(s.topic, s.step_type_key) for s in step_types}
    assert keys == {
        ("subtraction_with_borrowing", "compare_column"),
        ("subtraction_with_borrowing", "borrow"),
        ("subtraction_with_borrowing", "subtract_column"),
        ("subtraction_with_borrowing", "write_final_answer"),
        ("fractions_addition", "rewrite_common_denominator"),
        ("fractions_addition", "add_numerators"),
        ("fractions_addition", "subtract_numerators"),
        ("fractions_addition", "compare_fractions"),
        ("fractions_addition", "simplify_fraction"),
        ("fractions_addition", "write_final_answer"),
        ("lcm_hcf", "find_common_values"),
        ("lcm_hcf", "write_final_answer"),
        ("decimals", "align_place_value"),
        ("decimals", "compute_result"),
        ("decimals", "write_final_answer"),
        ("area_perimeter", "compute_area"),
        ("area_perimeter", "compute_perimeter"),
        ("area_perimeter", "write_final_answer"),
        ("multiplication_division", "multiply_units"),
        ("multiplication_division", "multiply_tens"),
        ("multiplication_division", "divide_tens"),
        ("multiplication_division", "divide_units"),
        ("multiplication_division", "write_final_answer"),
        ("measurement", "identify_conversion_factor"),
        ("measurement", "convert_units"),
        ("measurement", "write_final_answer"),
    }


def test_problems_load_and_pass_arithmetic_validation() -> None:
    """load_problems() itself calls validate_problem_arithmetic() on every
    fixture — if this doesn't raise, every seeded problem is internally
    consistent per the independent sympy cross-check."""
    problems = load_problems()
    assert len(problems) >= 66
    problem_ids = {p.problem_id for p in problems}
    assert "subtraction-borrow-014" in problem_ids


def test_misconceptions_load_with_nineteen_seed_entries() -> None:
    entries = load_misconceptions()
    assert len(entries) == 19
    ids = {e.id for e in entries}
    assert ids == {
        "subtraction_borrowing.smaller_from_larger",
        "subtraction_borrowing.no_decrement_after_borrow",
        "subtraction_borrowing.borrow_across_zero",
        "subtraction_borrowing.stale_borrow_digit",
        "fractions_addition.no_common_denominator",
        "fractions_addition.add_across",
        "fractions_addition.forgot_to_simplify",
        "fractions_addition.subtract_across",
        "fractions_addition.compares_numerators_only",
        "lcm_hcf.list_shifted_by_one",
        "lcm_hcf.extra_non_common_value",
        "decimals.tenths_written_as_hundredths",
        "decimals.decimal_point_shifted",
        "area_perimeter.formula_confusion",
        "area_perimeter.forgot_times_two",
        "multiplication_division.forgot_carry",
        "multiplication_division.misplaced_remainder",
        "measurement.wrong_direction",
        "measurement.wrong_factor",
    }


def test_buggy_rules_load_with_nineteen_seed_entries() -> None:
    entries = load_buggy_rules()
    assert len(entries) == 19
    bug_codes = {e.bug_code for e in entries}
    assert bug_codes == {
        "B1-smaller-from-larger",
        "B2-no-decrement-after-borrow",
        "B3-borrow-across-zero",
        "B4-stale-borrow-digit",
        "F1-no-common-denominator",
        "F2-add-across",
        "F3-forgot-to-simplify",
        "F4-subtract-across",
        "F5-compares-numerators-only",
        "LH1-list-shifted-by-one",
        "LH2-extra-non-common-value",
        "DEC1-tenths-written-as-hundredths",
        "DEC2-decimal-point-shifted",
        "AP1-formula-confusion",
        "AP2-forgot-times-two",
        "MD1-forgot-carry",
        "MD2-misplaced-remainder",
        "ME1-wrong-direction",
        "ME2-wrong-factor",
    }


def test_every_buggy_rule_misconception_id_resolves() -> None:
    misconception_ids = {e.id for e in load_misconceptions()}
    for rule in load_buggy_rules():
        assert rule.misconception_id is not None
        assert rule.misconception_id in misconception_ids, (
            f"{rule.id} references missing misconception {rule.misconception_id}"
        )


def test_every_buggy_rule_and_misconception_step_type_is_registered() -> None:
    registered = {(s.topic, s.step_type_key) for s in load_step_types()}
    for rule in load_buggy_rules():
        assert (rule.topic, rule.step_type) in registered, f"{rule.id} uses unregistered step_type"
    for entry in load_misconceptions():
        assert (entry.topic, entry.step_type) in registered, (
            f"{entry.id} uses unregistered step_type"
        )


def test_every_buggy_rule_example_pair_problem_exists() -> None:
    problem_ids = {p.problem_id for p in load_problems()}
    for rule in load_buggy_rules():
        assert rule.example_pair.problem_id in problem_ids, (
            f"{rule.id}'s example_pair references unknown problem {rule.example_pair.problem_id}"
        )
