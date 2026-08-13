"""Configurable intervention-timing policy (ARCHITECTURE.md D10) — not a
hardcoded "always interrupt immediately" default. The orchestrator consults
this before ever entering `ErrorDetected`. Mirrors the three policies named
in technical_architecture.md §6.

Note on the eventual three-condition RCT (docs/approach.md §3): the study's
"immediate" and "delayed" arms map onto `IMMEDIATE` and
`WAIT_FOR_COMPLETION` respectively; the "control" arm (plain right/wrong
marking, no Socratic dialogue at all) means *not invoking the dialogue
orchestrator in the first place* — that's a routing decision one layer up
(Phase 6/pilot scope), not another value of this policy.
"""

import enum


class InterventionPolicy(enum.StrEnum):
    IMMEDIATE = "immediate"
    """Interrupt on the first error."""

    AFTER_NTH_REPEAT = "after_nth_repeat"
    """Interrupt only once the same step has been gotten wrong
    `repeat_threshold` times in a row."""

    WAIT_FOR_COMPLETION = "wait_for_completion"
    """Don't interrupt mid-problem at all; only intervene once the whole
    problem has been submitted."""


DEFAULT_REPEAT_THRESHOLD = 2


def should_intervene(
    policy: InterventionPolicy,
    *,
    consecutive_errors_on_this_step: int,
    problem_is_complete: bool,
    repeat_threshold: int = DEFAULT_REPEAT_THRESHOLD,
) -> bool:
    """Whether the orchestrator should enter `ErrorDetected` for this wrong
    step right now, under the given policy."""
    if policy == InterventionPolicy.IMMEDIATE:
        return True
    if policy == InterventionPolicy.AFTER_NTH_REPEAT:
        return consecutive_errors_on_this_step >= repeat_threshold
    if policy == InterventionPolicy.WAIT_FOR_COMPLETION:
        return problem_is_complete
    raise ValueError(f"Unknown intervention policy: {policy}")
