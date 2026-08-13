from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, ForeignKeyConstraint, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from studyhelp.db.base import Base


class BuggyRuleEntry(Base):
    """Pattern-matchable buggy-rule library entry (Brown & Burton /
    VanLehn tradition — ARCHITECTURE.md D4). `signature_matcher` is a
    declarative pattern; the matching *logic* is Phase 2's rule_matcher.py,
    not this table. `example_pair` doubles as a golden-suite fixture input
    (avoids authoring the same bug example twice)."""

    __tablename__ = "buggy_rule_library"
    __table_args__ = (
        ForeignKeyConstraint(
            ["topic", "step_type"],
            ["step_types.topic", "step_types.step_type_key"],
            name="fk_buggy_rule_library_step_type",
        ),
    )

    id: Mapped[str] = mapped_column(String(128), primary_key=True)
    topic: Mapped[str] = mapped_column(String(128), index=True)
    step_type: Mapped[str] = mapped_column(String(128))
    bug_code: Mapped[str] = mapped_column(String(128))
    signature_matcher: Mapped[dict[str, Any]] = mapped_column(JSONB)
    citation: Mapped[str] = mapped_column(Text)
    misconception_id: Mapped[str | None] = mapped_column(
        ForeignKey("misconception_bank.id"), nullable=True
    )
    example_pair: Mapped[dict[str, Any]] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
