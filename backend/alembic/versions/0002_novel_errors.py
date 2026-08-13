"""Add novel_errors: the semi-automated review queue for LLM-classified
(no buggy-rule match) errors.

Revision ID: 0002
Revises: 0001
Create Date: 2026-08-14
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "novel_errors",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("event_id", sa.BigInteger(), sa.ForeignKey("events.id"), nullable=True),
        sa.Column("topic", sa.String(length=128), nullable=False, index=True),
        sa.Column("step_type", sa.String(length=128), nullable=False),
        sa.Column("correct_step", postgresql.JSONB(), nullable=False),
        sa.Column("student_step", postgresql.JSONB(), nullable=False),
        sa.Column("discrepant_fields", postgresql.JSONB(), nullable=False),
        sa.Column("llm_rationale", sa.String(length=2000), nullable=True),
        sa.Column("cluster_id", sa.String(length=256), nullable=True, index=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
    )


def downgrade() -> None:
    op.drop_table("novel_errors")
