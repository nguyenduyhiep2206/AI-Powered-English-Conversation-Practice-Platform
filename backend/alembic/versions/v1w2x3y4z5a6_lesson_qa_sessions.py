"""add lesson_qa_sessions and lesson_qa_messages tables

Revision ID: v1w2x3y4z5a6
Revises: u0v1w2x3y4z5
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "v1w2x3y4z5a6"
down_revision: Union[str, Sequence[str], None] = "u0v1w2x3y4z5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

lesson_qa_session_status_enum = postgresql.ENUM(
    "active",
    "ended",
    name="lesson_qa_session_status_enum",
    create_type=False,
)

lesson_qa_message_role_enum = postgresql.ENUM(
    "user",
    "assistant",
    "system",
    name="lesson_qa_message_role_enum",
    create_type=False,
)


def upgrade() -> None:
    lesson_qa_session_status_enum.create(op.get_bind(), checkfirst=True)
    lesson_qa_message_role_enum.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "lesson_qa_sessions",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("skill_id", sa.BigInteger(), nullable=False),
        sa.Column("status", lesson_qa_session_status_enum, nullable=False),
        sa.Column("message_count", sa.SmallInteger(), nullable=False, server_default="0"),
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
            ["skill_id"], ["learning_skills.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "skill_id", name="uq_lesson_qa_user_skill"),
    )
    op.create_index(
        op.f("ix_lesson_qa_sessions_user_id"),
        "lesson_qa_sessions",
        ["user_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_lesson_qa_sessions_skill_id"),
        "lesson_qa_sessions",
        ["skill_id"],
        unique=False,
    )

    op.create_table(
        "lesson_qa_messages",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("session_id", sa.BigInteger(), nullable=False),
        sa.Column("role", lesson_qa_message_role_enum, nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("meta", postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["session_id"], ["lesson_qa_sessions.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_lesson_qa_messages_session_id"),
        "lesson_qa_messages",
        ["session_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_lesson_qa_messages_session_id"), table_name="lesson_qa_messages"
    )
    op.drop_table("lesson_qa_messages")
    op.drop_index(
        op.f("ix_lesson_qa_sessions_skill_id"), table_name="lesson_qa_sessions"
    )
    op.drop_index(op.f("ix_lesson_qa_sessions_user_id"), table_name="lesson_qa_sessions")
    op.drop_table("lesson_qa_sessions")
    lesson_qa_message_role_enum.drop(op.get_bind(), checkfirst=True)
    lesson_qa_session_status_enum.drop(op.get_bind(), checkfirst=True)
