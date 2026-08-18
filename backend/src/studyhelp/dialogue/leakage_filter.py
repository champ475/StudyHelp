"""Deterministic, per-turn answer-leakage filter (ARCHITECTURE.md D8):
checks a generated message against known correct/secret values from the
problem schema before it can ever reach the child. Cheap to run before any
message is sent — prompting alone ("don't reveal the answer") is not
sufficient once a dialogue runs several turns (Hazra et al. 2026,
SafeTutors).

Deliberately topic-agnostic: callers (the orchestrator, which knows the
current step_type's schema) decide which field values actually constitute
"the answer" for this step and pass them in as `protected_values` — this
module only does the string/number matching, so it never needs updating
when a new topic is added. Most protected values are numbers (a digit, a
fraction's numerator); `compare_fractions` (fractions topic) is the one
step type whose answer is a symbol ("<"/">"/"=") rather than a number, so
string values are matched too, by substring containment — a bare
comparison symbol in an otherwise-prose child-facing message is already
atypical, so this is a safe deterministic gate, not just a numeric one.
"""

import re

_NUMBER_RE = re.compile(r"-?\d+")
_ANSWER_PHRASES = re.compile(r"\b(the answer is|the result is|equals|is equal to)\b", re.IGNORECASE)


def contains_leakage(message: str, protected_values: list[int | str]) -> bool:
    """True if the message either (a) uses an explicit answer-revealing
    phrase at all, regardless of the specific number that follows, (b)
    mentions one of `protected_values` as a bare number, or (c) contains
    one of `protected_values`' string values verbatim (e.g. a comparison
    symbol)."""
    if _ANSWER_PHRASES.search(message):
        return True
    mentioned_numbers = {int(match) for match in _NUMBER_RE.findall(message)}
    lowered_message = message.lower()
    for value in protected_values:
        if isinstance(value, int):
            if value in mentioned_numbers:
                return True
        elif value.lower() in lowered_message:
            return True
    return False
