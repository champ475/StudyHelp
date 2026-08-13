"""Regression set for the readability gate: known-over-complex drafts that
must be caught, and known-simple drafts that must NOT be flagged.
Flesch-Kincaid grades verified directly against textstat (not guessed) —
see CHANGELOG for the empirical check."""

import pytest

from studyhelp.dialogue.readability_gate import passes_readability

MAX_GRADE = 5.0

# --- known-over-complex: must be caught (grade ~20) -------------------------
OVER_COMPLEX_CASES = [
    "The subtrahend digit exceeds the corresponding minuend digit, thereby "
    "necessitating a regrouping operation wherein a unit is transferred from "
    "the adjacent higher-order positional column.",
    "The insufficiency of the minuend necessitates procurement of supplementary "
    "value from the preceding column via a regrouping procedure commonly "
    "termed borrowing.",
]

# --- known-simple: must NOT be flagged (grade well under 5) ----------------
SIMPLE_CASES = [
    "Look at this column. Is the top number big enough? If not, we need to borrow first.",
    "You wrote 3 here. If we have 2 apples, can we take away 7 of them?",
    "Right! So before we subtract, we need more apples in this pile. Where could we borrow some from?",
    "Can we take 7 away from 2? No. So we need to borrow a ten first.",
]


@pytest.mark.parametrize("message", OVER_COMPLEX_CASES)
def test_over_complex_drafts_are_caught(message: str) -> None:
    assert passes_readability(message, MAX_GRADE) is False


@pytest.mark.parametrize("message", SIMPLE_CASES)
def test_simple_drafts_are_not_flagged(message: str) -> None:
    assert passes_readability(message, MAX_GRADE) is True
