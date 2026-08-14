"""Confirms `alembic upgrade head` produced the expected schema, and that the
ORM models round-trip through a real Postgres (not mocked)."""

import uuid
from datetime import UTC, datetime

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from studyhelp.db.models import StepType, User, UserRole


async def test_all_tables_exist(db_session: AsyncSession) -> None:
    result = await db_session.execute(
        text("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'")
    )
    tables = {row[0] for row in result}
    expected = {
        "step_types",
        "problems",
        "misconception_bank",
        "buggy_rule_library",
        "users",
        "sessions",
        "events",
        "alembic_version",
    }
    assert expected.issubset(tables)


async def test_step_type_round_trips(db_session: AsyncSession) -> None:
    """Uses a synthetic (topic, step_type_key) rather than a real seeded
    one — CI's `test` job runs migrate -> seed -> test, so a real pair
    like ("subtraction_with_borrowing", "borrow") already exists by the
    time this test runs and would collide with the unique constraint.
    This test's intent is "does the ORM model round-trip through
    Postgres," not "does this specific seeded row exist" — synthetic
    data decouples the two."""
    row = StepType(
        topic="_test_topic",
        step_type_key="_test_step_type",
        description="Borrow ten from the column to the left.",
        structured_input_schema={
            "from_column": "str",
            "from_digit_before": "int",
            "from_digit_after": "int",
            "to_column": "str",
            "to_digit_before": "int",
            "to_digit_after": "int",
        },
    )
    db_session.add(row)
    await db_session.flush()
    await db_session.refresh(row)
    assert row.id is not None

    reloaded = await db_session.get(StepType, row.id)
    assert reloaded is not None
    assert reloaded.step_type_key == "_test_step_type"
    await db_session.rollback()


async def test_user_round_trips(db_session: AsyncSession) -> None:
    user = User(id=uuid.uuid4(), role=UserRole.STUDENT, display_name="dev-tester")
    db_session.add(user)
    await db_session.flush()
    await db_session.refresh(user)
    assert user.created_at is not None
    assert user.created_at.replace(tzinfo=UTC) < datetime.now(UTC)
    await db_session.rollback()
