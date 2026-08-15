"""sympy's role here is deliberately narrow (ARCHITECTURE.md D23), same as
the other topics: an independent arithmetic cross-check, not the source of
procedural correctness (that's the graph/field matching in `verifier.py`).
Every seeded problem is either a 2-digit x 1-digit multiplication or a
2-digit / 1-digit exact (no-remainder) division.
"""

from typing import TYPE_CHECKING

import sympy

if TYPE_CHECKING:
    from studyhelp.schemas.step_schema import Problem


def check_final_value(a: int, b: int, op: str, value: int) -> bool:
    """Cross-checks a result against the raw multiplication/division
    identity, independent of whatever the step graph claims."""
    if op == "x":
        return bool(sympy.Eq(sympy.Integer(a) * sympy.Integer(b), sympy.Integer(value)))
    if b == 0 or a % b != 0:
        return False
    return bool(sympy.Eq(sympy.Integer(a) / sympy.Integer(b), sympy.Integer(value)))


def validate_problem_arithmetic(problem: "Problem") -> None:
    """Seed-time gate, mirroring the other topics' function of the same
    name: every node in the graph is internally arithmetic-consistent, and
    the graph's own final answer agrees with the raw identity. Raises
    `ValueError` naming the offending node."""
    a, b, op = problem.given["a"], problem.given["b"], problem.given["op"]
    if op not in ("x", "/"):
        raise ValueError(f"{problem.problem_id}: given.op must be 'x' or '/', got {op!r}")
    if a < 10 or a > 99 or b < 1 or b > 9:
        raise ValueError(
            f"{problem.problem_id}: this topic only covers 2-digit x 1-digit multiplication / "
            f"2-digit-by-1-digit exact division, got a={a}, b={b}"
        )
    if op == "/" and a % b != 0:
        raise ValueError(f"{problem.problem_id}: division problems in this topic must be exact (no remainder)")

    final_value = problem.final_answer["value"]
    if not check_final_value(a, b, op, final_value):
        raise ValueError(
            f"{problem.problem_id}: final_answer {problem.final_answer} fails sympy identity "
            f"check against {a} {op} {b}"
        )

    tens_digit, units_digit = divmod(a, 10)

    if op == "x":
        for node in problem.step_graph:
            state = node.expected_state
            if node.type == "multiply_units":
                expected_product = units_digit * b
                if state["digit"] != units_digit or state["multiplier"] != b or state["product"] != expected_product:
                    raise ValueError(
                        f"{problem.problem_id}/{node.step_id}: multiply_units {state} is inconsistent "
                        f"with a={a}, b={b} (expected digit={units_digit}, product={expected_product})"
                    )
            if node.type == "multiply_tens":
                carry_in = (units_digit * b) // 10
                expected_product = tens_digit * b + carry_in
                if (
                    state["digit"] != tens_digit
                    or state["multiplier"] != b
                    or state["carry_in"] != carry_in
                    or state["product"] != expected_product
                ):
                    raise ValueError(
                        f"{problem.problem_id}/{node.step_id}: multiply_tens {state} is inconsistent "
                        f"with a={a}, b={b} (expected digit={tens_digit}, carry_in={carry_in}, "
                        f"product={expected_product})"
                    )
            if node.type == "write_final_answer" and not check_final_value(a, b, op, state["value"]):
                raise ValueError(
                    f"{problem.problem_id}/{node.step_id}: write_final_answer value {state['value']} "
                    f"fails sympy identity check against {a} x {b}"
                )
    else:
        tens_quotient, tens_remainder = divmod(tens_digit, b)
        units_group = tens_remainder * 10 + units_digit
        units_quotient, units_remainder = divmod(units_group, b)
        for node in problem.step_graph:
            state = node.expected_state
            if node.type == "divide_tens" and (
                state["dividend_group"] != tens_digit
                or state["divisor"] != b
                or state["quotient_digit"] != tens_quotient
                or state["remainder"] != tens_remainder
            ):
                raise ValueError(
                    f"{problem.problem_id}/{node.step_id}: divide_tens {state} is inconsistent "
                    f"with a={a}, b={b} (expected dividend_group={tens_digit}, "
                    f"quotient_digit={tens_quotient}, remainder={tens_remainder})"
                )
            if node.type == "divide_units" and (
                state["dividend_group"] != units_group
                or state["divisor"] != b
                or state["quotient_digit"] != units_quotient
                or state["remainder"] != units_remainder
            ):
                raise ValueError(
                    f"{problem.problem_id}/{node.step_id}: divide_units {state} is inconsistent "
                    f"with a={a}, b={b} (expected dividend_group={units_group}, "
                    f"quotient_digit={units_quotient}, remainder={units_remainder})"
                )
            if node.type == "write_final_answer" and not check_final_value(a, b, op, state["value"]):
                raise ValueError(
                    f"{problem.problem_id}/{node.step_id}: write_final_answer value {state['value']} "
                    f"fails sympy identity check against {a} / {b}"
                )
        if units_remainder != 0:
            raise ValueError(f"{problem.problem_id}: division doesn't come out exact (final remainder {units_remainder})")
