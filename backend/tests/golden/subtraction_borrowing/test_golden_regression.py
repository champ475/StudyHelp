"""Golden regression suite for the subtraction-with-borrowing verifier.

Each case in `cases/*.json` is a (problem, prior steps, student submission)
triple with an expected verdict, expressed as a *confidence band* rather
than a bare number — this is what lets `ACCEPT_THRESHOLD`/`REJECT_THRESHOLD`
be tuned later without every case needing to know the exact float. Golden
cases are the enduring regression asset (technical_architecture.md §11 step
2's "regression tests passing before moving on" gate) — distinct from the
narrower hand-picked unit tests in tests/unit/verification/, and from the
DB-independent fixture arithmetic checks in tests/unit/seed/.

Case fixtures are generated from real problem fixtures (see
`scripts/build_golden_cases.py`) rather than hand-transcribed, so digit
values can't drift from the seeded problems they're tested against.
"""

import json
from pathlib import Path
from typing import Any

import pytest

from studyhelp.schemas.step_schema import Problem
from studyhelp.schemas.verify import ProblemState, StudentStep, VerifyResult
from studyhelp.verification.confidence import (
    ACCEPT_THRESHOLD,
    NON_ADJACENT_MATCH_CONFIDENCE,
    REJECT_THRESHOLD,
)
from studyhelp.verification.topics.subtraction_borrowing.verifier import (
    SubtractionBorrowingVerifier,
)

CASES_DIR = Path(__file__).parent / "cases"
PROBLEMS_DIR = (
    Path(__file__).parents[3]
    / "src"
    / "studyhelp"
    / "seed"
    / "fixtures"
    / "problems"
    / "ch1_subtraction_borrowing"
)


def _load_problems() -> dict[str, Problem]:
    problems: dict[str, Problem] = {}
    for path in PROBLEMS_DIR.glob("*.json"):
        problem = Problem.model_validate(json.loads(path.read_text()))
        problems[problem.problem_id] = problem
    return problems


def _load_cases() -> list[dict[str, Any]]:
    return [json.loads(path.read_text()) for path in sorted(CASES_DIR.glob("*.json"))]


PROBLEMS = _load_problems()
CASES = _load_cases()

assert len(CASES) >= 28, (
    f"expected ~30 golden cases, found {len(CASES)} — did generation run correctly?"
)


def _assert_band(result: VerifyResult, band: str, case_id: str) -> None:
    if band == "accept":
        assert result.is_valid is True, case_id
        assert result.confidence >= ACCEPT_THRESHOLD, case_id
    elif band == "non_adjacent":
        assert result.is_valid is True, case_id
        assert result.confidence == pytest.approx(NON_ADJACENT_MATCH_CONFIDENCE), case_id
        assert result.confidence < ACCEPT_THRESHOLD, case_id
    elif band == "reject":
        assert result.is_valid is False, case_id
        assert result.confidence >= REJECT_THRESHOLD, case_id
    elif band == "passthrough":
        assert result.is_valid is True, case_id
        assert result.confidence < REJECT_THRESHOLD, case_id
    elif band == "structural":
        assert result.is_valid is False, case_id
        assert result.confidence == 1.0, case_id
    else:
        pytest.fail(f"{case_id}: unknown confidence_band '{band}' in golden case")


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["case_id"])
def test_golden_case(case: dict[str, Any]) -> None:
    problem = PROBLEMS[case["problem_id"]]
    state = ProblemState(problem=problem, accepted_step_ids=case["prior_accepted_steps"])
    student_step = StudentStep(
        step_type=case["student_step"]["step_type"], fields=case["student_step"]["fields"]
    )

    verifier = SubtractionBorrowingVerifier()
    result = verifier.verify_step(state, student_step)

    expected = case["expected"]
    _assert_band(result, expected["confidence_band"], case["case_id"])
    assert result.is_valid == expected["is_valid"], case["case_id"]
    assert result.matched_step_id == expected["matched_step_id"], case["case_id"]

    if expected["error_kind"] is not None:
        assert result.error_signal is not None, case["case_id"]
        assert result.error_signal.kind == expected["error_kind"], case["case_id"]
    if expected["error_note"] is not None:
        assert result.error_signal is not None, case["case_id"]
        assert result.error_signal.note == expected["error_note"], case["case_id"]


def test_golden_suite_covers_every_confidence_band() -> None:
    bands = {case["expected"]["confidence_band"] for case in CASES}
    assert bands == {"accept", "non_adjacent", "reject", "passthrough", "structural"}


def test_golden_suite_covers_all_four_buggy_rules() -> None:
    """B1-B3 land as `reject`, B4 lands as `passthrough` — a deliberate,
    documented finding (see CHANGELOG): the Phase 1 field-agreement
    heuristic can't confidently flag a two-field-correlated bug shape,
    which is exactly the gap Phase 2's buggy-rule matcher closes."""
    case_ids = {case["case_id"] for case in CASES}
    assert any(cid.startswith("reject_b1_") for cid in case_ids)
    assert any(cid.startswith("reject_b2_") for cid in case_ids)
    assert any(cid.startswith("reject_b3_") for cid in case_ids)
    assert any("b4_stale_borrow_digit" in cid for cid in case_ids)
