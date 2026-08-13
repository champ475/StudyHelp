from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from studyhelp.db.models import NovelError


async def log_novel_error(
    session: AsyncSession,
    *,
    topic: str,
    step_type: str,
    correct_step: dict[str, Any],
    student_step: dict[str, Any],
    discrepant_fields: list[str],
    llm_rationale: str | None,
    event_id: int | None = None,
) -> NovelError:
    row = NovelError(
        event_id=event_id,
        topic=topic,
        step_type=step_type,
        correct_step=correct_step,
        student_step=student_step,
        discrepant_fields=discrepant_fields,
        llm_rationale=llm_rationale,
    )
    session.add(row)
    await session.flush()
    return row
