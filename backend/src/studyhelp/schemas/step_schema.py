"""Topic-agnostic problem / step-graph domain schema.

A problem is authored as a DAG of acceptable intermediate states (`step_graph`),
not a linear list — Class 5 problems often have more than one legitimate solution
path (ARCHITECTURE.md D11). `type` is a first-class field on every step, not
inferred, so the verifier and misconception bank stay keyed consistently.

`expected_state` / student-submitted `fields` are intentionally untyped `dict`s at
this layer: this schema must stay usable by any future topic. Per-step-type typed
field models live under `verification/topics/<topic>/` next to the checkers that
know what a given step type actually means.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class StepTypeEntry(BaseModel):
    """A `(topic, step_type_key)` vocabulary entry — validates seed fixtures
    for the `step_types` table before DB insert."""

    topic: str
    step_type_key: str
    description: str
    structured_input_schema: dict[str, Any]


class NcertRef(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    ncert_class: int = Field(alias="class")
    chapter: int
    chapter_title: str
    topic: str


class StepNode(BaseModel):
    step_id: str
    type: str
    expected_state: dict[str, Any]
    next: list[str] = Field(default_factory=list)


class AltPath(BaseModel):
    path_id: str
    entry: str
    note: str | None = None


class Problem(BaseModel):
    problem_id: str
    ncert_ref: NcertRef
    given: dict[str, Any]
    final_answer: Any
    step_graph: list[StepNode]
    alt_paths: list[AltPath] = Field(default_factory=list)

    def node(self, step_id: str) -> StepNode | None:
        return next((n for n in self.step_graph if n.step_id == step_id), None)

    def nodes_of_type(self, step_type: str) -> list[StepNode]:
        return [n for n in self.step_graph if n.type == step_type]

    def entry_step_ids(self) -> list[str]:
        """Root nodes: the canonical first step plus every named alt-path entry."""
        entries = {self.step_graph[0].step_id} if self.step_graph else set()
        entries.update(p.entry for p in self.alt_paths)
        return list(entries)
