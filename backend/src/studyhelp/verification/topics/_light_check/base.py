"""Shared verifier for the 7 "light-check" chapters (ARCHITECTURE.md D20's
Phase-0 audit + the founder's Phase-E-adjacent scope decision): Shapes and
Angles, How Many Squares?, Does it Look the Same?, Can You See the
Pattern?, Mapping Your Way, Boxes and Sketches, Smart Charts. These are
recognition/visual/interpretive tasks, not linear checkable procedures —
rather than forcing each into its own 4-file heavy-topic module (proportion
matters: `verify_step()` for these is genuinely one thing, not four), every
light-check topic is one `LightCheckVerifier(topic=...)` instance sharing
this single module.

Every problem has 1-2 steps whose `expected_state` is `{"answer": <str>}` —
a single free-text field, compared case/whitespace-insensitively
(`_normalize()`) since the "answer" here is a word or number, not a
structured multi-field submission. Because there is exactly one field to
compare, a mismatch is always an unambiguous reject (confidence 1.0) — the
multi-field agreement-ratio machinery the heavy DAG topics need (D2's
false-negative bias, D22's thresholds) doesn't apply to a single yes/no
field comparison, so this module deliberately doesn't import or reuse it.

Candidate search covers every node still reachable from the current
frontier (`Problem.reachable_step_ids()`), not just the immediate frontier
(ARCHITECTURE.md D59/D65) — most light-check problems are exactly 1 step
so this is a no-op, but `patterns` (Ch.7) problems are a genuine 2-step DAG
(`patterns_common_difference` -> `patterns_next_term`), and the second
step's answer is often numerically simple enough that a student answers it
directly at step 1 (confirmed live: "2, 4, 6, 8, ..." — student typed "10",
the correct *next term*, while step 1 still expects the common difference
"2"). An exact match against the immediate frontier is a clean accept
(confidence 1.0); an exact match further along is accepted too but
surfaced at `NON_ADJACENT_MATCH_CONFIDENCE`, same tiering as every DAG
topic's verifier.

Deliberately does NOT filter candidate nodes by a hardcoded `node.type`
string (unlike every DAG topic's verifier) — each light-check topic gives
its own steps a topic-specific `type` name (e.g. `shapes_angles_answer`,
`symmetry_answer`) precisely so the shared `classification/rule_matcher.py`
buggy-rule matching, which scopes matchers by `step_type` alone (no topic
parameter — every DAG topic's step-type names have always been
topic-unique, so this was never previously an issue), can't cross-fire
between two different light-check topics that both happened to use the
same generic step-type name. This module only ever checks for an
`"answer"` key in `expected_state`, never the node's `type` string, so it
stays correct regardless of what each topic names its step types.
"""

from studyhelp.schemas.step_schema import Problem, StepNode
from studyhelp.schemas.verify import (
    ErrorSignal,
    FieldDiscrepancy,
    ProblemState,
    StudentStep,
    VerifyResult,
)
from studyhelp.verification.confidence import NON_ADJACENT_MATCH_CONFIDENCE


def _normalize(text: str) -> str:
    return " ".join(text.strip().lower().split())


class LightCheckVerifier:
    def __init__(self, topic: str) -> None:
        self.topic = topic

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
        candidates: list[StepNode] = [
            node
            for step_id in reachable_ids
            if (node := problem.node(step_id)) is not None and "answer" in node.expected_state
        ]

        if not candidates:
            return VerifyResult(
                is_valid=False,
                matched_step_id=None,
                confidence=1.0,
                error_signal=ErrorSignal(kind="none", note="no reachable next step"),
            )

        fields = {"answer": raw_text.strip()}
        normalized_student = _normalize(raw_text)
        exact = [
            n for n in candidates if _normalize(n.expected_state["answer"]) == normalized_student
        ]
        if exact:
            frontier_matches = [n for n in exact if n.step_id in frontier_ids]
            terminal_matches = [n for n in exact if not n.next]
            node = (
                frontier_matches[0]
                if frontier_matches
                else terminal_matches[0]
                if terminal_matches
                else exact[0]
            )
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

        # Prefer a frontier candidate as the "nearest" reject target when
        # the reachable set now spans more than one node (D59/D65) — a
        # wrong answer should be diagnosed against the step the student is
        # actually on, not an arbitrary later reachable one.
        frontier_candidates = [n for n in candidates if n.step_id in frontier_ids]
        nearest = frontier_candidates[0] if frontier_candidates else candidates[0]
        return VerifyResult(
            is_valid=False,
            matched_step_id=None,
            confidence=1.0,
            error_signal=ErrorSignal(
                kind="field_mismatch",
                discrepant_fields=[
                    FieldDiscrepancy(
                        field="answer",
                        expected=nearest.expected_state["answer"],
                        actual=raw_text.strip(),
                    )
                ],
                nearest_matched_step_id=nearest.step_id,
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


def validate_light_check_problem(problem: "Problem") -> None:
    """Seed-time gate, proportionate to this topic family's shape: every
    node must be type "answer" with a non-empty `answer` string, the graph
    is 1-2 nodes, and the terminal node's answer matches `final_answer`
    (case/whitespace-insensitively) — no arithmetic identity to
    cross-check here, unlike the DAG topics' sympy_utils modules."""
    if not 1 <= len(problem.step_graph) <= 2:
        raise ValueError(
            f"{problem.problem_id}: light-check problems must have 1-2 steps, got {len(problem.step_graph)}"
        )
    for node in problem.step_graph:
        answer = node.expected_state.get("answer")
        if not isinstance(answer, str) or not answer.strip():
            raise ValueError(
                f"{problem.problem_id}/{node.step_id}: expected_state.answer must be a non-empty string"
            )

    terminal_nodes = [n for n in problem.step_graph if not n.next]
    if len(terminal_nodes) != 1:
        raise ValueError(
            f"{problem.problem_id}: light-check problems must have exactly one terminal node"
        )
    terminal = terminal_nodes[0]
    final_answer = (
        problem.final_answer.get("answer") if isinstance(problem.final_answer, dict) else None
    )
    if not isinstance(final_answer, str) or _normalize(final_answer) != _normalize(
        terminal.expected_state["answer"]
    ):
        raise ValueError(
            f"{problem.problem_id}: final_answer {problem.final_answer!r} doesn't match terminal "
            f"step {terminal.step_id}'s answer {terminal.expected_state['answer']!r}"
        )
