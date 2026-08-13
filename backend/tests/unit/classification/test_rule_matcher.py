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
