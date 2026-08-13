"""Named confidence thresholds — the false-negative bias (ARCHITECTURE.md D2)
implemented as explicit, tested constants rather than emergent behavior."""

ACCEPT_THRESHOLD: float = 0.9
"""Confidence at or above which a match is a clean, unambiguous accept."""

REJECT_THRESHOLD: float = 0.75
"""Minimum confidence-of-wrongness required to flag a step as an error.
Below this, the verifier does not interrupt — bias toward false negatives
(CLAUDE.md; ARCHITECTURE.md D2). Wrongly telling a child a correct step is
wrong is worse than occasionally missing a real error."""

NON_ADJACENT_MATCH_CONFIDENCE: float = 0.85
"""Confidence assigned to an exact match against a graph-valid but
non-adjacent node (step-graph DAG, ARCHITECTURE.md D11). Accepted, but below
ACCEPT_THRESHOLD so it's surfaced (`non_adjacent_valid_match`) for review
rather than treated identically to a clean frontier hit."""
