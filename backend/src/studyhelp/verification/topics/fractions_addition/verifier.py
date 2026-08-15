"""Deterministic verifier for NCERT Class 5 fraction addition (like/unlike
denominators) — second topic slice, built on the founder's explicit
free-text-input request (ARCHITECTURE.md supersede entry over D12).

Unlike the subtraction topic, the student never declares a `step_type` —
there are no tabs, just one text box per step (CLAUDE.md: "text boxes for
each step ... mistake checking happen when I move to next step"). So this
verifier tries every step type reachable from the current frontier against
the raw text, rather than trusting a client-declared type. Restricting the
search to the *frontier* (not every node in the whole graph) is deliberate:
without it, text that happens to parse as some later step's shape would get
silently accepted as a "non-adjacent valid match" the moment it parses,
which is the wrong failure mode for a student who is simply behind and
typed the wrong shape of answer for where they actually are.
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
from studyhelp.verification.topics.fractions_addition.free_text_parser import parse_student_text
from studyhelp.verification.topics.fractions_addition.step_checkers import (
    STEP_TYPE_FIELD_MODELS,
    compare_to_expected,
)
from studyhelp.verification.topics.fractions_addition.sympy_utils import check_final_identity

_EvaluatedCandidate = tuple[StepNode, list[FieldDiscrepancy], float, dict[str, object]]


class FractionsAdditionVerifier:
    topic = "fractions_addition"

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
        # `REJECT_THRESHOLD`-style field-agreement ratios (ARCHITECTURE.md
        # D2's false-negative bias, tuned against subtraction's many-digit
        # fields) don't transfer cleanly here: every fraction step has only
        # 2-5 fields, so a single wrong digit already swings agreement well
        # below 0.75, and the exact misconceptions this topic's buggy-rule
        # library exists to catch (F1/F2/F3) would silently pass through
        # unflagged. What makes subtraction's low-agreement case genuinely
        # *ambiguous* (worth a false-negative-biased pass) doesn't apply
        # here: the text already parsed cleanly into this step type's exact
        # shape (`evaluated` only contains candidates whose grammar
        # matched), so a value mismatch is unambiguous, not low-confidence
        # noise. Any non-exact parse is therefore a definite error.
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
        # Unlike the subtraction topic (where a step *type* can legitimately
        # recur at more than one DAG position, e.g. compare_column), every
        # fraction step type appears exactly once per problem — so a
        # previously-accepted id lingering in `frontier` (an earlier
        # iteration's `.next` can still name it) would let a stale-shaped
        # resubmission match an already-completed node instead of the
        # actual next one. Excluding accepted ids outright is correct here.
        return frontier - set(accepted_step_ids)

    def _cross_check_final_identity(self, problem: Problem, node: StepNode) -> None:
        result_num = node.expected_state.get("num")
        result_den = node.expected_state.get("den")
        if result_num is None or result_den is None:
            return
        a_num, a_den = problem.given["a_num"], problem.given["a_den"]
        b_num, b_den = problem.given["b_num"], problem.given["b_den"]
        if not check_final_identity(a_num, a_den, b_num, b_den, result_num, result_den):
            raise ValueError(
                f"Problem '{problem.problem_id}' data integrity error: "
                f"{a_num}/{a_den} + {b_num}/{b_den} != {result_num}/{result_den} "
                "per independent sympy cross-check"
            )
