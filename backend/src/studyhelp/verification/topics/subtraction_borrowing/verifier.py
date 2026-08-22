"""Deterministic verifier for NCERT Class 5 Ch.1 multi-digit subtraction
with borrowing — the first topic slice (ARCHITECTURE.md D20).

Procedural correctness (was a borrow needed here, right column, right DAG
position) is custom graph/field-matching logic in this module, not sympy
(ARCHITECTURE.md D23). sympy's role is limited to `sympy_utils`'s narrow,
explicit arithmetic cross-checks.

Free-text input (ARCHITECTURE.md D41/D43, completing this topic's port off
tap-widget input): the student never declares a `step_type` — this
verifier tries every step type's grammar (`free_text_parser.py`) against
the raw text, the same "try every reachable candidate" pattern
`fractions_addition/verifier.py` established. One structural difference
from that topic's verifier survives on purpose: a step *type* can
legitimately recur at more than one DAG position here (e.g.
`subtract_column` appears once per column), so candidate search still
covers every node of a matched type in the whole graph, not just the
frontier, with the same non-adjacent-match / REJECT_THRESHOLD
false-negative-biased passthrough behavior this topic's golden suite
already exercises (ARCHITECTURE.md D22) — porting the input mechanism
must not silently change this topic's already-tuned confidence behavior.
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
from studyhelp.verification.topics.subtraction_borrowing.free_text_parser import parse_student_text
from studyhelp.verification.topics.subtraction_borrowing.step_checkers import (
    STEP_TYPE_FIELD_MODELS,
    compare_to_expected,
)
from studyhelp.verification.topics.subtraction_borrowing.sympy_utils import check_final_identity

_EvaluatedCandidate = tuple[StepNode, list[FieldDiscrepancy], float, dict[str, object]]


class SubtractionBorrowingVerifier:
    topic = "subtraction_with_borrowing"

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

        parsed_by_type: dict[str, dict[str, object]] = {}
        for step_type in STEP_TYPE_FIELD_MODELS:
            try:
                fields = parse_student_text(step_type, raw_text)
                STEP_TYPE_FIELD_MODELS[step_type].model_validate(fields)
            except (ValueError, ValidationError):
                continue
            parsed_by_type[step_type] = fields

        if not parsed_by_type:
            return VerifyResult(
                is_valid=False,
                matched_step_id=None,
                confidence=1.0,
                error_signal=ErrorSignal(
                    kind="malformed",
                    note=f"'{raw_text}' doesn't match any known step's grammar",
                ),
            )

        evaluated: list[_EvaluatedCandidate] = []
        for step_type, fields in parsed_by_type.items():
            for node in problem.nodes_of_type(step_type):
                discrepancies, agreement = compare_to_expected(node.expected_state, fields)
                evaluated.append((node, discrepancies, agreement, fields))

        if not evaluated:
            return VerifyResult(
                is_valid=False,
                matched_step_id=None,
                confidence=1.0,
                error_signal=ErrorSignal(
                    kind="wrong_step_type",
                    note=(
                        f"problem '{problem.problem_id}' has no step of type(s) "
                        f"{sorted(parsed_by_type)}"
                    ),
                ),
            )

        frontier = self._frontier(problem, problem_state.accepted_step_ids)
        exact = [c for c in evaluated if not c[1]]
        if exact:
            return self._resolve_exact_match(problem, exact, frontier)

        return self._resolve_near_match(evaluated, frontier)

    def _resolve_exact_match(
        self,
        problem: Problem,
        exact: list[_EvaluatedCandidate],
        frontier: set[str],
    ) -> VerifyResult:
        frontier_matches = [c for c in exact if c[0].step_id in frontier]
        # See fractions_addition/decimals/etc.'s identical tie-break
        # (ARCHITECTURE.md D59): prefer an actually-terminal (`next == []`)
        # match over a merely-further-along one when a submission's value
        # coincides with more than one candidate node.
        terminal_matches = [c for c in exact if not c[0].next]
        node, _discrepancies, _agreement, fields = (
            frontier_matches[0]
            if frontier_matches
            else terminal_matches[0]
            if terminal_matches
            else exact[0]
        )

        if node.type == "write_final_answer":
            self._cross_check_final_identity(problem, node)

        if node.step_id in frontier:
            return VerifyResult(
                is_valid=True, matched_step_id=node.step_id, confidence=1.0, parsed_fields=fields
            )

        return VerifyResult(
            is_valid=True,
            matched_step_id=node.step_id,
            confidence=NON_ADJACENT_MATCH_CONFIDENCE,
            error_signal=ErrorSignal(
                kind="none",
                note="non_adjacent_valid_match",
                nearest_matched_step_id=node.step_id,
            ),
            parsed_fields=fields,
        )

    def _resolve_near_match(
        self, evaluated: list[_EvaluatedCandidate], frontier: set[str]
    ) -> VerifyResult:
        def sort_key(candidate: _EvaluatedCandidate) -> tuple[float, bool]:
            node, _discrepancies, agreement, _fields = candidate
            return (agreement, node.step_id in frontier)

        node, discrepancies, agreement, fields = max(evaluated, key=sort_key)

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
                parsed_fields=fields,
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
