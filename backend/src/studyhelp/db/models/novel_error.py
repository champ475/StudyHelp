from datetime import datetime
from typing import Any

from sqlalchemy import BigInteger, DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from studyhelp.db.base import Base


class NovelError(Base):
    """Semi-automated review queue (ARCHITECTURE.md D5, Feldman et al.
    2018): every LLM-classified (i.e. no buggy-rule match) error lands
    here. `cluster_id` is populated by `classification/clustering.py`,
    grouping structurally similar errors so a human reviewer confirms
    "this cluster is a new bug" once rather than triaging near-duplicates
    one at a time. Confirmed novel bugs get promoted into
    `buggy_rule_library`/`misconception_bank` — that promotion path is
    real-pilot-data scope (Phase 6), not built yet."""

    __tablename__ = "novel_errors"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    event_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("events.id"), nullable=True)
    topic: Mapped[str] = mapped_column(String(128), index=True)
    step_type: Mapped[str] = mapped_column(String(128))
    correct_step: Mapped[dict[str, Any]] = mapped_column(JSONB)
    student_step: Mapped[dict[str, Any]] = mapped_column(JSONB)
    discrepant_fields: Mapped[list[str]] = mapped_column(JSONB)
    llm_rationale: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    cluster_id: Mapped[str | None] = mapped_column(String(256), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
