"""add tutor_sessions and tutor_messages tables

Revision ID: t9u0v1w2x3y4
Revises: s8t9u0v1w2x3
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "t9u0v1w2x3y4"
down_revision: Union[str, Sequence[str], None] = "s8t9u0v1w2x3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

tutor_session_status_enum = postgresql.ENUM(
    "active",
    "completed",
    "abandoned",
    name="tutor_session_status_enum",
    create_type=False,
)

tutor_message_role_enum = postgresql.ENUM(
    "user",
    "assistant",
    name="tutor_message_role_enum",
    create_type=False,
)


def upgrade() -> None:
    tutor_session_status_enum.create(op.get_bind(), checkfirst=True)
    tutor_message_role_enum.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "tutor_sessions",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("roadmap_step_id", sa.BigInteger(), nullable=False),
        sa.Column("scenario_id", sa.BigInteger(), nullable=False),
        sa.Column("status", tutor_session_status_enum, nullable=False),
        sa.Column(
            "target_skill_ids",
            postgresql.JSON(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column("message_count", sa.SmallInteger(), nullable=False, server_default="0"),
        sa.Column("summary", postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column(
            "started_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("ended_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["roadmap_step_id"], ["roadmap_steps.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(["scenario_id"], ["scenarios.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_tutor_sessions_user_id"), "tutor_sessions", ["user_id"], unique=False
    )
    op.create_index(
        op.f("ix_tutor_sessions_roadmap_step_id"),
        "tutor_sessions",
        ["roadmap_step_id"],
        unique=False,
    )

    op.create_table(
        "tutor_messages",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("session_id", sa.BigInteger(), nullable=False),
        sa.Column("role", tutor_message_role_enum, nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("meta", postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["session_id"], ["tutor_sessions.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_tutor_messages_session_id"),
        "tutor_messages",
        ["session_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_tutor_messages_session_id"), table_name="tutor_messages")
    op.drop_table("tutor_messages")
    op.drop_index(op.f("ix_tutor_sessions_roadmap_step_id"), table_name="tutor_sessions")
    op.drop_index(op.f("ix_tutor_sessions_user_id"), table_name="tutor_sessions")
    op.drop_table("tutor_sessions")
    tutor_message_role_enum.drop(op.get_bind(), checkfirst=True)
    tutor_session_status_enum.drop(op.get_bind(), checkfirst=True)
