"""Deterministic verifier for NCERT Class 5 Ch.10 ("Tenths and Hundredths"
-- decimal addition/subtraction). Mirrors `LcmHcfVerifier`'s /
`FractionsAdditionVerifier`'s pattern exactly (ARCHITECTURE.md D41): no
client-declared `step_type`, tries every step type's grammar against the
submitted text, restricts candidate search to the DAG frontier (this
topic's DAG is linear with no step-type recurrence), and rejects any
non-exact frontier-parseable match rather than a low-confidence passthrough
(D40's rationale: once text parses cleanly into a step's exact grammar, a
value mismatch is unambiguous).
"""

from pydantic import ValidationError

from studyhelp.schemas.step_schema import Problem, StepNode
from studyhelp.schemas.verify import (
    ErrorSignal,
    FieldDiscrepancy,
    ProblemState,
    StudentStep,
    VerifyResult,
)
from studyhelp.verification.topics.decimals.free_text_parser import parse_student_text
from studyhelp.verification.topics.decimals.step_checkers import (
    STEP_TYPE_FIELD_MODELS,
    compare_to_expected,
)
from studyhelp.verification.topics.decimals.sympy_utils import check_final_identity

_EvaluatedCandidate = tuple[StepNode, list[FieldDiscrepancy], float, dict[str, object]]


class DecimalsVerifier:
    topic = "decimals"

    def verify_step(self, problem_state: ProblemState, student_step: StudentStep) -> VerifyResult:
        problem = problem_state.problem
        raw_text = student_step.fields.get("text")
        if not isinstance(raw_text, str) or not raw_text.strip():
            return VerifyResult(
                is_valid=False,
                matched_step_id=None,
                confidence=1.0,
                error_signal=ErrorSignal(kind="malformed", note="empty or missing 'text' field"),
            )

        frontier_ids = self._frontier(problem, problem_state.accepted_step_ids)
        frontier_nodes: list[StepNode] = [
            node for step_id in frontier_ids if (node := problem.node(step_id)) is not None
        ]

        if not frontier_nodes:
            return VerifyResult(
                is_valid=False,
                matched_step_id=None,
                confidence=1.0,
                error_signal=ErrorSignal(kind="none", note="no reachable next step"),
            )

        evaluated: list[_EvaluatedCandidate] = []
        for node in frontier_nodes:
            if node.type not in STEP_TYPE_FIELD_MODELS:
                continue
            try:
                fields = parse_student_text(node.type, raw_text)
                STEP_TYPE_FIELD_MODELS[node.type].model_validate(fields)
            except (ValueError, ValidationError):
                continue
            discrepancies, agreement = compare_to_expected(node.expected_state, fields)
            evaluated.append((node, discrepancies, agreement, fields))

        if not evaluated:
            return VerifyResult(
                is_valid=False,
                matched_step_id=None,
                confidence=1.0,
                error_signal=ErrorSignal(
                    kind="malformed",
                    note=(
                        f"'{raw_text}' doesn't match the expected shape for this step "
                        f"({', '.join(n.type for n in frontier_nodes)})"
                    ),
                ),
            )

        exact = [c for c in evaluated if not c[1]]
        if exact:
            node, _discrepancies, _agreement, fields = exact[0]
            if node.type == "write_final_answer":
                self._cross_check_final_identity(problem, node)
            return VerifyResult(
                is_valid=True, matched_step_id=node.step_id, confidence=1.0, parsed_fields=fields
            )

        return self._resolve_near_match(evaluated)

    def _resolve_near_match(self, evaluated: list[_EvaluatedCandidate]) -> VerifyResult:
        # Same rationale as fractions_addition's D40 / lcm_hcf's precedent:
        # `evaluated` only ever contains candidates whose text already
        # parsed cleanly into that step type's exact grammar, so a
        # non-exact value match is unambiguous, not low-confidence noise.
        node, discrepancies, agreement, fields = max(evaluated, key=lambda c: c[2])
        return VerifyResult(
            is_valid=False,
            matched_step_id=None,
            confidence=1.0 - agreement,
            error_signal=ErrorSignal(
                kind="field_mismatch",
                discrepant_fields=discrepancies,
                nearest_matched_step_id=node.step_id,
            ),
            parsed_fields=fields,
        )

    def _frontier(self, problem: Problem, accepted_step_ids: list[str]) -> set[str]:
        if not accepted_step_ids:
            return set(problem.entry_step_ids())
        frontier: set[str] = set()
        for step_id in accepted_step_ids:
            node = problem.node(step_id)
            if node is not None:
                frontier.update(node.next)
        return frontier - set(accepted_step_ids)

    def _cross_check_final_identity(self, problem: Problem, node: StepNode) -> None:
        result = node.expected_state.get("result_hundredths")
        if result is None:
            return
        a = problem.given["a_hundredths"]
        b = problem.given["b_hundredths"]
        op = problem.given["op"]
        if not check_final_identity(a, b, op, result):
            raise ValueError(
                f"Problem '{problem.problem_id}' data integrity error: "
                f"{a} {op} {b} != {result} (hundredths) per independent sympy cross-check"
            )
