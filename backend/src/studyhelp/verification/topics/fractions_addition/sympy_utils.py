"""sympy's role here is deliberately narrow (ARCHITECTURE.md D23), same as
the subtraction topic: an independent arithmetic cross-check, not the
source of procedural correctness (that's the graph/field matching in
`verifier.py`).
"""

from typing import TYPE_CHECKING

import sympy

if TYPE_CHECKING:
    from studyhelp.schemas.step_schema import Problem


def check_final_identity(a_num: int, a_den: int, b_num: int, b_den: int, result_num: int, result_den: int) -> bool:
    """Cross-checks a `write_final_answer` step's value against the raw
    fraction-addition identity, independent of whatever the step graph
    claims."""
    lhs = sympy.Rational(a_num, a_den) + sympy.Rational(b_num, b_den)
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
    `ValueError` naming the offending node."""
    a_num, a_den = problem.given["a_num"], problem.given["a_den"]
    b_num, b_den = problem.given["b_num"], problem.given["b_den"]
    final = problem.final_answer
    if not check_final_identity(a_num, a_den, b_num, b_den, final["num"], final["den"]):
        raise ValueError(
            f"{problem.problem_id}: final_answer {final} fails sympy identity check against "
            f"{a_num}/{a_den} + {b_num}/{b_den}"
        )

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
        if node.type == "add_numerators":
            rewrite_node = next(
                (n for n in problem.step_graph if n.type == "rewrite_common_denominator"), None
            )
            if rewrite_node is None:
                raise ValueError(f"{problem.problem_id}: no rewrite_common_denominator node found")
            rs = rewrite_node.expected_state
            if not check_addition_arithmetic(
                rs["left_num"], rs["left_den"], rs["right_num"], rs["right_den"], state["num"], state["den"]
            ):
                raise ValueError(f"{problem.problem_id}/{node.step_id}: add_numerators arithmetic is inconsistent")
        if node.type == "simplify_fraction":
            add_node = next((n for n in problem.step_graph if n.type == "add_numerators"), None)
            if add_node is None:
                raise ValueError(f"{problem.problem_id}: no add_numerators node found")
            asrc = add_node.expected_state
            if not check_simplify_arithmetic(asrc["num"], asrc["den"], state["num"], state["den"]):
                raise ValueError(f"{problem.problem_id}/{node.step_id}: simplify_fraction arithmetic is inconsistent")
