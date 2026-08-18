"""Confirms the seed loader's upserts actually work against real Postgres,
and that running it twice is idempotent (no duplicate rows, no FK errors on
re-run) — the property the whole loader design is built around."""

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from studyhelp.db.models import BuggyRuleEntry, MisconceptionBankEntry, ProblemModel, StepType
from studyhelp.seed.loader import seed_all


async def test_seed_all_is_idempotent(db_session: AsyncSession) -> None:
    await seed_all(db_session)
    await db_session.flush()

    async def counts() -> tuple[int, int, int, int]:
        step_types = (
            await db_session.execute(select(func.count()).select_from(StepType))
        ).scalar_one()
        problems = (
            await db_session.execute(select(func.count()).select_from(ProblemModel))
        ).scalar_one()
        misconceptions = (
            await db_session.execute(select(func.count()).select_from(MisconceptionBankEntry))
        ).scalar_one()
        buggy_rules = (
            await db_session.execute(select(func.count()).select_from(BuggyRuleEntry))
        ).scalar_one()
        return step_types, problems, misconceptions, buggy_rules

    first_pass = await counts()
    assert first_pass == (34, 140, 26, 21)

    # Re-running must upsert by natural key, not duplicate rows.
    await seed_all(db_session)
    await db_session.flush()
    second_pass = await counts()
    assert second_pass == first_pass

    await db_session.rollback()


async def test_seeded_problem_round_trips_step_graph(db_session: AsyncSession) -> None:
    await seed_all(db_session)
    await db_session.flush()

    problem = await db_session.get(ProblemModel, "subtraction-borrow-014")
    assert problem is not None
    assert problem.final_answer == 355
    assert len(problem.step_graph) == 9
    assert problem.step_graph[0]["step_id"] == "s1_cmp_units"

    await db_session.rollback()


async def test_seeded_buggy_rule_resolves_its_misconception_fk(db_session: AsyncSession) -> None:
    await seed_all(db_session)
    await db_session.flush()

    rule = await db_session.get(BuggyRuleEntry, "subtraction_borrowing.stale_borrow_digit")
    assert rule is not None
    assert rule.misconception_id is not None

    misconception = await db_session.get(MisconceptionBankEntry, rule.misconception_id)
    assert misconception is not None
    assert misconception.topic == "subtraction_with_borrowing"

    await db_session.rollback()
