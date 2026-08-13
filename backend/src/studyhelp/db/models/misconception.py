import enum
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKeyConstraint, Integer, String, Text, func
from sqlalchemy import Enum as SqlEnum
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from studyhelp.db.base import Base


class ReviewStatus(enum.StrEnum):
    SEED_CURATED = "seed_curated"
    PILOT_DERIVED = "pilot_derived"
    REVIEWED = "reviewed"
    PENDING = "pending"


class MisconceptionBankEntry(Base):
    """`technical_architecture.md §5`'s misconception bank fields, stored as
    a structured table (not a flat text file) keyed by `(topic, step_type)`
    for retrieve-don't-dump lookup (ARCHITECTURE.md, retrieval section)."""

    __tablename__ = "misconception_bank"
    __table_args__ = (
        ForeignKeyConstraint(
            ["topic", "step_type"],
            ["step_types.topic", "step_types.step_type_key"],
            name="fk_misconception_bank_step_type",
        ),
    )

    id: Mapped[str] = mapped_column(String(128), primary_key=True)
    topic: Mapped[str] = mapped_column(String(128), index=True)
    step_type: Mapped[str] = mapped_column(String(128))
    bug_signature: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    typical_mindset: Mapped[str] = mapped_column(Text)
    explanation_strategy: Mapped[str] = mapped_column(Text)
    example_dialogue: Mapped[list[dict[str, Any]]] = mapped_column(JSONB)
    source: Mapped[str] = mapped_column(Text)
    version: Mapped[int] = mapped_column(Integer, default=1)
    review_status: Mapped[ReviewStatus] = mapped_column(
        SqlEnum(
            ReviewStatus,
            name="review_status",
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
        ),
        default=ReviewStatus.SEED_CURATED,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
