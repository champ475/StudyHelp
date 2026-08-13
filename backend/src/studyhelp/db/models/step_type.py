from typing import Any

from sqlalchemy import String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from studyhelp.db.base import Base


class StepType(Base):
    """A `(topic, step_type_key)` pair — the shared vocabulary that keys the
    step graph, the verifier, and the misconception bank consistently
    (ARCHITECTURE.md D1's "step type is a first-class field")."""

    __tablename__ = "step_types"
    __table_args__ = (UniqueConstraint("topic", "step_type_key", name="uq_step_types_topic_key"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    topic: Mapped[str] = mapped_column(String(128), index=True)
    step_type_key: Mapped[str] = mapped_column(String(128))
    description: Mapped[str] = mapped_column(Text)
    structured_input_schema: Mapped[dict[str, Any]] = mapped_column(JSONB)
