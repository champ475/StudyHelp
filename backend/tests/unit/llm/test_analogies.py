"""Regression coverage for the hand-authored constraints `llm/analogies.py`'s
docstring commits every library entry to: no bare digits, a Class-5
readability ceiling once wrapped the way `dialogue/orchestrator.py`'s
generate() call actually uses it (CLAUDE.md Bug2), and — for the
word-answer light-check topics — no literal collision with any of that
topic's own possible answer words (CLAUDE.md e2e-round-2 finding: an
earlier `shapes_angles` draft named "acute"/"obtuse"/"right" directly,
which is exactly this topic's own closed answer vocabulary, and got
rejected by the leakage filter live on a problem whose real answer was
"acute")."""

import json
import re
from pathlib import Path

from studyhelp.dialogue.leakage_filter import contains_leakage
from studyhelp.dialogue.readability_gate import passes_readability
from studyhelp.llm.analogies import TOPIC_ANALOGIES, get_analogy

_DIGIT = re.compile(r"\d")

_FIXTURES_DIR = Path(__file__).parents[3] / "src" / "studyhelp" / "seed" / "fixtures" / "problems"
_LIGHT_CHECK_TOPIC_DIRS = {
    "shapes_angles": "ch2_shapes_angles",
    "how_many_squares": "ch3_how_many_squares",
    "symmetry": "ch5_symmetry",
    "patterns": "ch7_patterns",
    "mapping": "ch8_mapping",
    "boxes_sketches": "ch9_boxes_sketches",
    "smart_charts": "ch12_smart_charts",
}


def test_get_analogy_returns_none_for_unknown_topic() -> None:
    assert get_analogy("not_a_real_topic") is None


def test_every_registered_topic_has_an_analogy() -> None:
    """All 14 topics (7 heavy DAG + 7 light-check) now have a library
    entry — the light-check 7 were added after the e2e sweep found a
    student stuck on the same light-check mistake twice got the identical
    generic re-explanation verbatim, with no register to switch to."""
    assert len(TOPIC_ANALOGIES) == 14
    for topic in (
        "subtraction_with_borrowing",
        "fractions_addition",
        "lcm_hcf",
        "decimals",
        "area_perimeter",
        "multiplication_division",
        "measurement",
        "patterns",
        "shapes_angles",
        "how_many_squares",
        "symmetry",
        "mapping",
        "boxes_sketches",
        "smart_charts",
    ):
        assert get_analogy(topic) is not None, f"{topic}: missing analogy entry"


def test_every_analogy_is_registered_and_non_empty() -> None:
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


def test_no_light_check_analogy_collides_with_that_topics_own_answer_words() -> None:
    """Every light-check topic's `expected_state.answer` across every one
    of its seeded problems must never appear inside that topic's own
    analogy text, using the exact same case-insensitive check the real
    leakage filter applies — a numeric-answer topic (how_many_squares,
    symmetry, mapping, boxes_sketches, smart_charts) is already covered by
    `test_no_analogy_contains_a_bare_digit`, but a word-answer topic
    (shapes_angles, and `patterns`' word-shaped edge cases if any) needs
    this check against its actual real answer vocabulary too."""
    for topic, dirname in _LIGHT_CHECK_TOPIC_DIRS.items():
        analogy = TOPIC_ANALOGIES[topic]
        answers: set[str] = set()
        for path in (_FIXTURES_DIR / dirname).glob("*.json"):
            problem = json.loads(path.read_text(encoding="utf-8"))
            for node in problem["step_graph"]:
                answer = node["expected_state"].get("answer")
                if isinstance(answer, str) and not answer.isdigit():
                    answers.add(answer)
        for answer in answers:
            assert not contains_leakage(analogy, [answer]), (
                f"{topic}: analogy collides with its own real answer word {answer!r}"
            )


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
