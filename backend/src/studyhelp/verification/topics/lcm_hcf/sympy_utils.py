"""sympy's role here is deliberately narrow (ARCHITECTURE.md D23), same as
the other topics: an independent arithmetic cross-check, not the source of
procedural correctness (that's the graph/field matching in `verifier.py`).
"""

from typing import TYPE_CHECKING

import sympy

if TYPE_CHECKING:
    from studyhelp.schemas.step_schema import Problem


def common_factors(a: int, b: int) -> list[int]:
    """All positive integers that divide both a and b, ascending."""
    hcf = int(sympy.gcd(a, b))
    return [d for d in range(1, hcf + 1) if hcf % d == 0]


def smallest_common_multiples(a: int, b: int, count: int = 3) -> list[int]:
    """The `count` smallest positive common multiples of a and b, ascending."""
    lcm = int(sympy.lcm(a, b))
    return [lcm * k for k in range(1, count + 1)]


def check_final_value(a: int, b: int, op: str, value: int) -> bool:
    """Cross-checks a `write_final_answer` step's value against the raw
    LCM/HCF identity, independent of whatever the step graph claims."""
    if op == "lcm":
        return int(sympy.lcm(a, b)) == value
    return int(sympy.gcd(a, b)) == value


def validate_problem_arithmetic(problem: "Problem") -> None:
    """Seed-time gate, mirroring the other topics' function of the same
    name: every node in the graph is internally arithmetic-consistent, and
    the graph's own final answer agrees with the raw identity. Raises
    `ValueError` naming the offending node."""
    a, b, op = problem.given["a"], problem.given["b"], problem.given["op"]
    if op not in ("lcm", "hcf"):
        raise ValueError(f"{problem.problem_id}: given.op must be 'lcm' or 'hcf', got {op!r}")

    final_value = problem.final_answer["value"]
    if not check_final_value(a, b, op, final_value):
        raise ValueError(
            f"{problem.problem_id}: final_answer {problem.final_answer} fails sympy "
            f"identity check for {op}({a}, {b})"
        )

    for node in problem.step_graph:
        state = node.expected_state
        if node.type == "find_common_values":
            expected_values = smallest_common_multiples(a, b) if op == "lcm" else common_factors(a, b)
            if state["values"] != expected_values:
                raise ValueError(
                    f"{problem.problem_id}/{node.step_id}: find_common_values expected "
                    f"{expected_values}, fixture has {state['values']}"
                )
        if node.type == "write_final_answer" and not check_final_value(a, b, op, state["value"]):
            raise ValueError(
                f"{problem.problem_id}/{node.step_id}: write_final_answer value "
                f"{state['value']} fails sympy identity check for {op}({a}, {b})"
            )
