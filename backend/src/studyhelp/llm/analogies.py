"""Small, curated per-topic concrete-analogy library (ARCHITECTURE.md D60).

CLAUDE.md's Bug2 fix: when a student gets the *same* step wrong more than
once, the tutor's register must switch from abstract/numeric re-explanation
to a concrete, real-world analogy grounded in the topic — a fraction becomes
a pizza, subtraction-with-borrowing becomes trading coins, multiplication
becomes counting equal groups. This library is deliberately small and
hand-authored, not LLM-invented per turn: a repeat-count-triggered switch to
"whatever analogy the model feels like inventing this turn" would be
unpredictable and could itself leak toward the answer (an ad hoc analogy
that happens to use the problem's own numbers). Application code
(`dialogue/orchestrator.py`) looks up the entry deterministically by topic
and hands it to both the `decide()` and `generate()` calls as a fixed
ingredient — the LLM's job is to *use* the given analogy well, not to
choose or invent one.

Two constraints every entry must keep, both enforced by
`tests/unit/llm/test_analogies.py`:
- No bare digits. The leakage filter (`dialogue/leakage_filter.py`) rejects
  any generated message that mentions one of the current problem's own
  protected numbers — often small single digits (a borrow digit, a result
  digit) — so a numeral used only for analogy flavor risks a coincidental
  collision that gets an otherwise-safe message rejected for an unrelated
  reason. Spelled-out amounts ("a few", "more than that") say the same
  thing without that risk.
- Short, simple sentences. This text gets folded directly into a
  child-facing message and must clear the readability gate
  (`dialogue/readability_gate.py`, Class-5 Flesch-Kincaid ceiling) on its
  own, with room left for the sentence that introduces/closes it.

Keyed by the exact `topic` string each verifier registers under
(`verification/__init__.py`)."""

TOPIC_ANALOGIES: dict[str, str] = {
    "subtraction_with_borrowing": (
        "Think about trading coins. You have a few one-rupee coins. You need to give away more "
        "coins than that. You can't do it yet. So you trade one ten-rupee note for ten one-rupee "
        "coins. Now you have enough coins. Borrowing works the same way, but with digits."
    ),
    "fractions_addition": (
        "Think about a pizza cut into equal slices. The bottom number is how many slices the "
        "whole pizza was cut into. The top number is how many slices you have. Two pizzas cut "
        "into a different number of slices can't be added slice-for-slice right away. That is "
        "why fractions need the same bottom number before you add or compare them."
    ),
    "lcm_hcf": (
        "Think about two buses at the same bus stop. One bus comes back again and again on its "
        "own schedule. The other bus comes back on a different schedule. The LCM is the first "
        "time both buses arrive together again. The HCF is like splitting two teams into the "
        "biggest equal-sized groups, with nobody left over on either team."
    ),
    "decimals": (
        "Think about rupees and paise. A whole rupee is the number before the dot. The first "
        "digit after the dot counts small groups of paise. The second digit after the dot counts "
        "single paise coins. You can only add or compare amounts once the paise columns line up "
        "the same way, just like lining up the decimal points."
    ),
    "area_perimeter": (
        "Think about a garden. Perimeter is how far you would walk if you walked once around the "
        "edge of the garden. Area is how many square floor tiles it would take to cover the whole "
        "garden inside that edge."
    ),
    "multiplication_division": (
        "Think about counters arranged in equal rows. Multiplication counts how many counters are "
        "in several equal groups all together. Division is the opposite. You start with a pile of "
        "counters and share them out evenly into equal groups, to see how many groups you get."
    ),
    "measurement": (
        "Think about a shopkeeper's weighing scale. Changing between units, like metres and "
        "centimetres, is like reading the same weight on a different scale. The real amount does "
        "not change. Only how many small units it takes to say the same thing changes."
    ),
}


def get_analogy(topic: str) -> str | None:
    """`None` for a topic with no library entry (e.g. the light-check
    chapters, which aren't multi-step numeric procedures) — the caller
    treats that as "no analogy available," not an error."""
    return TOPIC_ANALOGIES.get(topic)
