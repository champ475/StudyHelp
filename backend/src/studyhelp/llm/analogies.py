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
    "patterns": (
        "Think about a staircase. Each step is the same height as the one before it. That steady "
        "jump from step to step is the pattern's rule. Once you know that jump, you can guess the "
        "next step without climbing all the way there."
    ),
    # Deliberately never names a category word (the ones a real problem
    # here could ask the student to classify an angle as) — this topic's
    # possible answers are a small closed set of English words, not just
    # numbers, so naming one directly in the analogy risks leaking the
    # actual answer whenever that word happens to be it (confirmed live:
    # an earlier draft that said "...is acute" got rejected by the
    # leakage filter on exactly a problem whose real answer was "acute").
    "shapes_angles": (
        "Think about a clock's two hands. The corner they make between them can be small and "
        "narrow, or wide and open. A very wide corner can even open all the way around, almost "
        "back to where it started. Compare the corner in your own angle to a clock's hands to see "
        "how far it opens."
    ),
    "how_many_squares": (
        "Think about a chessboard. You can count the small squares one at a time. You can also "
        "join four small squares together to make one bigger square. Keep looking for bigger "
        "squares hiding inside the grid, not just the smallest ones."
    ),
    # Avoids the word "no" as a substring on purpose — some symmetry
    # problems here ask a yes/no question, and contains_leakage() does
    # plain substring matching, so an innocent word like "nothing" would
    # otherwise falsely collide with a protected answer of "no".
    "symmetry": (
        "Think about folding a piece of paper in half. If both sides match exactly and line up "
        "all the way, that fold line is a line of symmetry. Some shapes only fold perfectly one "
        "way. Other shapes fold perfectly along more than one line."
    ),
    "mapping": (
        "Think about giving directions to a friend. You say how many steps to take one way. Then "
        "you say how many steps to take another way. Following each direction in order gets your "
        "friend to the right spot."
    ),
    "boxes_sketches": (
        "Think about a flat piece of cardboard before it is folded into a box. Flat, it is just a "
        "few joined shapes. Once folded, those flat shapes become the box's faces. The lines where "
        "they meet become its edges."
    ),
    "smart_charts": (
        "Think about jars of marbles, one color for each group. A chart is just a picture of those "
        "jars side by side. You can see which jar has the most, or the fewest, without counting "
        "every single marble."
    ),
}


def get_analogy(topic: str) -> str | None:
    """`None` for a topic string with no library entry — the caller treats
    that as "no analogy available," not an error. Every registered topic
    (`verification/__init__.py`) has an entry, including the 7 light-check
    chapters (added after the e2e sweep found a student stuck on the same
    light-check mistake twice got the identical generic re-explanation
    verbatim, with no register to switch to)."""
    return TOPIC_ANALOGIES.get(topic)
