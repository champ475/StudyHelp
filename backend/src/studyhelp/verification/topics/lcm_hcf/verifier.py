"""Deterministic verifier for NCERT Class 5 Ch.6 ("Be My Multiple, I'll Be
Your Factor" — LCM and HCF). Mirrors `FractionsAdditionVerifier`'s pattern
exactly (ARCHITECTURE.md D41): no client-declared `step_type`, tries every
step type's grammar against the submitted text.

Candidate search covers every node still reachable from the current
frontier (BFS forward closure over `.next`, `Problem.reachable_step_ids()`),
not just the immediate frontier (ARCHITECTURE.md D59, superseding this
module's original frontier-only search) -- otherwise a student who jumps
straight to the final answer, skipping intermediate steps the DAG still
accepts, is wrongly flagged wrong. An exact match against the immediate
frontier is a clean accept (confidence 1.0); an exact match further along
is accepted too but surfaced at `NON_ADJACENT_MATCH_CONFIDENCE`
(`non_adjacent_valid_match`), same tiering as `SubtractionBorrowingVerifier`.
A non-exact match anywhere in the reachable set is still an unambiguous
reject rather than a low-confidence passthrough (D40's rationale: once text
parses cleanly into a step's exact grammar, a value mismatch is unambiguous).
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
from studyhelp.verification.confidence import NON_ADJACENT_MATCH_CONFIDENCE
from studyhelp.verification.topics.lcm_hcf.free_text_parser import parse_student_text
from studyhelp.verification.topics.lcm_hcf.step_checkers import (
    STEP_TYPE_FIELD_MODELS,
    compare_to_expected,
)
from studyhelp.verification.topics.lcm_hcf.sympy_utils import check_final_value

_EvaluatedCandidate = tuple[StepNode, list[FieldDiscrepancy], float, dict[str, object]]


class LcmHcfVerifier:
    topic = "lcm_hcf"

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
        reachable_ids = problem.reachable_step_ids(frontier_ids) if frontier_ids else set()
        reachable_nodes: list[StepNode] = [
            node for step_id in reachable_ids if (node := problem.node(step_id)) is not None
        ]

        if not reachable_nodes:
            return VerifyResult(
                is_valid=False,
                matched_step_id=None,
                confidence=1.0,
                error_signal=ErrorSignal(kind="none", note="no reachable next step"),
            )

        evaluated: list[_EvaluatedCandidate] = []
        for node in reachable_nodes:
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
                        f"({', '.join(n.type for n in reachable_nodes)})"
                    ),
                ),
            )

        exact = [c for c in evaluated if not c[1]]
        if exact:
            frontier_matches = [c for c in exact if c[0].step_id in frontier_ids]
            # A submission's value can coincide with more than one
            # non-frontier reachable node (e.g. a `simplify_fraction` step
            # whose correct output happens to equal the final answer) --
            # prefer an actually-terminal (`next == []`) match over a
            # merely-further-along intermediate one, so a value that both
            # legitimately completes the problem AND happens to satisfy an
            # earlier node is read as "the student finished" (Bug3), not
            # as an arbitrary pick between coincidentally-equal candidates.
            terminal_matches = [c for c in exact if not c[0].next]
            node, _discrepancies, _agreement, fields = (
                frontier_matches[0]
                if frontier_matches
                else terminal_matches[0]
                if terminal_matches
                else exact[0]
            )
            if node.type == "write_final_answer":
                self._cross_check_final_value(problem, node)
            if node.step_id in frontier_ids:
                return VerifyResult(
                    is_valid=True,
                    matched_step_id=node.step_id,
                    confidence=1.0,
                    parsed_fields=fields,
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

        return self._resolve_near_match(evaluated, frontier_ids)

    def _resolve_near_match(
        self, evaluated: list[_EvaluatedCandidate], frontier_ids: set[str]
    ) -> VerifyResult:
        # Same rationale as fractions_addition's D40: `evaluated` only ever
        # contains candidates whose text already parsed cleanly into that
        # step type's exact grammar, so a non-exact value match is
        # unambiguous, not low-confidence noise — always reject.
        # Candidate search now spans every reachable node (D59), not just
        # the frontier, so two reachable nodes can tie on agreement (e.g. a
        # re-used field name whose expected value happens to coincide further
        # down the DAG) -- prefer the frontier candidate on a tie so the
        # diagnosis points at the step the student is actually on, same
        # (agreement, in_frontier) tie-break as
        # SubtractionBorrowingVerifier._resolve_near_match.
        node, discrepancies, agreement, fields = max(
            evaluated, key=lambda c: (c[2], c[0].step_id in frontier_ids)
        )
        return VerifyResult(
            is_valid=False,
            matched_step_id=None,
            confidence=round(1.0 - agreement, 4),
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
        a, b, op = problem.given["a"], problem.given["b"], problem.given["op"]
        if not check_final_value(a, b, op, value):
            raise ValueError(
                f"Problem '{problem.problem_id}' data integrity error: "
                f"{op}({a}, {b}) != {value} per independent sympy cross-check"
            )
