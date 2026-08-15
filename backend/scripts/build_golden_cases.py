"""Builds the golden regression suite's JSON case files
(tests/golden/subtraction_borrowing/cases/*.json) by pulling
`expected_state` straight from the real seeded problem fixtures — never
hand-transcribed, so case digits can't drift from the problems they're
tested against.

Cases are expressed as free text (ARCHITECTURE.md D41/D43 -- this topic's
port off tap-widget input), rendered from the same structured field dicts
via `_render_text()` (the inverse of `free_text_parser.parse_student_text`)
so the *semantics* each case exercises (which fields are right/wrong) stay
identical to the pre-port suite; only the wire encoding changed.

Not run automatically (the golden suite is a committed, reviewed artifact,
not regenerated on every test run) — re-run deliberately when adding new
cases, then review the diff before committing.

Usage: python scripts/build_golden_cases.py
"""

import json
from pathlib import Path

from studyhelp.schemas.step_schema import Problem
from studyhelp.seed.loader import load_problems
from studyhelp.verification.topics.subtraction_borrowing.free_text_parser import (
    render_student_text as _render_text,
)

OUT_DIR = Path(__file__).parents[1] / "tests" / "golden" / "subtraction_borrowing" / "cases"

problems: dict[str, Problem] = {p.problem_id: p for p in load_problems()}


def field(problem_id: str, step_id: str) -> dict:
    node = problems[problem_id].node(step_id)
    assert node is not None
    return dict(node.expected_state)


def path_to(problem_id: str, step_id: str) -> list[str]:
    """Canonical-path prefix (exclusive of step_id) — walks node.next[0]
    from the graph root until step_id is reached."""
    problem = problems[problem_id]
    path = []
    node = problem.step_graph[0]
    while node.step_id != step_id:
        path.append(node.step_id)
        nxt = problem.node(node.next[0])
        assert nxt is not None
        node = nxt
    return path


cases = []


def add(case_id, problem_id, target_step_id_or_none, student_type, student_fields, expected):
    add_raw_text(
        case_id,
        problem_id,
        target_step_id_or_none,
        _render_text(student_type, student_fields),
        expected,
    )


def add_raw_text(case_id, problem_id, target_step_id_or_none, raw_text, expected):
    prior = path_to(problem_id, target_step_id_or_none) if target_step_id_or_none else []
    cases.append(
        {
            "case_id": case_id,
            "problem_id": problem_id,
            "prior_accepted_steps": prior,
            "student_step": {"step_type": "free_text_step", "fields": {"text": raw_text}},
            "expected": expected,
        }
    )


# ============================== ACCEPT (clean frontier match) ==============
add(
    "accept_001_p001_first_step",
    "subtraction-borrow-001",
    "s1_cmp_units",
    "compare_column",
    field("subtraction-borrow-001", "s1_cmp_units"),
    {
        "is_valid": True,
        "matched_step_id": "s1_cmp_units",
        "confidence_band": "accept",
        "error_kind": None,
        "error_note": None,
    },
)

add(
    "accept_002_p001_final_answer",
    "subtraction-borrow-001",
    "s6_final",
    "write_final_answer",
    field("subtraction-borrow-001", "s6_final"),
    {
        "is_valid": True,
        "matched_step_id": "s6_final",
        "confidence_band": "accept",
        "error_kind": None,
        "error_note": None,
    },
)

add(
    "accept_003_p002_first_borrow",
    "subtraction-borrow-002",
    "s2_borrow_hundreds_to_tens",
    "borrow",
    field("subtraction-borrow-002", "s2_borrow_hundreds_to_tens"),
    {
        "is_valid": True,
        "matched_step_id": "s2_borrow_hundreds_to_tens",
        "confidence_band": "accept",
        "error_kind": None,
        "error_note": None,
    },
)

