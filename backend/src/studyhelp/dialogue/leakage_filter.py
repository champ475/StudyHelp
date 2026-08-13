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
when a new topic is added.
"""

import re

_NUMBER_RE = re.compile(r"-?\d+")
_ANSWER_PHRASES = re.compile(r"\b(the answer is|the result is|equals|is equal to)\b", re.IGNORECASE)


def contains_leakage(message: str, protected_values: list[int]) -> bool:
    """True if the message either (a) uses an explicit answer-revealing
    phrase at all, regardless of the specific number that follows, or
    (b) mentions one of `protected_values` as a bare number."""
    if _ANSWER_PHRASES.search(message):
        return True
    mentioned = {int(match) for match in _NUMBER_RE.findall(message)}
    return any(value in mentioned for value in protected_values)
