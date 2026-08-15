"""sympy's role here is deliberately narrow (ARCHITECTURE.md D23), same as
the other topics: an independent arithmetic cross-check, not the source of
procedural correctness (that's the graph/field matching in `verifier.py`).
"""

from typing import TYPE_CHECKING

import sympy

if TYPE_CHECKING:
    from studyhelp.schemas.step_schema import Problem


def check_final_value(length: int, width: int, measure: str, result: int) -> bool:
    """Cross-checks a result against the raw area/perimeter identity,
    independent of whatever the step graph claims."""
    if measure == "area":
        expected = sympy.Integer(length) * sympy.Integer(width)
    else:
        expected = 2 * (sympy.Integer(length) + sympy.Integer(width))
    return bool(sympy.Eq(expected, sympy.Integer(result)))


def validate_problem_arithmetic(problem: "Problem") -> None:
    """Seed-time gate, mirroring the other topics' function of the same
    name: every node in the graph is internally arithmetic-consistent, and
    the graph's own final answer agrees with the raw identity. Raises
    `ValueError` naming the offending node."""
    length = problem.given["length"]
    width = problem.given["width"]
    measure = problem.given["measure"]
    if measure not in ("area", "perimeter"):
        raise ValueError(f"{problem.problem_id}: given.measure must be 'area' or 'perimeter', got {measure!r}")

    final_value = problem.final_answer["value"]
    if not check_final_value(length, width, measure, final_value):
        raise ValueError(
            f"{problem.problem_id}: final_answer {problem.final_answer} fails sympy identity "
            f"check for {measure} of length={length}, width={width}"
        )

    compute_type = "compute_area" if measure == "area" else "compute_perimeter"
    for node in problem.step_graph:
        state = node.expected_state
        if node.type == compute_type:
            if state["length"] != length or state["width"] != width:
                raise ValueError(
                    f"{problem.problem_id}/{node.step_id}: {compute_type} length/width "
                    f"{state['length']}/{state['width']} don't match given length={length}, width={width}"
                )
            if not check_final_value(length, width, measure, state["result"]):
                raise ValueError(
                    f"{problem.problem_id}/{node.step_id}: {compute_type} result {state['result']} "
                    f"fails sympy identity check for {measure} of length={length}, width={width}"
                )
        if node.type == "write_final_answer" and not check_final_value(
            length, width, measure, state["value"]
        ):
            raise ValueError(
                f"{problem.problem_id}/{node.step_id}: write_final_answer value {state['value']} "
                f"fails sympy identity check for {measure} of length={length}, width={width}"
            )