add(
    "accept_004_p003_first_subtract_no_borrow",
    "subtraction-borrow-003",
    "s2_sub_units",
    "subtract_column",
    field("subtraction-borrow-003", "s2_sub_units"),
    {
        "is_valid": True,
        "matched_step_id": "s2_sub_units",
        "confidence_band": "accept",
        "error_kind": None,
        "error_note": None,
    },
)

add(
    "accept_005_p004_middle_borrow_chain",
    "subtraction-borrow-004",
    "s3_borrow_hundreds_to_tens",
    "borrow",
    field("subtraction-borrow-004", "s3_borrow_hundreds_to_tens"),
    {
        "is_valid": True,
        "matched_step_id": "s3_borrow_hundreds_to_tens",
        "confidence_band": "accept",
        "error_kind": None,
        "error_note": None,
    },
)

add(
    "accept_006_p005_middle_step",
    "subtraction-borrow-005",
    "s5_borrow_tens",
    "borrow",
    field("subtraction-borrow-005", "s5_borrow_tens"),
    {
        "is_valid": True,
        "matched_step_id": "s5_borrow_tens",
        "confidence_band": "accept",
        "error_kind": None,
        "error_note": None,
    },
)

add(
    "accept_007_p014_middle_step",
    "subtraction-borrow-014",
    "s4_cmp_tens",
    "compare_column",
    field("subtraction-borrow-014", "s4_cmp_tens"),
    {
        "is_valid": True,
        "matched_step_id": "s4_cmp_tens",
        "confidence_band": "accept",
        "error_kind": None,
        "error_note": None,
    },
)

add(
    "accept_008_p002_final_answer",
    "subtraction-borrow-002",
    "s9_final",
    "write_final_answer",
    field("subtraction-borrow-002", "s9_final"),
    {
        "is_valid": True,
        "matched_step_id": "s9_final",
        "confidence_band": "accept",
        "error_kind": None,
        "error_note": None,
    },
)

add(
    "accept_009_p004_final_answer",
    "subtraction-borrow-004",
    "s12_final",
    "write_final_answer",
    field("subtraction-borrow-004", "s12_final"),
    {
        "is_valid": True,
        "matched_step_id": "s12_final",
        "confidence_band": "accept",
        "error_kind": None,
        "error_note": None,
    },
)

# ============================== NON-ADJACENT (exact match, skipped ahead) ==
add(
    "non_adjacent_001_p014_skip_borrow",
    "subtraction-borrow-014",
    "s1_cmp_units",
    "subtract_column",
    field("subtraction-borrow-014", "s3_sub_units"),
    {
        "is_valid": True,
        "matched_step_id": "s3_sub_units",
        "confidence_band": "non_adjacent",
        "error_kind": "none",
        "error_note": "non_adjacent_valid_match",
    },
)

add(
    "non_adjacent_002_p002_skip_both_borrows",
    "subtraction-borrow-002",
    "s1_cmp_units",
    "subtract_column",
    field("subtraction-borrow-002", "s4_sub_units"),
    {
        "is_valid": True,
        "matched_step_id": "s4_sub_units",
        "confidence_band": "non_adjacent",
        "error_kind": "none",
        "error_note": "non_adjacent_valid_match",
    },
)

add(
    "non_adjacent_003_p004_skip_all_three_borrows",
    "subtraction-borrow-004",
    "s1_cmp_units",
    "subtract_column",
    field("subtraction-borrow-004", "s5_sub_units"),
    {
        "is_valid": True,
        "matched_step_id": "s5_sub_units",
        "confidence_band": "non_adjacent",
        "error_kind": "none",
        "error_note": "non_adjacent_valid_match",
    },
)

add(
    "non_adjacent_004_p005_skip_borrow",
    "subtraction-borrow-005",
    "s1_cmp_units",
    "subtract_column",
    field("subtraction-borrow-005", "s3_sub_units"),
    {
        "is_valid": True,
        "matched_step_id": "s3_sub_units",
        "confidence_band": "non_adjacent",
        "error_kind": "none",
        "error_note": "non_adjacent_valid_match",
    },
)


