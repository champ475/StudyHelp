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
from studyhelp.dialogue.step_family import resolve_step_family
from studyhelp.llm.analogies import STEP_FAMILY_ANALOGIES, TOPIC_ANALOGIES, get_analogy

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


# ---------------------------------------------------------------------------
# Step-family-specific overrides (CLAUDE.md live-testing Bug D): three
# topics whose chapter mixes two distinct operations under one topic string
# each got a per-family entry instead of one conflated topic-wide analogy.
# ---------------------------------------------------------------------------

_MIXED_TOPIC_FAMILIES = {
    "area_perimeter": ("area", "perimeter"),
    "multiplication_division": ("multiply", "divide"),
    "lcm_hcf": ("lcm", "hcf"),
}


def test_every_mixed_topic_has_both_step_family_entries() -> None:
    for topic, families in _MIXED_TOPIC_FAMILIES.items():
        for family in families:
            assert (topic, family) in STEP_FAMILY_ANALOGIES, (
                f"{topic}/{family}: missing step-family analogy entry"
            )


def test_get_analogy_prefers_step_family_entry_over_topic_wide_entry() -> None:
    for topic, families in _MIXED_TOPIC_FAMILIES.items():
        for family in families:
            assert get_analogy(topic, family) == STEP_FAMILY_ANALOGIES[(topic, family)]
            assert get_analogy(topic, family) != TOPIC_ANALOGIES[topic]


def test_get_analogy_falls_back_to_topic_wide_entry_when_family_unresolved() -> None:
    for topic in _MIXED_TOPIC_FAMILIES:
        assert get_analogy(topic, None) == TOPIC_ANALOGIES[topic]
        assert get_analogy(topic, "not_a_real_family") == TOPIC_ANALOGIES[topic]


def test_area_perimeter_analogy_does_not_conflate_the_two_operations() -> None:
    """The exact bug reported live: a pure-area step's analogy must not also
    talk about walking around the edge (perimeter), and vice versa."""
    area_analogy = STEP_FAMILY_ANALOGIES[("area_perimeter", "area")]
    perimeter_analogy = STEP_FAMILY_ANALOGIES[("area_perimeter", "perimeter")]
    assert "walk" not in area_analogy.lower()
    assert "edge" not in area_analogy.lower()
    assert "tile" not in perimeter_analogy.lower()


def test_no_step_family_analogy_contains_a_bare_digit() -> None:
    for key, text in STEP_FAMILY_ANALOGIES.items():
        assert not _DIGIT.search(text), f"{key}: analogy contains a bare digit: {text!r}"


def test_every_step_family_analogy_passes_readability_once_wrapped() -> None:
    for key, analogy in STEP_FAMILY_ANALOGIES.items():
        wrapped = (
            f"Let's try this a different way. {analogy} Now think about your own step. "
            "What do you notice that might need to change?"
        )
        assert passes_readability(wrapped, max_grade=5.0), (
            f"{key}: wrapped step-family analogy fails the Class-5 readability ceiling"
        )


def test_resolve_step_family_matches_the_real_seeded_problems() -> None:
    """Cross-check against every seeded problem in the three mixed topics:
    `resolve_step_family` must never return `None` for a real problem's own
    step, and must agree with that problem's `given` discriminator field."""
    for topic, dirname in (
        ("area_perimeter", "ch11_area_perimeter"),
        ("multiplication_division", "ch13_multiplication_division"),
        ("lcm_hcf", "ch6_lcm_hcf"),
    ):
        for path in (_FIXTURES_DIR / dirname).glob("*.json"):
            problem = json.loads(path.read_text(encoding="utf-8"))
            given = problem["given"]
            for node in problem["step_graph"]:
                family = resolve_step_family(topic, node["type"], given)
                assert family is not None, (
                    f"{topic}/{path.name}/{node['step_id']}: step_family unresolved "
                    f"(step_type={node['type']!r}, given={given!r})"
                )
                assert (topic, family) in STEP_FAMILY_ANALOGIES
