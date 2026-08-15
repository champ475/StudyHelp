"""Deterministic verifier for NCERT Class 5 Ch.11 ("Area and its Boundary"
-- area and perimeter of rectangles/squares). Mirrors `DecimalsVerifier`'s
/ `LcmHcfVerifier`'s pattern exactly (ARCHITECTURE.md D41): no
client-declared `step_type`, tries every step type's grammar against the
submitted text, restricts candidate search to the DAG frontier (this
topic's DAG is linear with no step-type recurrence -- a given problem's
graph only ever contains ONE of `compute_area`/`compute_perimeter`, never
both), and rejects any non-exact frontier-parseable match rather than a
low-confidence passthrough (D40's rationale).
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
from studyhelp.verification.topics.area_perimeter.free_text_parser import parse_student_text
from studyhelp.verification.topics.area_perimeter.step_checkers import (
    STEP_TYPE_FIELD_MODELS,
    compare_to_expected,
)
from studyhelp.verification.topics.area_perimeter.sympy_utils import check_final_value

_EvaluatedCandidate = tuple[StepNode, list[FieldDiscrepancy], float, dict[str, object]]


class AreaPerimeterVerifier:
    topic = "area_perimeter"

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
                self._cross_check_final_value(problem, node)
            return VerifyResult(
                is_valid=True, matched_step_id=node.step_id, confidence=1.0, parsed_fields=fields
            )

        return self._resolve_near_match(evaluated)

    def _resolve_near_match(self, evaluated: list[_EvaluatedCandidate]) -> VerifyResult:
        # Same rationale as fractions_addition's D40 / lcm_hcf's / decimals'
        # precedent: `evaluated` only ever contains candidates whose text
        # already parsed cleanly into that step type's exact grammar, so a
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

    def _cross_check_final_value(self, problem: Problem, node: StepNode) -> None:
        value = node.expected_state.get("value")
        if value is None:
            return
        length = problem.given["length"]
        width = problem.given["width"]
        measure = problem.given["measure"]
        if not check_final_value(length, width, measure, value):
            raise ValueError(
                f"Problem '{problem.problem_id}' data integrity error: {measure} of "
                f"length={length}, width={width} != {value} per independent sympy cross-check"
            )
