"""Deterministic diagram-as-hint lookup for the dialogue's remediation
turns (distinct from `frontend/src/diagrams/DiagramPanel.tsx`, which shows a
diagram alongside the problem statement at load time regardless of whether
the student has made any mistake).

Same non-negotiable as `llm/analogies.py::get_analogy()`: which diagram
shows up, if any, is picked by application code, never by the LLM — the
model has no diagram-authoring ability at all, so there is nothing here for
`decide()`/`generate()` to invent or leak. This module only ever answers
"should the frontend re-show topic X's existing, `given`-derived diagram
this turn" — it never produces new diagram content of its own; the actual
picture is still whichever `DIAGRAM_REGISTRY[topic]` renderer the frontend
already uses at problem-load, driven by the same `given` (never
`expected_state`), so nothing shown mid-dialogue can reveal more than the
problem statement itself already did.

`DIAGRAM_HINT_MISCONCEPTION_IDS` is a curated, hand-picked subset of the
misconception bank — not "every misconception in a topic with a real
diagram renderer" — because a diagram only actually helps when the
*specific* confusion is visual/spatial in nature (e.g. "which pieces are
bigger," "does this fold match") rather than, say, a purely procedural slip
(forgetting a step) or an arithmetic mistake a picture wouldn't clarify."""

DIAGRAM_HINT_MISCONCEPTION_IDS: frozenset[str] = frozenset(
    {
        # subtraction_with_borrowing — the borrow itself is the hardest step
        # to verbalize; a place-value column diagram shows it directly.
        "subtraction_borrowing.no_decrement_after_borrow",
        "subtraction_borrowing.stale_borrow_digit",
        "subtraction_borrowing.borrow_across_zero",
        # fractions_addition — "different-sized pieces" is exactly what the
        # pie/bar diagram shows without the child having to imagine it.
        "fractions_addition.no_common_denominator",
        # lcm_hcf — a Venn diagram shows which values fall outside the
        # overlap directly.
        "lcm_hcf.extra_non_common_value",
        # area_perimeter — a labeled rectangle disambiguates sides-vs-interior.
        "area_perimeter.formula_confusion",
        # decimals — a place-value grid makes a missing/padded column visible.
        "decimals.tenths_written_as_hundredths",
        # measurement — the conversion-arrow diagram is the exact picture
        # this misconception gets backwards.
        "measurement.wrong_direction",
        # shapes_angles — the angle-arc/shape-outline diagram lets the child
        # compare the actual angle or shape against the label they're
        # confusing, or re-count sides directly instead of from memory.
        "shapes_angles.acute_obtuse_swap",
        "shapes_angles.right_straight_swap",
        "shapes_angles.miscounts_polygon_sides",
        # symmetry — the bare shape/letter diagram is exactly what the fold
        # test needs; all three of this topic's misconceptions are about
        # visually mis-judging whether a fold or spin actually matches.
        "symmetry.assumes_nonzero_symmetry",
        "symmetry.overcounts_diagonal_lines",
        "symmetry.confuses_rotational_with_line_symmetry",
    }
)


def should_attach_diagram_hint(misconception_id: str | None) -> bool:
    """`False` for `None` (no classification, or classification produced no
    misconception id) and for any id not in the curated set above — the
    caller (`dialogue/orchestrator.py`) treats that as "don't attach a
    diagram this turn," the same way `get_analogy()` returning `None` means
    "no analogy," not an error."""
    if misconception_id is None:
        return False
    return misconception_id in DIAGRAM_HINT_MISCONCEPTION_IDS


SYMMETRY_REVEAL_REPEAT_THRESHOLD = 2
"""Same value as `orchestrator.py::REGISTER_SWITCH_REPEAT_THRESHOLD` (the
existing "switch to a concrete analogy" threshold) — deliberately reused
rather than a new tunable, so "the tutor gets more concrete after 2 misses
on the same step" stays one consistent rule across the register switch and
this reveal, not two thresholds a future change could silently drift apart."""


def should_reveal_symmetry_lines(topic: str, repeat_count: int) -> bool:
    """User-directed, explicitly-confirmed exception to "diagram hints never
    show the answer" (see this module's docstring) — scoped narrowly to
    `symmetry` alone, and only once the student has missed the same step at
    least `SYMMETRY_REVEAL_REPEAT_THRESHOLD` times in a row. This is the same
    category of deliberate leakage-filter bypass as
    `orchestrator.py::_worked_example_message()` (turn-budget escalation
    already reveals the correct step outright) — here it fires earlier, at
    the repeat-count register-switch point rather than only at full
    escalation, because for `symmetry` specifically a picture of the actual
    fold line *is* the re-teaching (there is no lower-information visual
    partial hint the way `AreaPerimeter`'s labeled rectangle is for other
    topics — see `SymmetryDiagram.tsx`'s docstring for why the bare-shape
    diagram alone carries no line data to withhold).

    Every other topic's diagram hint (`should_attach_diagram_hint()` above)
    is unaffected by this function and never reveals an answer at any
    `repeat_count` — this is not a general precedent, just a scoped,
    explicitly-approved one for this single topic."""
    return topic == "symmetry" and repeat_count >= SYMMETRY_REVEAL_REPEAT_THRESHOLD
