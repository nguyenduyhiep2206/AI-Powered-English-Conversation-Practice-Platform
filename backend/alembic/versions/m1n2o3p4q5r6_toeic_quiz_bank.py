"""Add quiz_passages and TOEIC fields on quiz_questions

Revision ID: m1n2o3p4q5r6
Revises: l2m3n4o5p6q7
Create Date: 2026-07-28 14:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "m1n2o3p4q5r6"
down_revision: Union[str, Sequence[str], None] = "l2m3n4o5p6q7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

toeic_part_enum = postgresql.ENUM(
    "r5",
    "r6",
    "r7",
    "w1",
    "w2",
    "w3",
    name="toeic_part_enum",
    create_type=False,
)


def upgrade() -> None:
    op.execute(sa.text("ALTER TYPE quiz_question_type_enum ADD VALUE IF NOT EXISTS 'writing'"))

    toeic_part_enum.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "quiz_passages",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("book_id", sa.BigInteger(), nullable=True),
        sa.Column("unit_id", sa.BigInteger(), nullable=True),
        sa.Column("toeic_part", toeic_part_enum, nullable=False),
        sa.Column("body", sa.TEXT(), nullable=False),
        sa.Column("media_url", sa.String(length=1000), nullable=True),
        sa.Column(
            "status",
            postgresql.ENUM(
                "draft",
                "published",
                "rejected",
                name="quiz_question_status_enum",
                create_type=False,
            ),
            nullable=False,
            server_default="draft",
        ),
        sa.Column("meta", sa.JSON(), nullable=True),
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
        sa.ForeignKeyConstraint(["book_id"], ["books.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["unit_id"], ["book_structure_preview.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_quiz_passages_book_id", "quiz_passages", ["book_id"])
    op.create_index("ix_quiz_passages_toeic_part", "quiz_passages", ["toeic_part"])

    op.add_column(
        "quiz_questions",
        sa.Column("passage_id", sa.BigInteger(), nullable=True),
    )
    op.add_column(
        "quiz_questions",
        sa.Column("toeic_part", toeic_part_enum, nullable=True),
    )
    op.add_column(
        "quiz_questions",
        sa.Column("prompt_words", sa.JSON(), nullable=True),
    )
    op.add_column(
        "quiz_questions",
        sa.Column("media_url", sa.String(length=1000), nullable=True),
    )
    op.add_column(
        "quiz_questions",
        sa.Column("task_brief", sa.JSON(), nullable=True),
    )
    op.create_foreign_key(
        "fk_quiz_questions_passage_id",
        "quiz_questions",
        "quiz_passages",
        ["passage_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_quiz_questions_passage_id", "quiz_questions", ["passage_id"])
    op.create_index("ix_quiz_questions_toeic_part", "quiz_questions", ["toeic_part"])
    op.alter_column(
        "quiz_questions",
        "answer",
        existing_type=sa.String(length=500),
        server_default="",
        existing_nullable=False,
    )


def downgrade() -> None:
    op.alter_column(
        "quiz_questions",
        "answer",
        existing_type=sa.String(length=500),
        server_default=None,
        existing_nullable=False,
    )
    op.drop_index("ix_quiz_questions_toeic_part", table_name="quiz_questions")
    op.drop_index("ix_quiz_questions_passage_id", table_name="quiz_questions")
    op.drop_constraint("fk_quiz_questions_passage_id", "quiz_questions", type_="foreignkey")
    op.drop_column("quiz_questions", "task_brief")
    op.drop_column("quiz_questions", "media_url")
    op.drop_column("quiz_questions", "prompt_words")
    op.drop_column("quiz_questions", "toeic_part")
    op.drop_column("quiz_questions", "passage_id")
    op.drop_index("ix_quiz_passages_toeic_part", table_name="quiz_passages")
    op.drop_index("ix_quiz_passages_book_id", table_name="quiz_passages")
    op.drop_table("quiz_passages")
    op.execute(sa.text("DROP TYPE IF EXISTS toeic_part_enum"))
