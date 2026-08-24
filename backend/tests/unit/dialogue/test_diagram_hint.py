import json

from studyhelp.dialogue.diagram_hint import (
    DIAGRAM_HINT_MISCONCEPTION_IDS,
    SYMMETRY_REVEAL_REPEAT_THRESHOLD,
    should_attach_diagram_hint,
    should_reveal_symmetry_lines,
)
from studyhelp.seed.loader import FIXTURES_ROOT


def test_curated_id_attaches() -> None:
    assert should_attach_diagram_hint("fractions_addition.no_common_denominator") is True


def test_uncurated_id_does_not_attach() -> None:
    assert should_attach_diagram_hint("fractions_addition.add_across") is False


def test_none_does_not_attach() -> None:
    assert should_attach_diagram_hint(None) is False


def test_every_curated_id_is_a_non_empty_string() -> None:
    assert len(DIAGRAM_HINT_MISCONCEPTION_IDS) > 0
    for misconception_id in DIAGRAM_HINT_MISCONCEPTION_IDS:
        assert isinstance(misconception_id, str) and misconception_id


def test_every_curated_id_actually_exists_in_the_misconception_bank_fixtures() -> None:
    """A stale/typo'd id here would silently never fire — this test fails
    loudly instead the moment a curated id and the bank fixtures drift
    apart (e.g. an id gets renamed in a fixture file after this module was
    written)."""
    all_bank_ids: set[str] = set()
    for path in sorted((FIXTURES_ROOT / "misconception_bank").glob("*.json")):
        entries = json.loads(path.read_text(encoding="utf-8"))
        all_bank_ids.update(entry["id"] for entry in entries)

    missing = DIAGRAM_HINT_MISCONCEPTION_IDS - all_bank_ids
    assert not missing, f"Curated diagram-hint ids missing from the misconception bank: {missing}"


def test_symmetry_reveals_at_threshold() -> None:
    assert should_reveal_symmetry_lines("symmetry", SYMMETRY_REVEAL_REPEAT_THRESHOLD) is True


def test_symmetry_reveals_above_threshold() -> None:
    assert should_reveal_symmetry_lines("symmetry", SYMMETRY_REVEAL_REPEAT_THRESHOLD + 5) is True


def test_symmetry_does_not_reveal_below_threshold() -> None:
    assert should_reveal_symmetry_lines("symmetry", SYMMETRY_REVEAL_REPEAT_THRESHOLD - 1) is False


def test_other_topics_never_reveal_regardless_of_repeat_count() -> None:
    for topic in (
        "subtraction_borrowing",
        "fractions_addition",
        "lcm_hcf",
        "area_perimeter",
        "decimals",
        "measurement",
        "shapes_angles",
    ):
        assert should_reveal_symmetry_lines(topic, 99) is False
