"""Retrieve-don't-dump (technical_architecture.md §5): only the
misconception-bank entries matching the current (topic, step_type) are
ever loaded — never the whole bank — keeping the LLM classification
prompt small and its attention on what's actually relevant."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from studyhelp.db.models import MisconceptionBankEntry
from studyhelp.llm.client import ClassifyCandidate


async def get_candidates(
    session: AsyncSession, *, topic: str, step_type: str
) -> list[ClassifyCandidate]:
    stmt = select(MisconceptionBankEntry).where(
        MisconceptionBankEntry.topic == topic,
        MisconceptionBankEntry.step_type == step_type,
    )
    rows = (await session.execute(stmt)).scalars().all()
    return [
        ClassifyCandidate(misconception_id=row.id, typical_mindset=row.typical_mindset)
        for row in rows
    ]
