"""Serialization tests for the domain step-schema, against the canonical
542 - 187 worked example (a real problem fixture, not a synthetic stub)."""

import pytest
from pydantic import ValidationError

from studyhelp.schemas.step_schema import AltPath, NcertRef, Problem, StepNode


def test_loads_and_validates(problem_542_187: Problem) -> None:
    assert problem_542_187.problem_id == "subtraction-borrow-014"
    assert problem_542_187.ncert_ref.ncert_class == 5
    assert problem_542_187.ncert_ref.topic == "subtraction_with_borrowing"
    assert problem_542_187.final_answer == 355
    assert len(problem_542_187.step_graph) == 9


def test_ncert_ref_alias_round_trips() -> None:
    ref = NcertRef.model_validate(
        {
            "class": 5,
            "chapter": 1,
            "chapter_title": "The Fish Tale",
            "topic": "subtraction_with_borrowing",
        }
    )
    assert ref.ncert_class == 5
    # by_alias=True on dump so "class" (a Python keyword) round-trips correctly
    dumped = ref.model_dump(by_alias=True)
    assert dumped["class"] == 5


def test_step_graph_is_a_dag_not_a_list(problem_542_187: Problem) -> None:
    """The DAG shape (ARCHITECTURE.md D11): more than one node can share a
    `next` successor, and the canonical linear path coexists with an
    alternate combined-step path that rejoins it."""
    granular_units_step = problem_542_187.node("s2_borrow_units")
    combined_units_step = problem_542_187.node("s2b_borrow_and_subtract_units")
    assert granular_units_step is not None
    assert combined_units_step is not None
    # both borrow-at-units nodes are distinct but converge on the same successor
    assert granular_units_step.next != [combined_units_step.step_id]
    assert combined_units_step.next == ["s4_cmp_tens"]


def test_entry_step_ids_include_alt_path_entries(problem_542_187: Problem) -> None:
    entries = problem_542_187.entry_step_ids()
    assert "s1_cmp_units" in entries
    assert "s2b_borrow_and_subtract_units" in entries


def test_nodes_of_type_finds_all_matching_step_types(problem_542_187: Problem) -> None:
    borrow_nodes = problem_542_187.nodes_of_type("borrow")
    # two borrow columns (units, tens) plus the alt-path combined borrow node
    assert {n.step_id for n in borrow_nodes} == {
        "s2_borrow_units",
        "s5_borrow_tens",
        "s2b_borrow_and_subtract_units",
    }


def test_step_node_defaults_next_to_empty_list() -> None:
    node = StepNode(step_id="terminal", type="write_final_answer", expected_state={"value": 355})
    assert node.next == []


def test_alt_path_note_is_optional() -> None:
    path = AltPath(path_id="granular", entry="s1_cmp_units")
    assert path.note is None


def test_missing_required_field_rejected() -> None:
    with pytest.raises(ValidationError):
        Problem.model_validate({"problem_id": "incomplete"})


def test_round_trip_serialization(problem_542_187: Problem) -> None:
    dumped = problem_542_187.model_dump(mode="json", by_alias=True)
    reloaded = Problem.model_validate(dumped)
    assert reloaded == problem_542_187
