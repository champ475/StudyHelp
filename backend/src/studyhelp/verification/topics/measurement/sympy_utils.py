"""sympy's role here is deliberately narrow (ARCHITECTURE.md D23), same as
the other topics: an independent arithmetic cross-check, not the source of
procedural correctness (that's the graph/field matching in `verifier.py`).
"""

from typing import TYPE_CHECKING

import sympy

if TYPE_CHECKING:
    from studyhelp.schemas.step_schema import Problem


def check_final_value(value: int, direction: str, factor: int, result: int) -> bool:
    """Cross-checks a converted result against the raw conversion identity,
    independent of whatever the step graph claims."""
    if direction == "x":
        expected = sympy.Integer(value) * sympy.Integer(factor)
    else:
        if factor == 0 or value % factor != 0:
            return False
        expected = sympy.Integer(value) / sympy.Integer(factor)
    return bool(sympy.Eq(expected, sympy.Integer(result)))


def validate_problem_arithmetic(problem: "Problem") -> None:
    """Seed-time gate, mirroring the other topics' function of the same
    name: every node in the graph is internally arithmetic-consistent, and
    the graph's own final answer agrees with the raw identity. Raises
    `ValueError` naming the offending node."""
    value = problem.given["value"]
    direction = problem.given["direction"]
    factor = problem.given["factor"]
    if direction not in ("x", "/"):
        raise ValueError(f"{problem.problem_id}: given.direction must be 'x' or '/', got {direction!r}")

    final_value = problem.final_answer["value"]
    if not check_final_value(value, direction, factor, final_value):
        raise ValueError(
            f"{problem.problem_id}: final_answer {problem.final_answer} fails sympy identity "
            f"check against {value} {direction} {factor}"
        )

    for node in problem.step_graph:
        state = node.expected_state
        if node.type == "identify_conversion_factor" and (
            state["direction"] != direction or state["factor"] != factor
        ):
            raise ValueError(
                f"{problem.problem_id}/{node.step_id}: identify_conversion_factor {state} doesn't "
                f"match given direction={direction}, factor={factor}"
            )
        if node.type in ("convert_units", "write_final_answer") and not check_final_value(
            value, direction, factor, state["value"]
        ):
            raise ValueError(
                f"{problem.problem_id}/{node.step_id}: {node.type} value {state['value']} fails "
                f"sympy identity check against {value} {direction} {factor}"
            )
