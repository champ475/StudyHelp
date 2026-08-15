from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, DateTime, Integer, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from studyhelp.db.base import Base


class ProblemModel(Base):
    """A problem authored against the step-graph schema
    (`schemas.step_schema.Problem`), stored whole as JSONB. The row is the
    unit of versioning (`version`/`is_active`); the DAG shape itself is not
    normalized into rows — the verifier reads it as a document."""

    __tablename__ = "problems"

    id: Mapped[str] = mapped_column(String(128), primary_key=True)
    ncert_class: Mapped[int] = mapped_column(Integer)
    ncert_chapter: Mapped[int] = mapped_column(Integer)
    ncert_chapter_title: Mapped[str] = mapped_column(String(256))
    topic: Mapped[str] = mapped_column(String(128), index=True)
    display_label: Mapped[str] = mapped_column(String(256))
    given: Mapped[dict[str, Any]] = mapped_column(JSONB)
    final_answer: Mapped[Any] = mapped_column(JSONB)
    step_graph: Mapped[list[dict[str, Any]]] = mapped_column(JSONB)
    alt_paths: Mapped[list[dict[str, Any]] | None] = mapped_column(JSONB, nullable=True)
    version: Mapped[int] = mapped_column(Integer, default=1)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
