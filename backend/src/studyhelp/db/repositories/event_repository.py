"""Append-only event log writes — the research dataset
(technical_architecture.md §8). Every write goes through here so the
"never update in place, only insert" invariant lives in one place."""

import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from studyhelp.db.models import Event


async def log_event(
    session: AsyncSession,
    *,
    event_type: str,
    payload: dict[str, Any],
    session_id: uuid.UUID | None = None,
    user_id: uuid.UUID | None = None,
    problem_id: str | None = None,
    step_id: str | None = None,
) -> Event:
    event = Event(
        session_id=session_id,
        user_id=user_id,
        problem_id=problem_id,
        step_id=step_id,
        event_type=event_type,
        payload=payload,
    )
    session.add(event)
    await session.flush()
    return event
