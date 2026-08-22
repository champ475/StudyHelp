"""Regression coverage for the two hand-authored constraints
`llm/analogies.py`'s docstring commits every library entry to: no bare
digits (leakage-collision risk) and a Class-5 readability ceiling once
wrapped the way `dialogue/orchestrator.py`'s generate() call actually uses
it (CLAUDE.md Bug2)."""

import re

from studyhelp.dialogue.readability_gate import passes_readability
from studyhelp.llm.analogies import TOPIC_ANALOGIES, get_analogy

_DIGIT = re.compile(r"\d")


def test_get_analogy_returns_none_for_unknown_topic() -> None:
    assert get_analogy("shapes_angles") is None
    assert get_analogy("not_a_real_topic") is None


def test_every_analogy_is_registered_and_non_empty() -> None:
    assert len(TOPIC_ANALOGIES) >= 7
    for topic, text in TOPIC_ANALOGIES.items():
        assert get_analogy(topic) == text
        assert text.strip()


def test_no_analogy_contains_a_bare_digit() -> None:
    """A numeral used only for analogy flavor could coincidentally equal
    the real problem's own protected answer digit and get an otherwise
    safe message rejected by the leakage filter for an unrelated reason —
    see the module docstring."""
    for topic, text in TOPIC_ANALOGIES.items():
        assert not _DIGIT.search(text), f"{topic}: analogy contains a bare digit: {text!r}"


def test_every_analogy_passes_readability_once_wrapped() -> None:
    """Mirrors the wrapping `llm/providers/mock.py`'s `generate()` (and the
    real GENERATE_SYSTEM_PROMPT rule 8) apply around the raw analogy text."""
    for topic, analogy in TOPIC_ANALOGIES.items():
        wrapped = (
            f"Let's try this a different way. {analogy} Now think about your own step. "
            "What do you notice that might need to change?"
        )
        assert passes_readability(wrapped, max_grade=5.0), (
            f"{topic}: wrapped analogy fails the Class-5 readability ceiling"
        )
