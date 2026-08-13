import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, String, func
from sqlalchemy import Enum as SqlEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from studyhelp.db.base import Base


class UserRole(enum.StrEnum):
    STUDENT = "student"
    PARENT = "parent"
    TEACHER = "teacher"
    ADMIN = "admin"


class User(Base):
    """Stub for Phase 1 — no auth logic yet. Real accounts/consent flow is
    gated on DPDP legal review before any real child's data is collected
    (ARCHITECTURE.md D18); Phase 4's frontend uses this only for a local
    dev-mode identity picker, not real students."""

    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email: Mapped[str | None] = mapped_column(String(256), nullable=True)
    role: Mapped[UserRole] = mapped_column(
        SqlEnum(
            UserRole, name="user_role", values_callable=lambda enum_cls: [m.value for m in enum_cls]
        )
    )
    display_name: Mapped[str] = mapped_column(String(128))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
