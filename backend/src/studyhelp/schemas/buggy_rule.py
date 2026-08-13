"""Buggy-rule library domain schema (Brown & Burton / VanLehn tradition —
ARCHITECTURE.md D4). `signature_matcher` is a declarative pattern; the
matching *logic* against a (correct_step, student_step) pair is Phase 2's
`classification/rule_matcher.py`, not this schema. Used to validate seed
fixtures before DB insert."""

from typing import Any

from pydantic import BaseModel


class StepSnapshot(BaseModel):
    """A concrete step submission — same shape as `schemas.verify.StudentStep`,
    duplicated here (not imported) so buggy-rule fixtures stay self-describing
    JSON without importing pipeline-boundary types into seed data."""

    step_type: str
    fields: dict[str, Any]


class ExamplePair(BaseModel):
    problem_id: str
    correct_step: StepSnapshot
    student_step: StepSnapshot
    note: str


class BuggyRuleEntry(BaseModel):
    id: str
    topic: str
    step_type: str
    bug_code: str
    signature_matcher: dict[str, Any]
    citation: str
    misconception_id: str | None = None
    example_pair: ExamplePair
