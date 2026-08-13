"""Deterministic verifier for NCERT Class 5 Ch.1 multi-digit subtraction
with borrowing — the first topic slice (ARCHITECTURE.md D20).

Procedural correctness (was a borrow needed here, right column, right DAG
position) is custom graph/field-matching logic in this module, not sympy
(ARCHITECTURE.md D23). sympy's role is limited to `sympy_utils`'s narrow,
explicit arithmetic cross-checks.
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
from studyhelp.verification.confidence import NON_ADJACENT_MATCH_CONFIDENCE, REJECT_THRESHOLD
from studyhelp.verification.topics.subtraction_borrowing.step_checkers import (
    STEP_TYPE_FIELD_MODELS,
    compare_to_expected,
    parse_student_fields,
)
from studyhelp.verification.topics.subtraction_borrowing.sympy_utils import check_final_identity

_EvaluatedCandidate = tuple[StepNode, list[FieldDiscrepancy], float]


class SubtractionBorrowingVerifier:
    topic = "subtraction_with_borrowing"

    def verify_step(self, problem_state: ProblemState, student_step: StudentStep) -> VerifyResult:
        problem = problem_state.problem

        if student_step.step_type not in STEP_TYPE_FIELD_MODELS:
            return VerifyResult(
                is_valid=False,
                matched_step_id=None,
                confidence=1.0,
                error_signal=ErrorSignal(
                    kind="wrong_step_type",
                    note=f"'{student_step.step_type}' is not a known step type for {self.topic}",
                ),
            )

        try:
            parse_student_fields(student_step.step_type, student_step.fields)
        except ValidationError as exc:
            return VerifyResult(
                is_valid=False,
                matched_step_id=None,
                confidence=1.0,
                error_signal=ErrorSignal(kind="malformed", note=str(exc)),
            )

        candidates = problem.nodes_of_type(student_step.step_type)
        if not candidates:
            return VerifyResult(
                is_valid=False,
                matched_step_id=None,
                confidence=1.0,
                error_signal=ErrorSignal(
                    kind="wrong_step_type",
                    note=f"problem '{problem.problem_id}' has no '{student_step.step_type}' step",
                ),
            )

        frontier = self._frontier(problem, problem_state.accepted_step_ids)
        evaluated: list[_EvaluatedCandidate] = [
            (node, *compare_to_expected(node.expected_state, student_step.fields))
            for node in candidates
        ]

        exact = [node for node, discrepancies, _ in evaluated if not discrepancies]
        if exact:
            return self._resolve_exact_match(problem, exact, frontier, student_step.step_type)

        return self._resolve_near_match(evaluated, frontier)

    def _resolve_exact_match(
        self, problem: Problem, exact: list[StepNode], frontier: set[str], step_type: str
    ) -> VerifyResult:
        frontier_matches = [node for node in exact if node.step_id in frontier]
        matched = frontier_matches[0] if frontier_matches else exact[0]

        if step_type == "write_final_answer":
            self._cross_check_final_identity(problem, matched)

        if matched.step_id in frontier:
            return VerifyResult(is_valid=True, matched_step_id=matched.step_id, confidence=1.0)

        return VerifyResult(
            is_valid=True,
            matched_step_id=matched.step_id,
            confidence=NON_ADJACENT_MATCH_CONFIDENCE,
            error_signal=ErrorSignal(
                kind="none",
                note="non_adjacent_valid_match",
                nearest_matched_step_id=matched.step_id,
            ),
        )

    def _resolve_near_match(
        self, evaluated: list[_EvaluatedCandidate], frontier: set[str]
    ) -> VerifyResult:
        def sort_key(candidate: _EvaluatedCandidate) -> tuple[float, bool]:
            node, _discrepancies, agreement = candidate
            return (agreement, node.step_id in frontier)

        node, discrepancies, agreement = max(evaluated, key=sort_key)

        if agreement >= REJECT_THRESHOLD:
            return VerifyResult(
                is_valid=False,
                matched_step_id=None,
                confidence=agreement,
                error_signal=ErrorSignal(
                    kind="field_mismatch",
                    discrepant_fields=discrepancies,
                    nearest_matched_step_id=node.step_id,
                ),
            )

        return VerifyResult(
            is_valid=True,
            matched_step_id=None,
            confidence=agreement,
            error_signal=ErrorSignal(
                kind="field_mismatch",
                discrepant_fields=discrepancies,
                nearest_matched_step_id=node.step_id,
                note="low_confidence_passthrough",
            ),
        )

    def _frontier(self, problem: Problem, accepted_step_ids: list[str]) -> set[str]:
        if not accepted_step_ids:
            return set(problem.entry_step_ids())
        frontier: set[str] = set()
        for step_id in accepted_step_ids:
            node = problem.node(step_id)
            if node is not None:
                frontier.update(node.next)
        return frontier

    def _cross_check_final_identity(self, problem: Problem, node: StepNode) -> None:
        value = node.expected_state.get("value")
        if value is None:
            return
        minuend = problem.given["minuend"]
        subtrahend = problem.given["subtrahend"]
        if not check_final_identity(minuend, subtrahend, value):
            raise ValueError(
                f"Problem '{problem.problem_id}' data integrity error: "
                f"{minuend} - {subtrahend} != {value} per independent sympy cross-check"
            )
