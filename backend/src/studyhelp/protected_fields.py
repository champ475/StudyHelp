"""Single source of truth for which `expected_state`/`given` field names are
answer-bearing, shared by two independent leakage vectors:

1. `dialogue/orchestrator.py::_protected_values()` — what the LLM-generated
   child-facing message must never contain (the leakage filter gate).
2. `api/routes/problems.py::get_problem_public()` — what the public,
   browser-reachable problem catalog must redact from `Problem.given`
   before sending it to the frontend at all.

The second vector was a real, separate bug found live (CLAUDE.md
live-testing round, full-system audit): `measurement` problems' `given`
dict includes `direction`/`factor`, which are *also* the exact
`expected_state` of that problem's first step (`identify_conversion_factor`)
— meaning the answer to every measurement problem's first step was already
readable straight out of the browser's network tab on page load, before the
student ever attempted it, with no LLM or dialogue turn involved at all.
`given` is meant to hold only the problem's genuinely visible input (the
numbers/units the question states), never a field that happens to double as
some step's correct output — but nothing previously enforced that
distinction, so a future topic's fixture could reintroduce the same class
of leak by accident. Keeping one shared classification, consulted by both
call sites, closes that off structurally instead of per-topic vigilance.
"""

PROTECTED_INT_KEYS: tuple[str, ...] = (
    "result_digit",
    "value",
    "to_digit_after",
    "from_digit_after",
    "combined_result_digit",
    "num",
    "den",
    "left_num",
    "left_den",
    "right_num",
    "right_den",
    "result",
    "result_hundredths",
    "product",
    "quotient_digit",
    "remainder",
    "carry_in",
    "factor",
)
"""Field names, shared across every topic's `expected_state`, whose *int*
value is output-defining (the answer, or part of it) rather than a visible
input the student already sees on the widget."""

PROTECTED_STR_VALUES_BY_KEY: dict[str, tuple[str, ...]] = {
    # fractions' `compare_fractions` step: "<"/">"/"=" is literally the
    # answer to a comparison problem. Excludes "+"/"-" (`op` on
    # `rewrite_common_denominator`, and on `multiplication_division`'s and
    # `lcm_hcf`'s `given`), which is the problem's *given* operation,
    # visible to the student before they submit anything.
    "op": ("<", ">", "="),
    # measurement's `identify_conversion_factor` step: "x"/"/" is literally
    # the answer to "which operation do I use here".
    "direction": ("x", "/"),
}
"""Field names whose value is a protected *answer* only for specific
string values — the same field name can also appear as non-secret, already-
visible input under a different value (see `op`'s docstring above)."""
