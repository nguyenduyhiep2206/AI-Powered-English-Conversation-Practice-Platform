"""drop unused legacy chat/vocab/gamification tables

Revision ID: s8t9u0v1w2x3
Revises: r7s8t9u0v1w2
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision: str = "s8t9u0v1w2x3"
down_revision: Union[str, Sequence[str], None] = "r7s8t9u0v1w2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Children first so FKs do not block drops.
_DROP_TABLES: tuple[str, ...] = (
    "story_answers",
    "story_vocab_items",
    "story_exercises",
    "story_vocab_selections",
    "vocabulary_bank",
    "chat_messages",
    "chat_sessions",
    "quiz_sessions",
    "user_streaks",
    "user_badges",
    "notifications",
    "password_reset_tokens",
)

_DROP_ENUMS: tuple[str, ...] = (
    "session_status_enum",
    "message_role_enum",
    "register_enum",
    "vocab_source_enum",
    "selection_status_enum",
    "exercise_status_enum",
    "quiz_type_enum",
    "notification_type_enum",
)


def upgrade() -> None:
    bind = op.get_bind()
    tables = set(inspect(bind).get_table_names())
    for name in _DROP_TABLES:
        if name in tables:
            op.drop_table(name)

    for enum_name in _DROP_ENUMS:
        op.execute(sa.text(f"DROP TYPE IF EXISTS {enum_name}"))


def downgrade() -> None:
    bind = op.get_bind()
    tables = set(inspect(bind).get_table_names())

    if "chat_sessions" not in tables:
        op.create_table(
            "chat_sessions",
            sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
            sa.Column("user_id", sa.BigInteger(), nullable=False),
            sa.Column("scenario_id", sa.BigInteger(), nullable=False),
            sa.Column(
                "status",
                sa.Enum("active", "completed", "abandoned", name="session_status_enum"),
                nullable=False,
            ),
            sa.Column("clarity_score", sa.SmallInteger(), nullable=True),
            sa.Column("message_count", sa.SmallInteger(), nullable=False),
            sa.Column("duration_sec", sa.Integer(), nullable=False),
            sa.Column("feedback_summary", sa.JSON(), nullable=True),
            sa.Column(
                "started_at",
                sa.TIMESTAMP(timezone=True),
                server_default=sa.text("now()"),
                nullable=False,
            ),
            sa.Column("ended_at", sa.TIMESTAMP(timezone=True), nullable=True),
            sa.ForeignKeyConstraint(["scenario_id"], ["scenarios.id"], ondelete="RESTRICT"),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(op.f("ix_chat_sessions_scenario_id"), "chat_sessions", ["scenario_id"])
        op.create_index(op.f("ix_chat_sessions_user_id"), "chat_sessions", ["user_id"])

    if "notifications" not in tables:
        op.create_table(
            "notifications",
            sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
            sa.Column("user_id", sa.BigInteger(), nullable=False),
            sa.Column(
                "type",
                sa.Enum(
                    "daily_reminder",
                    "streak_alert",
                    "milestone",
                    "weekly_digest",
                    name="notification_type_enum",
                ),
                nullable=False,
            ),
            sa.Column("title", sa.String(length=255), nullable=False),
            sa.Column("body", sa.TEXT(), nullable=True),
            sa.Column("is_read", sa.Boolean(), nullable=False),
            sa.Column("send_at", sa.TIMESTAMP(timezone=True), nullable=False),
            sa.Column(
                "created_at",
                sa.TIMESTAMP(timezone=True),
                server_default=sa.text("now()"),
                nullable=False,
            ),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(op.f("ix_notifications_user_id"), "notifications", ["user_id"])

    if "quiz_sessions" not in tables:
        op.create_table(
            "quiz_sessions",
            sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
            sa.Column("user_id", sa.BigInteger(), nullable=False),
            sa.Column(
                "quiz_type",
                sa.Enum(
                    "word_snap",
                    "fix_the_chat",
                    "context_challenge",
                    "streak_quiz",
                    name="quiz_type_enum",
                ),
                nullable=False,
            ),
            sa.Column("score", sa.SmallInteger(), nullable=False),
            sa.Column("total_q", sa.SmallInteger(), nullable=False),
            sa.Column("correct_q", sa.SmallInteger(), nullable=False),
            sa.Column("lives_used", sa.SmallInteger(), nullable=False),
            sa.Column("completed", sa.Boolean(), nullable=False),
            sa.Column(
                "created_at",
                sa.TIMESTAMP(timezone=True),
                server_default=sa.text("now()"),
                nullable=False,
            ),
            sa.Column("ended_at", sa.TIMESTAMP(timezone=True), nullable=True),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(op.f("ix_quiz_sessions_user_id"), "quiz_sessions", ["user_id"])

    if "story_vocab_selections" not in tables:
        op.create_table(
            "story_vocab_selections",
            sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
            sa.Column("user_id", sa.BigInteger(), nullable=False),
            sa.Column("name", sa.String(length=150), nullable=True),
            sa.Column(
                "status",
                sa.Enum(
                    "draft",
                    "generating",
                    "generated",
                    "archived",
                    name="selection_status_enum",
                ),
                nullable=False,
            ),
            sa.Column("word_count", sa.SmallInteger(), nullable=False),
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
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(
            op.f("ix_story_vocab_selections_user_id"),
            "story_vocab_selections",
            ["user_id"],
        )

    if "user_badges" not in tables:
        op.create_table(
            "user_badges",
            sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
            sa.Column("user_id", sa.BigInteger(), nullable=False),
            sa.Column("badge_code", sa.String(length=100), nullable=False),
            sa.Column("badge_name", sa.String(length=150), nullable=False),
            sa.Column(
                "earned_at",
                sa.TIMESTAMP(timezone=True),
                server_default=sa.text("now()"),
                nullable=False,
            ),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("user_id", "badge_code", name="uq_user_badge"),
        )
        op.create_index(op.f("ix_user_badges_user_id"), "user_badges", ["user_id"])

    if "user_streaks" not in tables:
        op.create_table(
            "user_streaks",
            sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
            sa.Column("user_id", sa.BigInteger(), nullable=False),
            sa.Column("current_streak", sa.SmallInteger(), nullable=False),
            sa.Column("longest_streak", sa.SmallInteger(), nullable=False),
            sa.Column("last_activity", sa.DATE(), nullable=True),
            sa.Column("total_sessions", sa.Integer(), nullable=False),
            sa.Column("total_words", sa.Integer(), nullable=False),
            sa.Column(
                "updated_at",
                sa.TIMESTAMP(timezone=True),
                server_default=sa.text("now()"),
                nullable=False,
            ),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("user_id"),
        )

    if "chat_messages" not in tables:
        op.create_table(
            "chat_messages",
            sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
            sa.Column("session_id", sa.BigInteger(), nullable=False),
            sa.Column(
                "role",
                sa.Enum("user", "assistant", name="message_role_enum"),
                nullable=False,
            ),
            sa.Column("content", sa.TEXT(), nullable=False),
            sa.Column("feedback", sa.JSON(), nullable=True),
            sa.Column(
                "created_at",
                sa.TIMESTAMP(timezone=True),
                server_default=sa.text("now()"),
                nullable=False,
            ),
            sa.ForeignKeyConstraint(["session_id"], ["chat_sessions.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(op.f("ix_chat_messages_session_id"), "chat_messages", ["session_id"])

    if "story_exercises" not in tables:
        op.create_table(
            "story_exercises",
            sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
            sa.Column("user_id", sa.BigInteger(), nullable=False),
            sa.Column("selection_id", sa.BigInteger(), nullable=False),
            sa.Column("title", sa.String(length=255), nullable=False),
            sa.Column("content", sa.TEXT(), nullable=False),
            sa.Column("blanks", sa.JSON(), nullable=False),
            sa.Column("total_blanks", sa.SmallInteger(), nullable=False),
            sa.Column(
                "status",
                sa.Enum("pending", "in_progress", "completed", name="exercise_status_enum"),
                nullable=False,
            ),
            sa.Column("score", sa.SmallInteger(), nullable=True),
            sa.Column(
                "generated_at",
                sa.TIMESTAMP(timezone=True),
                server_default=sa.text("now()"),
                nullable=False,
            ),
            sa.Column("completed_at", sa.TIMESTAMP(timezone=True), nullable=True),
            sa.ForeignKeyConstraint(
                ["selection_id"], ["story_vocab_selections.id"], ondelete="RESTRICT"
            ),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(
            op.f("ix_story_exercises_selection_id"),
            "story_exercises",
            ["selection_id"],
        )
        op.create_index(op.f("ix_story_exercises_user_id"), "story_exercises", ["user_id"])

    if "vocabulary_bank" not in tables:
        op.create_table(
            "vocabulary_bank",
            sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
            sa.Column("user_id", sa.BigInteger(), nullable=False),
            sa.Column("word", sa.String(length=150), nullable=False),
            sa.Column("definition", sa.TEXT(), nullable=False),
            sa.Column("example", sa.TEXT(), nullable=True),
            sa.Column("synonyms", sa.JSON(), nullable=True),
            sa.Column(
                "register",
                sa.Enum("formal", "informal", "neutral", "technical", name="register_enum"),
                nullable=True,
            ),
            sa.Column(
                "source",
                sa.Enum("chat", "suggestion", "bookmark", "quiz", name="vocab_source_enum"),
                nullable=False,
            ),
            sa.Column("session_id", sa.BigInteger(), nullable=True),
            sa.Column("srs_level", sa.SmallInteger(), nullable=False),
            sa.Column("next_review", sa.DATE(), nullable=True),
            sa.Column("review_count", sa.SmallInteger(), nullable=False),
            sa.Column("correct_streak", sa.SmallInteger(), nullable=False),
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
            sa.ForeignKeyConstraint(["session_id"], ["chat_sessions.id"], ondelete="SET NULL"),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(op.f("ix_vocabulary_bank_session_id"), "vocabulary_bank", ["session_id"])
        op.create_index(op.f("ix_vocabulary_bank_user_id"), "vocabulary_bank", ["user_id"])

    if "story_answers" not in tables:
        op.create_table(
            "story_answers",
            sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
            sa.Column("exercise_id", sa.BigInteger(), nullable=False),
            sa.Column("vocab_id", sa.BigInteger(), nullable=False),
            sa.Column("blank_pos", sa.SmallInteger(), nullable=False),
            sa.Column("user_answer", sa.String(length=255), nullable=False),
            sa.Column("is_correct", sa.Boolean(), nullable=False),
            sa.Column("ai_feedback", sa.TEXT(), nullable=True),
            sa.Column(
                "answered_at",
                sa.TIMESTAMP(timezone=True),
                server_default=sa.text("now()"),
                nullable=False,
            ),
            sa.ForeignKeyConstraint(["exercise_id"], ["story_exercises.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["vocab_id"], ["vocabulary_bank.id"], ondelete="RESTRICT"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("exercise_id", "blank_pos", name="uq_exercise_blank_pos"),
        )
        op.create_index(op.f("ix_story_answers_exercise_id"), "story_answers", ["exercise_id"])

    if "story_vocab_items" not in tables:
        op.create_table(
            "story_vocab_items",
            sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
            sa.Column("selection_id", sa.BigInteger(), nullable=False),
            sa.Column("vocab_id", sa.BigInteger(), nullable=False),
            sa.Column(
                "added_at",
                sa.TIMESTAMP(timezone=True),
                server_default=sa.text("now()"),
                nullable=False,
            ),
            sa.ForeignKeyConstraint(
                ["selection_id"], ["story_vocab_selections.id"], ondelete="CASCADE"
            ),
            sa.ForeignKeyConstraint(["vocab_id"], ["vocabulary_bank.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("selection_id", "vocab_id", name="uq_selection_vocab"),
        )
        op.create_index(
            op.f("ix_story_vocab_items_selection_id"),
            "story_vocab_items",
            ["selection_id"],
        )
        op.create_index(
            op.f("ix_story_vocab_items_vocab_id"),
            "story_vocab_items",
            ["vocab_id"],
        )

    # Orphan table that existed in DB without a tracked migration/model.
    tables = set(inspect(bind).get_table_names())
    if "password_reset_tokens" not in tables:
        op.create_table(
            "password_reset_tokens",
            sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
            sa.Column("user_id", sa.BigInteger(), nullable=False),
            sa.Column("token_hash", sa.String(length=64), nullable=False),
            sa.Column("expires_at", sa.TIMESTAMP(), nullable=False),
            sa.Column("consumed_at", sa.TIMESTAMP(), nullable=True),
            sa.Column("created_at", sa.TIMESTAMP(), nullable=False),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("token_hash", name="uq_password_reset_token_hash"),
        )
        op.create_index(
            "ix_password_reset_tokens_token_hash",
            "password_reset_tokens",
            ["token_hash"],
            unique=True,
        )
        op.create_index(
            "ix_password_reset_tokens_user_id",
            "password_reset_tokens",
            ["user_id"],
        )
