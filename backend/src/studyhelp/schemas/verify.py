"""Verifier pipeline boundary types.

`verify_step()` is a hard pipeline gate called directly by application code —
never a tool the LLM decides when to invoke (ARCHITECTURE.md D1). Everything
here is deterministic, structured data; no free text.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from studyhelp.schemas.step_schema import Problem


class StudentStep(BaseModel):
    """A structured step submission.

    `fields` arrives as an unambiguous structured JSON value from the
    math-aware input widget (ARCHITECTURE.md D12) — never a raw string to
    parse. Per-step-type typed field models live next to each topic's
    checkers, which parse `fields` into them at point of use.
    """

    step_type: str
    fields: dict[str, Any]


class ProblemState(BaseModel):
    problem: Problem
    accepted_step_ids: list[str] = Field(default_factory=list)


class FieldDiscrepancy(BaseModel):
    field: str
    expected: Any
    actual: Any


class ErrorSignal(BaseModel):
    """Descriptive, not diagnostic.

    Reports which fields differ from which candidate step; says nothing about
    *why* the student got it wrong. Misconception classification is a
    downstream, LLM-touching concern (Phase 2) — the verifier stays dumb and
    deterministic (ARCHITECTURE.md D1).
    """

    kind: Literal["field_mismatch", "wrong_step_type", "malformed", "none"]
    discrepant_fields: list[FieldDiscrepancy] = Field(default_factory=list)
    nearest_matched_step_id: str | None = None
    note: str | None = None
    """e.g. "non_adjacent_valid_match", "low_confidence_passthrough"."""


class VerifyResult(BaseModel):
    is_valid: bool
    matched_step_id: str | None
    confidence: float
    error_signal: ErrorSignal | None = None
    parsed_fields: dict[str, Any] | None = None
    """Populated only by topics whose `StudentStep.fields` isn't already the
    structured shape downstream consumers need (e.g. fractions' free-text
    `{"text": ...}` — ARCHITECTURE.md's free-text-input supersede entry).
    Structured-widget topics leave this `None`; callers fall back to
    `StudentStep.fields` in that case, which is already structured."""