# ============================== REJECT: B1 smaller-from-larger (1-field-off) =
def b1_case(case_id, problem_id, target_step_id, pre_borrow_minuend_digit):
    correct = field(problem_id, target_step_id)
    buggy_result = abs(correct["subtrahend_digit"] - pre_borrow_minuend_digit)
    assert buggy_result != correct["result_digit"], (
        "B1 case must diverge from correct to be meaningful"
    )
    buggy = dict(correct)
    buggy["result_digit"] = buggy_result
    add(
        case_id,
        problem_id,
        target_step_id,
        "subtract_column",
        buggy,
        {
            "is_valid": False,
            "matched_step_id": None,
            "confidence_band": "reject",
            "error_kind": "field_mismatch",
            "error_note": None,
        },
    )


b1_case(
    "reject_b1_001_p001_units", "subtraction-borrow-001", "s3_sub_units", pre_borrow_minuend_digit=2
)
b1_case(
    "reject_b1_002_p004_units", "subtraction-borrow-004", "s5_sub_units", pre_borrow_minuend_digit=0
)
b1_case(
    "reject_b1_003_p005_units", "subtraction-borrow-005", "s3_sub_units", pre_borrow_minuend_digit=2
)


# ============================== REJECT: B2 no-decrement-after-borrow (1-field-off)
def b2_case(case_id, problem_id, target_step_id):
    correct = field(problem_id, target_step_id)
    buggy = dict(correct)
    buggy["from_digit_after"] = buggy["from_digit_before"]  # never decremented
    assert buggy["from_digit_after"] != correct["from_digit_after"]
    add(
        case_id,
        problem_id,
        target_step_id,
        "borrow",
        buggy,
        {
            "is_valid": False,
            "matched_step_id": None,
            "confidence_band": "reject",
            "error_kind": "field_mismatch",
            "error_note": None,
        },
    )


b2_case("reject_b2_001_p001_borrow", "subtraction-borrow-001", "s2_borrow_units")
b2_case("reject_b2_002_p005_first_borrow", "subtraction-borrow-005", "s2_borrow_units")
b2_case("reject_b2_003_p014_second_borrow", "subtraction-borrow-014", "s5_borrow_tens")


# ============================== REJECT: B3 borrow-across-zero (1-field-off) ===
def b3_case(case_id, problem_id, target_step_id):
    correct = field(problem_id, target_step_id)
    assert correct["to_digit_before"] == 0, "B3 case must target a zero-column borrow"
    buggy = dict(correct)
    buggy["to_digit_after"] = 9  # zero column mishandled instead of +10
    assert buggy["to_digit_after"] != correct["to_digit_after"]
    add(
        case_id,
        problem_id,
        target_step_id,
        "borrow",
        buggy,
        {
            "is_valid": False,
            "matched_step_id": None,
            "confidence_band": "reject",
            "error_kind": "field_mismatch",
            "error_note": None,
        },
    )


b3_case(
    "reject_b3_001_p002_borrow_across_zero", "subtraction-borrow-002", "s2_borrow_hundreds_to_tens"
)
b3_case(
    "reject_b3_002_p004_first_borrow", "subtraction-borrow-004", "s2_borrow_thousands_to_hundreds"
)
b3_case("reject_b3_003_p004_second_borrow", "subtraction-borrow-004", "s3_borrow_hundreds_to_tens")


# ============================== PASSTHROUGH: ambiguous submissions (<0.75) ===
def passthrough_case(case_id, problem_id, target_step_id, student_type, overrides):
    correct = field(problem_id, target_step_id)
    buggy = dict(correct)
    buggy.update(overrides)
    add(
        case_id,
        problem_id,
        target_step_id,
        student_type,
        buggy,
        {
            "is_valid": True,
            "matched_step_id": None,
            "confidence_band": "passthrough",
            "error_kind": "field_mismatch",
            "error_note": "low_confidence_passthrough",
        },
    )


