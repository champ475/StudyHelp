import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import BigInteger, DateTime, ForeignKey, Index, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from studyhelp.db.base import Base


class Event(Base):
    """Append-only event log — the research dataset (technical_architecture.md
    §8). `event_type` values used from Phase 1: "step_submitted", "verdict".
    Reserved for later phases: "error_type", "turn", "resolution",
    "escalation". Never updated in place; only ever inserted."""

    __tablename__ = "events"
    __table_args__ = (
        Index("ix_events_session_created", "session_id", "created_at"),
        Index("ix_events_problem_event_type", "problem_id", "event_type"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    session_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("sessions.id"), nullable=True
    )
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    problem_id: Mapped[str | None] = mapped_column(
        String(128), ForeignKey("problems.id"), nullable=True
    )
    step_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    event_type: Mapped[str] = mapped_column(String(64))
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
