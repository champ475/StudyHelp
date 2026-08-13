import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey
from sqlalchemy import Enum as SqlEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from studyhelp.db.base import Base


class ExperimentCondition(enum.StrEnum):
    """The three-condition study design (docs/approach.md §3): assigned and
    persisted per session from day one, per CLAUDE.md's explicit instruction
    that this must not be retrofitted later."""

    IMMEDIATE = "immediate"
    DELAYED = "delayed"
    CONTROL = "control"


class SessionModel(Base):
    """Named SessionModel, not Session, to avoid colliding with
    sqlalchemy.orm.Session."""

    __tablename__ = "sessions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    experiment_condition: Mapped[ExperimentCondition | None] = mapped_column(
        SqlEnum(
            ExperimentCondition,
            name="experiment_condition",
            values_callable=lambda enum_cls: [m.value for m in enum_cls],
        ),
        nullable=True,
    )