passthrough_case(
    "passthrough_001_p002_ambiguous_borrow",
    "subtraction-borrow-002",
    "s2_borrow_hundreds_to_tens",
    "borrow",
    {"from_column": "thousands", "from_digit_before": 9, "from_digit_after": 8},
)

passthrough_case(
    "passthrough_002_p001_ambiguous_borrow",
    "subtraction-borrow-001",
    "s2_borrow_units",
    "borrow",
    {"from_column": "hundreds", "from_digit_before": 9, "from_digit_after": 8},
)

passthrough_case(
    "passthrough_003_p003_ambiguous_subtract",
    "subtraction-borrow-003",
    "s2_sub_units",
    "subtract_column",
    {"minuend_digit": 3, "result_digit": 0},
)

passthrough_case(
    "passthrough_004_p005_ambiguous_compare",
    "subtraction-borrow-005",
    "s4_cmp_tens",
    "compare_column",
    {"minuend_digit": 9, "subtrahend_digit": 1, "borrow_needed": False},
)

# B4 stale-borrow-digit: genuinely lands as passthrough under the Phase-1
# field-agreement heuristic (2 of 4 fields diverge) — an honest, deliberate
# finding (see CHANGELOG), not an oversight: it's exactly the two-field-
# correlated bug shape Phase 2's buggy-rule matcher (operating on the raw
# correct/student pair, not a threshold) exists to catch.
passthrough_case(
    "passthrough_005_p014_b4_stale_borrow_digit",
    "subtraction-borrow-014",
    "s6_sub_tens",
    "subtract_column",
    {"minuend_digit": 14, "result_digit": 6},
)

# ============================== STRUCTURAL REJECTION ==========================
# Free text that doesn't match ANY of the four step grammars at all --
# with tap widgets, an explicit unrecognized step_type used to trigger
# this; with free text, the analogous "structurally not a step at all"
# case is text with no grammar match whatsoever (ARCHITECTURE.md D41/D43).
add_raw_text(
    "structural_001_p001_text_matches_no_grammar",
    "subtraction-borrow-001",
    None,
    "please multiply everything",
    {
        "is_valid": False,
        "matched_step_id": None,
        "confidence_band": "structural",
        "error_kind": "malformed",
        "error_note": None,
    },
)

add(
    "structural_002_p002_malformed_borrow",
    "subtraction-borrow-002",
    None,
    "borrow",
    {
        "from_column": "hundreds",
        "from_digit_before": "five",
        "from_digit_after": 4,
        "to_column": "tens",
        "to_digit_before": 0,
        "to_digit_after": 10,
    },
    {
        "is_valid": False,
        "matched_step_id": None,
        "confidence_band": "structural",
        "error_kind": "malformed",
        "error_note": None,
    },
)

add(
    "structural_003_p003_no_borrow_step_in_this_problem",
    "subtraction-borrow-003",
    None,
    "borrow",
    {
        "from_column": "tens",
        "from_digit_before": 8,
        "from_digit_after": 7,
        "to_column": "units",
        "to_digit_before": 9,
        "to_digit_after": 19,
    },
    {
        "is_valid": False,
        "matched_step_id": None,
        "confidence_band": "structural",
        "error_kind": "wrong_step_type",
        "error_note": None,
    },
)

# ==============================================================================

if __name__ == "__main__":
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for case in cases:
        path = OUT_DIR / f"{case['case_id']}.json"
        path.write_text(json.dumps(case, indent=2) + "\n")

    band_counts: dict[str, int] = {}
    for c in cases:
        band = c["expected"]["confidence_band"]
        band_counts[band] = band_counts.get(band, 0) + 1
    print(f"Wrote {len(cases)} golden case files to {OUT_DIR}")
    print("By band:", band_counts)
