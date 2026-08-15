"""Add problems.display_label: a short, human-readable label per problem
(e.g. "52 - 25 (single borrow)"). Needed once the frontend's problem picker
moves from a hardcoded ~10-entry array to a real GET /problems catalog
covering the full 140-problem syllabus (ARCHITECTURE.md D43) -- the picker
needs *some* short string to show per problem, and deriving one generically
from `given` would require topic-specific logic the catalog endpoint is
meant to avoid.

Revision ID: 0003
Revises: 0002
Create Date: 2026-08-15
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "problems",
        sa.Column("display_label", sa.String(length=256), nullable=False, server_default=""),
    )
    op.alter_column("problems", "display_label", server_default=None)


def downgrade() -> None:
    op.drop_column("problems", "display_label")
