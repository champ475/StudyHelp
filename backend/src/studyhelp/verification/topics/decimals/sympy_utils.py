"""sympy's role here is deliberately narrow (ARCHITECTURE.md D23), same as
the other topics: an independent arithmetic cross-check, not the source of
procedural correctness (that's the graph/field matching in `verifier.py`).
Every decimal is represented as an integer count of hundredths; sympy
`Rational(n, 100)` gives exact (never floating-point) arithmetic for the
cross-check.
"""

from typing import TYPE_CHECKING

import sympy

if TYPE_CHECKING:
    from studyhelp.schemas.step_schema import Problem


def check_final_identity(a_hundredths: int, b_hundredths: int, op: str, result_hundredths: int) -> bool:
    """Cross-checks a result against the raw decimal addition/subtraction
    identity, independent of whatever the step graph claims."""
    a = sympy.Rational(a_hundredths, 100)
    b = sympy.Rational(b_hundredths, 100)
    lhs = a + b if op == "+" else a - b
    rhs = sympy.Rational(result_hundredths, 100)
    return bool(sympy.Eq(lhs, rhs))


def validate_problem_arithmetic(problem: "Problem") -> None:
    """Seed-time gate, mirroring the other topics' function of the same
    name: every node in the graph is internally arithmetic-consistent, and
    the graph's own final answer agrees with the raw identity. Raises
    `ValueError` naming the offending node."""
    a_hundredths = problem.given["a_hundredths"]
    b_hundredths = problem.given["b_hundredths"]
    op = problem.given["op"]
    if op not in ("+", "-"):
        raise ValueError(f"{problem.problem_id}: given.op must be '+' or '-', got {op!r}")

    final_result = problem.final_answer["result_hundredths"]
    if not check_final_identity(a_hundredths, b_hundredths, op, final_result):
        raise ValueError(
            f"{problem.problem_id}: final_answer {problem.final_answer} fails sympy identity "
            f"check against {a_hundredths} {op} {b_hundredths} (hundredths)"
        )

    for node in problem.step_graph:
        state = node.expected_state
        if node.type == "align_place_value" and (
            state["a_hundredths"] != a_hundredths or state["b_hundredths"] != b_hundredths
        ):
            raise ValueError(
                f"{problem.problem_id}/{node.step_id}: align_place_value {state} doesn't match "
                f"given a_hundredths={a_hundredths}, b_hundredths={b_hundredths}"
            )
        if node.type in ("compute_result", "write_final_answer") and not check_final_identity(
            a_hundredths, b_hundredths, op, state["result_hundredths"]
        ):
            raise ValueError(
                f"{problem.problem_id}/{node.step_id}: {node.type} value "
                f"{state['result_hundredths']} fails sympy identity check against "
                f"{a_hundredths} {op} {b_hundredths} (hundredths)"
            )
