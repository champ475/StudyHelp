"""Misconception bank domain schema (technical_architecture.md §5): a
structured table, not a flat text file, keyed by (topic, step_type) for
retrieve-don't-dump lookup. Used to validate seed fixtures before DB
insert; the DB row shape (`db/models/misconception.py`) mirrors this."""

from typing import Any, Literal

from pydantic import BaseModel


class DialogueTurn(BaseModel):
    role: Literal["tutor", "student"]
    text: str


class MisconceptionEntry(BaseModel):
    id: str
    topic: str
    step_type: str
    bug_signature: dict[str, Any] | None = None
    typical_mindset: str
    explanation_strategy: str
    example_dialogue: list[DialogueTurn]
    """A demonstration of tone and approach, not a script to recite
    verbatim (technical_architecture.md §5)."""
    source: str
    version: int = 1
    review_status: Literal["seed_curated", "pilot_derived", "reviewed", "pending"] = "seed_curated"
