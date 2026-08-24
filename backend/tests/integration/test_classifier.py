"""Full classify_error() flow against a real DB: candidate retrieval,
closed-set validation (including the adversarial case), and novel-error
logging + clustering. Skips gracefully without a local Postgres, same as
every other integration test."""

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from studyhelp.classification.classifier import classify_error
from studyhelp.classification.clustering import cluster_pending_novel_errors, cluster_signature
from studyhelp.db.models import NovelError
from studyhelp.llm.client import ClassifyResponse
from studyhelp.llm.providers.mock import MockLLMProvider
from studyhelp.seed.loader import seed_all

# Deliberately doesn't match B2 (from_digit_after != from_digit_before, i.e.
# the lender *was* decremented, just the wrong one) or B3 (correct's
# to_digit_before is 2, not 0) — falls through to the LLM path.
_CORRECT_BORROW = {
    "from_column": "tens",
    "from_digit_before": 5,
    "from_digit_after": 4,
    "to_column": "units",
    "to_digit_before": 2,
    "to_digit_after": 12,
}
_WRONG_COLUMN_BORROW = {
    "from_column": "hundreds",
    "from_digit_before": 9,
    "from_digit_after": 8,
    "to_column": "units",
    "to_digit_before": 2,
    "to_digit_after": 12,
}


async def test_llm_fallback_picks_a_real_retrieved_candidate(db_session: AsyncSession) -> None:
    await seed_all(db_session)
    await db_session.flush()

    result = await classify_error(
        db_session,
        MockLLMProvider(),
        topic="subtraction_with_borrowing",
        step_type="borrow",
        correct_fields=_CORRECT_BORROW,
        student_fields=_WRONG_COLUMN_BORROW,
        discrepant_fields=["from_column", "from_digit_before", "from_digit_after"],
    )
    assert result.source == "llm"
    assert result.confidence == "low"  # never auto-trusted at the rule-match tier (D3)
    assert result.misconception_id in {
        "subtraction_borrowing.no_decrement_after_borrow",
        "subtraction_borrowing.borrow_across_zero",
    }
    await db_session.rollback()


async def test_closed_set_violation_never_trusted_and_logged_as_novel(
    db_session: AsyncSession,
) -> None:
    await seed_all(db_session)
    await db_session.flush()

    adversarial = ClassifyResponse(
        misconception_id="not-a-real-candidate-id", rationale="a misbehaving model"
    )
    result = await classify_error(
        db_session,
        MockLLMProvider(classify_override=adversarial),
        topic="subtraction_with_borrowing",
        step_type="borrow",
        correct_fields=_CORRECT_BORROW,
        student_fields=_WRONG_COLUMN_BORROW,
        discrepant_fields=["from_column"],
    )
    assert result.source == "novel"
    assert result.misconception_id is None

    rows = (
        (
            await db_session.execute(
                select(NovelError).where(NovelError.llm_rationale == "a misbehaving model")
            )
        )
        .scalars()
        .all()
    )
    assert len(rows) == 1
    assert rows[0].topic == "subtraction_with_borrowing"
    assert rows[0].step_type == "borrow"
    await db_session.rollback()


async def test_no_candidates_routes_to_novel(db_session: AsyncSession) -> None:
    await seed_all(db_session)
    await db_session.flush()

    result = await classify_error(
        db_session,
        MockLLMProvider(),
        topic="subtraction_with_borrowing",
        # A step_type that exists nowhere in the seeded misconception_bank
        # (every real step_type across every topic now has at least one
        # entry after the misconception-bank expansion pass — see
        # ARCHITECTURE.md's retrieval-bank sizing note) — get_candidates()
        # returns empty for it by construction, keeping this test's premise
        # true regardless of how full any individual topic's bank gets.
        step_type="__no_seeded_candidates_for_this_step_type__",
        correct_fields={
            "column": "units",
            "minuend_digit": 9,
            "subtrahend_digit": 5,
            "borrow_needed": False,
        },
        student_fields={
            "column": "units",
            "minuend_digit": 3,
            "subtrahend_digit": 5,
            "borrow_needed": True,
        },
        discrepant_fields=["minuend_digit", "borrow_needed"],
    )
    assert result.source == "novel"
    await db_session.rollback()


async def test_cluster_pending_novel_errors_groups_by_structural_signature(
    db_session: AsyncSession,
) -> None:
    await seed_all(db_session)
    await db_session.flush()

    # Three novel errors: two share the same (topic, step_type, discrepant
    # fields) signature, one differs — should end up in two clusters.
    for discrepant in (["from_column"], ["from_column"], ["to_column"]):
        await classify_error(
            db_session,
            MockLLMProvider(
                classify_override=ClassifyResponse(misconception_id=None, rationale="none fit")
            ),
            topic="subtraction_with_borrowing",
            step_type="borrow",
            correct_fields=_CORRECT_BORROW,
            student_fields=_WRONG_COLUMN_BORROW,
            discrepant_fields=discrepant,
        )
    await db_session.flush()

    clustered_count = await cluster_pending_novel_errors(db_session)
    assert clustered_count == 3

    expected_a = cluster_signature("subtraction_with_borrowing", "borrow", ["from_column"])
    expected_b = cluster_signature("subtraction_with_borrowing", "borrow", ["to_column"])

    count_a = (
        await db_session.execute(
            select(func.count()).select_from(NovelError).where(NovelError.cluster_id == expected_a)
        )
    ).scalar_one()
    count_b = (
        await db_session.execute(
            select(func.count()).select_from(NovelError).where(NovelError.cluster_id == expected_b)
        )
    ).scalar_one()
    assert count_a == 2
    assert count_b == 1

    # Idempotent: re-running clusters nothing new.
    assert await cluster_pending_novel_errors(db_session) == 0

    await db_session.rollback()
