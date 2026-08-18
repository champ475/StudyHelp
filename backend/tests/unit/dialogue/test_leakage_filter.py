"""Regression set for the leakage filter: known-leaky drafts that must be
caught, and known-safe drafts that must NOT be flagged (precision matters
as much as recall — an over-aggressive filter burns through the turn
budget with pointless regenerations, per technical_architecture.md §9)."""

import pytest

from studyhelp.dialogue.leakage_filter import contains_leakage

# --- known-leaky: must be caught -------------------------------------------
LEAKY_CASES = [
    ("The answer is 355.", [355]),
    ("You need to write 5 here.", [5]),
    ("The result is 27, can you see why?", [27]),
    ("That equals 12, right?", [12]),
    ("It is equal to 8.", [8]),
    ("So we know 1/4 < 1/6.", ["<"]),
    ("This shape is acute, isn't it?", ["acute"]),
    ("This shape is Acute, isn't it?", ["acute"]),
]

# --- known-safe: must NOT be flagged ----------------------------------------
SAFE_CASES = [
    ("Let's look at this column again — what do you notice?", [5]),
    ("If you have 5 apples, can you take away 7 of them?", [355]),
    ("Try again — think about what happens when the top digit is smaller.", [12]),
    ("You wrote 3 here. If we have 2 apples, can we take away 7 of them?", [9]),
    ("Where could we borrow some from?", [355, 5]),
    ("Which fraction do you think has bigger pieces?", ["<", ">"]),
    ("Is this angle bigger or smaller than a right angle?", ["acute"]),
]


@pytest.mark.parametrize(("message", "protected_values"), LEAKY_CASES)
def test_known_leaky_drafts_are_caught(message: str, protected_values: list[int | str]) -> None:
    assert contains_leakage(message, protected_values) is True


@pytest.mark.parametrize(("message", "protected_values"), SAFE_CASES)
def test_known_safe_drafts_are_not_flagged(message: str, protected_values: list[int | str]) -> None:
    assert contains_leakage(message, protected_values) is False
