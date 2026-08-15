"""sympy's role here is deliberately narrow (ARCHITECTURE.md D23), same as
the subtraction topic: an independent arithmetic cross-check, not the
source of procedural correctness (that's the graph/field matching in
`verifier.py`).
"""

from typing import TYPE_CHECKING

import sympy

if TYPE_CHECKING:
    from studyhelp.schemas.step_schema import Problem


def check_final_identity(
    a_num: int, a_den: int, b_num: int, b_den: int, result_num: int, result_den: int, op: str = "+"
) -> bool:
    """Cross-checks a `write_final_answer` step's value against the raw
    fraction addition/subtraction identity, independent of whatever the
    step graph claims. `op="-"` for subtraction problems."""
    left = sympy.Rational(a_num, a_den)
    right = sympy.Rational(b_num, b_den)
    lhs = left + right if op == "+" else left - right
    rhs = sympy.Rational(result_num, result_den)
    return bool(sympy.Eq(lhs, rhs))


def check_common_denominator_equivalent(orig_num: int, orig_den: int, common_num: int, common_den: int) -> bool:
    """Used at seed-validation time: the rewritten fraction must be an
    equivalent form of the original, not just any fraction."""
    return bool(sympy.Eq(sympy.Rational(orig_num, orig_den), sympy.Rational(common_num, common_den)))


def check_addition_arithmetic(left_num: int, left_den: int, right_num: int, right_den: int, sum_num: int, sum_den: int) -> bool:
    """Used at seed-validation time to confirm an `add_numerators` node is
    internally consistent with the `rewrite_common_denominator` node that
    feeds it."""
    if left_den != right_den or sum_den != left_den:
        return False
    return bool(sympy.Eq(sympy.Integer(sum_num), sympy.Integer(left_num) + sympy.Integer(right_num)))


def check_subtraction_arithmetic(left_num: int, left_den: int, right_num: int, right_den: int, diff_num: int, diff_den: int) -> bool:
    """Used at seed-validation time to confirm a `subtract_numerators` node
    is internally consistent with the `rewrite_common_denominator` node
    that feeds it."""
    if left_den != right_den or diff_den != left_den:
        return False
    return bool(sympy.Eq(sympy.Integer(diff_num), sympy.Integer(left_num) - sympy.Integer(right_num)))


def check_comparison(a_num: int, a_den: int, op: str, b_num: int, b_den: int) -> bool:
    """Used both at seed-validation time and (indirectly, via the verifier
    trusting a correctly-authored `expected_state`) to confirm a
    `compare_fractions` node's stated comparison actually holds."""
    left = sympy.Rational(a_num, a_den)
    right = sympy.Rational(b_num, b_den)
    if op == "<":
        return bool(left < right)
    if op == ">":
        return bool(left > right)
    return bool(sympy.Eq(left, right))


def check_simplify_arithmetic(num: int, den: int, simplified_num: int, simplified_den: int) -> bool:
    """Used at seed-validation time: the simplified fraction must equal the
    unsimplified one and be in lowest terms."""
    equal = sympy.Eq(sympy.Rational(num, den), sympy.Rational(simplified_num, simplified_den))
    reduced = sympy.gcd(simplified_num, simplified_den) == 1
    return bool(equal) and bool(reduced)


def validate_problem_arithmetic(problem: "Problem") -> None:
    """Seed-time gate, mirroring the subtraction topic's function of the
    same name: every node in the graph is internally arithmetic-consistent,
    and the graph's own final answer agrees with the raw identity. Raises
    `ValueError` naming the offending node.

    Dispatches on `given["op"]` ("+"/"-"/"compare", default "+" so the
    original 4 addition-only fixtures don't need updating) — the topic now
    covers all three of NCERT Ch.4's operations, not just addition."""
    a_num, a_den = problem.given["a_num"], problem.given["a_den"]
    b_num, b_den = problem.given["b_num"], problem.given["b_den"]
    op = problem.given.get("op", "+")

    if op == "compare":
        _validate_comparison_problem(problem, a_num, a_den, b_num, b_den)
        return

    final = problem.final_answer
    if not check_final_identity(a_num, a_den, b_num, b_den, final["num"], final["den"], op=op):
        raise ValueError(
            f"{problem.problem_id}: final_answer {final} fails sympy identity check against "
            f"{a_num}/{a_den} {op} {b_num}/{b_den}"
        )

    combine_type = "add_numerators" if op == "+" else "subtract_numerators"
    combine_check = check_addition_arithmetic if op == "+" else check_subtraction_arithmetic

    for node in problem.step_graph:
        state = node.expected_state
        if node.type == "rewrite_common_denominator" and not (
            check_common_denominator_equivalent(a_num, a_den, state["left_num"], state["left_den"])
            and check_common_denominator_equivalent(b_num, b_den, state["right_num"], state["right_den"])
        ):
            raise ValueError(
                f"{problem.problem_id}/{node.step_id}: rewritten fractions aren't equivalent "
                "to the original given fractions"
            )
        if node.type == combine_type:
            rewrite_node = next(
                (n for n in problem.step_graph if n.type == "rewrite_common_denominator"), None
            )
            if rewrite_node is None:
                raise ValueError(f"{problem.problem_id}: no rewrite_common_denominator node found")
            rs = rewrite_node.expected_state
            if not combine_check(
                rs["left_num"], rs["left_den"], rs["right_num"], rs["right_den"], state["num"], state["den"]
            ):
                raise ValueError(f"{problem.problem_id}/{node.step_id}: {combine_type} arithmetic is inconsistent")
        if node.type == "simplify_fraction":
            combine_node = next((n for n in problem.step_graph if n.type == combine_type), None)
            if combine_node is None:
                raise ValueError(f"{problem.problem_id}: no {combine_type} node found")
            csrc = combine_node.expected_state
            if not check_simplify_arithmetic(csrc["num"], csrc["den"], state["num"], state["den"]):
                raise ValueError(f"{problem.problem_id}/{node.step_id}: simplify_fraction arithmetic is inconsistent")


def _validate_comparison_problem(problem: "Problem", a_num: int, a_den: int, b_num: int, b_den: int) -> None:
    compare_node = next((n for n in problem.step_graph if n.type == "compare_fractions"), None)
    if compare_node is None:
        raise ValueError(f"{problem.problem_id}: comparison problem has no compare_fractions node")
    state = compare_node.expected_state
    if (state["left_num"], state["left_den"]) != (a_num, a_den) or (
        state["right_num"],
        state["right_den"],
    ) != (b_num, b_den):
        raise ValueError(
            f"{problem.problem_id}/{compare_node.step_id}: compare_fractions fractions don't match "
            "the problem's given fractions"
        )
    if not check_comparison(a_num, a_den, state["op"], b_num, b_den):
        raise ValueError(
            f"{problem.problem_id}/{compare_node.step_id}: stated comparison '{state['op']}' "
            f"doesn't hold for {a_num}/{a_den} vs {b_num}/{b_den}"
        )
