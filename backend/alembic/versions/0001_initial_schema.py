"""Initial schema: step_types, problems, misconception_bank,
buggy_rule_library, users, sessions, events.

Revision ID: 0001
Revises:
Create Date: 2026-08-13
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001"
down_revision: str | None = None
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "step_types",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("topic", sa.String(length=128), nullable=False, index=True),
        sa.Column("step_type_key", sa.String(length=128), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("structured_input_schema", postgresql.JSONB(), nullable=False),
        sa.UniqueConstraint("topic", "step_type_key", name="uq_step_types_topic_key"),
    )

    op.create_table(
        "problems",
        sa.Column("id", sa.String(length=128), primary_key=True),
        sa.Column("ncert_class", sa.Integer(), nullable=False),
        sa.Column("ncert_chapter", sa.Integer(), nullable=False),
        sa.Column("ncert_chapter_title", sa.String(length=256), nullable=False),
        sa.Column("topic", sa.String(length=128), nullable=False, index=True),
        sa.Column("given", postgresql.JSONB(), nullable=False),
        sa.Column("final_answer", postgresql.JSONB(), nullable=False),
        sa.Column("step_graph", postgresql.JSONB(), nullable=False),
        sa.Column("alt_paths", postgresql.JSONB(), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
    )

    op.create_table(
        "misconception_bank",
        sa.Column("id", sa.String(length=128), primary_key=True),
        sa.Column("topic", sa.String(length=128), nullable=False, index=True),
        sa.Column("step_type", sa.String(length=128), nullable=False),
        sa.Column("bug_signature", postgresql.JSONB(), nullable=True),
        sa.Column("typical_mindset", sa.Text(), nullable=False),
        sa.Column("explanation_strategy", sa.Text(), nullable=False),
        sa.Column("example_dialogue", postgresql.JSONB(), nullable=False),
        sa.Column("source", sa.Text(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column(
            "review_status",
            postgresql.ENUM(
                "seed_curated",
                "pilot_derived",
                "reviewed",
                "pending",
                name="review_status",
            ),
            nullable=False,
            server_default="seed_curated",
        ),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.ForeignKeyConstraint(
            ["topic", "step_type"],
            ["step_types.topic", "step_types.step_type_key"],
            name="fk_misconception_bank_step_type",
        ),
    )

    op.create_table(
        "buggy_rule_library",
        sa.Column("id", sa.String(length=128), primary_key=True),
        sa.Column("topic", sa.String(length=128), nullable=False, index=True),
        sa.Column("step_type", sa.String(length=128), nullable=False),
        sa.Column("bug_code", sa.String(length=128), nullable=False),
        sa.Column("signature_matcher", postgresql.JSONB(), nullable=False),
        sa.Column("citation", sa.Text(), nullable=False),
        sa.Column(
            "misconception_id",
            sa.String(length=128),
            sa.ForeignKey("misconception_bank.id"),
            nullable=True,
        ),
        sa.Column("example_pair", postgresql.JSONB(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.ForeignKeyConstraint(
            ["topic", "step_type"],
            ["step_types.topic", "step_types.step_type_key"],
            name="fk_buggy_rule_library_step_type",
        ),
    )

    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("email", sa.String(length=256), nullable=True),
        sa.Column(
            "role",
            postgresql.ENUM("student", "parent", "teacher", "admin", name="user_role"),
            nullable=False,
        ),
        sa.Column("display_name", sa.String(length=128), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
    )

    op.create_table(
        "sessions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "experiment_condition",
            postgresql.ENUM("immediate", "delayed", "control", name="experiment_condition"),
            nullable=True,
        ),
    )

    op.create_table(
        "events",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column(
            "session_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("sessions.id"), nullable=True
        ),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("problem_id", sa.String(length=128), sa.ForeignKey("problems.id"), nullable=True),
        sa.Column("step_id", sa.String(length=128), nullable=True),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("payload", postgresql.JSONB(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
    )
    op.create_index("ix_events_session_created", "events", ["session_id", "created_at"])
    op.create_index("ix_events_problem_event_type", "events", ["problem_id", "event_type"])


def downgrade() -> None:
    op.drop_index("ix_events_problem_event_type", table_name="events")
    op.drop_index("ix_events_session_created", table_name="events")
    op.drop_table("events")
    op.drop_table("sessions")
    op.drop_table("users")
    op.drop_table("buggy_rule_library")
    op.drop_table("misconception_bank")
    op.drop_table("problems")
    op.drop_table("step_types")
    op.execute("DROP TYPE IF EXISTS experiment_condition")
    op.execute("DROP TYPE IF EXISTS user_role")
    op.execute("DROP TYPE IF EXISTS review_status")
