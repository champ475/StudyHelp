"""Deterministic, per-turn readability gate (ARCHITECTURE.md D9): a
measurable Flesch-Kincaid check against a Class-5-appropriate reading-level
ceiling, not just a prompt instruction — Parra et al. 2026 found LLM tutor
responses need a *higher* reading level than human tutors' by default;
models don't self-correct for this without being forced to."""

import textstat


def flesch_kincaid_grade(message: str) -> float:
    return float(textstat.flesch_kincaid_grade(message))


def passes_readability(message: str, max_grade: float) -> bool:
    return flesch_kincaid_grade(message) <= max_grade
