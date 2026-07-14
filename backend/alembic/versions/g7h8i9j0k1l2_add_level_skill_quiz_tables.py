"""add learning skills, book sources, quiz bank, mastery tables

Revision ID: g7h8i9j0k1l2
Revises: a9b8c7d6e5f4
Create Date: 2026-07-14 20:30:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "g7h8i9j0k1l2"
down_revision: Union[str, Sequence[str], None] = "a9b8c7d6e5f4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

quiz_question_type_enum = postgresql.ENUM(
    "mcq",
    "cloze",
    "fix_grammar",
    name="quiz_question_type_enum",
    create_type=False,
)
quiz_question_status_enum = postgresql.ENUM(
    "draft",
    "published",
    "rejected",
    name="quiz_question_status_enum",
    create_type=False,
)
skill_type_enum = postgresql.ENUM(
    "grammar",
    "vocabulary",
    "reading",
    "functional",
    name="skill_type_enum",
    create_type=False,
)
cefr_level = postgresql.ENUM(
    "A1",
    "A2",
    "B1",
    "B2",
    "C1",
    name="cefr_level",
    create_type=False,
)


def upgrade() -> None:
    bind = op.get_bind()
    quiz_question_type_enum.create(bind, checkfirst=True)
    quiz_question_status_enum.create(bind, checkfirst=True)
    skill_type_enum.create(bind, checkfirst=True)

    op.create_table(
        "learning_skills",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("slug", sa.String(length=120), nullable=False),
        sa.Column("title", sa.String(length=500), nullable=False),
        sa.Column("cefr_level", cefr_level, nullable=False),
        sa.Column("skill_type", skill_type_enum, server_default="grammar", nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("slug", "cefr_level", name="uq_learning_skill_slug_cefr"),
    )
    op.create_index("ix_learning_skills_slug", "learning_skills", ["slug"])
    op.create_index("ix_learning_skills_cefr_level", "learning_skills", ["cefr_level"])

    op.create_table(
        "skill_edges",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("from_skill_id", sa.BigInteger(), nullable=False),
        sa.Column("to_skill_id", sa.BigInteger(), nullable=False),
        sa.Column("relation", sa.String(length=50), server_default="prerequisite", nullable=False),
        sa.ForeignKeyConstraint(["from_skill_id"], ["learning_skills.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["to_skill_id"], ["learning_skills.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("from_skill_id", "to_skill_id", name="uq_skill_edge"),
    )

    op.create_table(
        "book_skill_sources",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("skill_id", sa.BigInteger(), nullable=False),
        sa.Column("book_id", sa.BigInteger(), nullable=False),
        sa.Column("unit_id", sa.BigInteger(), nullable=False),
        sa.Column("unit_title", sa.String(length=500), nullable=False),
        sa.Column("section_title", sa.String(length=255), nullable=True),
        sa.Column("is_excluded", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("is_primary", sa.Boolean(), server_default="false", nullable=False),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["skill_id"], ["learning_skills.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["book_id"], ["books.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["unit_id"], ["book_structure_preview.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("book_id", "unit_id", name="uq_book_skill_source_unit"),
    )
    op.create_index("ix_book_skill_sources_skill_id", "book_skill_sources", ["skill_id"])
    op.create_index("ix_book_skill_sources_book_id", "book_skill_sources", ["book_id"])
    op.create_index("ix_book_skill_sources_unit_id", "book_skill_sources", ["unit_id"])

    op.create_table(
        "quiz_questions",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("skill_id", sa.BigInteger(), nullable=False),
        sa.Column("book_id", sa.BigInteger(), nullable=False),
        sa.Column("unit_id", sa.BigInteger(), nullable=False),
        sa.Column("question_type", quiz_question_type_enum, nullable=False),
        sa.Column("stem", sa.TEXT(), nullable=False),
        sa.Column("options", sa.JSON(), nullable=True),
        sa.Column("answer", sa.String(length=500), nullable=False),
        sa.Column("explanation", sa.TEXT(), nullable=True),
        sa.Column("cefr_level", cefr_level, nullable=True),
        sa.Column("difficulty", sa.String(length=20), server_default="medium", nullable=False),
        sa.Column("status", quiz_question_status_enum, server_default="draft", nullable=False),
        sa.Column("generation_batch_id", sa.String(length=64), nullable=True),
        sa.Column("source_chunk_ids", sa.JSON(), nullable=True),
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
        sa.ForeignKeyConstraint(["skill_id"], ["learning_skills.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["book_id"], ["books.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["unit_id"], ["book_structure_preview.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_quiz_questions_skill_id", "quiz_questions", ["skill_id"])
    op.create_index("ix_quiz_questions_book_id", "quiz_questions", ["book_id"])
    op.create_index(
        "ix_quiz_questions_generation_batch_id", "quiz_questions", ["generation_batch_id"]
    )

    op.create_table(
        "user_skill_mastery",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("skill_id", sa.BigInteger(), nullable=False),
        sa.Column("mastery", sa.Float(), server_default="0", nullable=False),
        sa.Column("attempts", sa.Integer(), server_default="0", nullable=False),
        sa.Column("correct", sa.Integer(), server_default="0", nullable=False),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["skill_id"], ["learning_skills.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "skill_id", name="uq_user_skill_mastery"),
    )
    op.create_index("ix_user_skill_mastery_user_id", "user_skill_mastery", ["user_id"])
    op.create_index("ix_user_skill_mastery_skill_id", "user_skill_mastery", ["skill_id"])

    op.create_table(
        "roadmap_step_skills",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("roadmap_step_id", sa.BigInteger(), nullable=False),
        sa.Column("skill_id", sa.BigInteger(), nullable=False),
        sa.Column("role", sa.String(length=50), server_default="quiz", nullable=False),
        sa.ForeignKeyConstraint(["roadmap_step_id"], ["roadmap_steps.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["skill_id"], ["learning_skills.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("roadmap_step_id", "skill_id", name="uq_step_skill"),
    )
    op.create_index(
        "ix_roadmap_step_skills_roadmap_step_id", "roadmap_step_skills", ["roadmap_step_id"]
    )
    op.create_index("ix_roadmap_step_skills_skill_id", "roadmap_step_skills", ["skill_id"])


def downgrade() -> None:
    op.drop_index("ix_roadmap_step_skills_skill_id", table_name="roadmap_step_skills")
    op.drop_index("ix_roadmap_step_skills_roadmap_step_id", table_name="roadmap_step_skills")
    op.drop_table("roadmap_step_skills")

    op.drop_index("ix_user_skill_mastery_skill_id", table_name="user_skill_mastery")
    op.drop_index("ix_user_skill_mastery_user_id", table_name="user_skill_mastery")
    op.drop_table("user_skill_mastery")

    op.drop_index("ix_quiz_questions_generation_batch_id", table_name="quiz_questions")
    op.drop_index("ix_quiz_questions_book_id", table_name="quiz_questions")
    op.drop_index("ix_quiz_questions_skill_id", table_name="quiz_questions")
    op.drop_table("quiz_questions")

    op.drop_index("ix_book_skill_sources_unit_id", table_name="book_skill_sources")
    op.drop_index("ix_book_skill_sources_book_id", table_name="book_skill_sources")
    op.drop_index("ix_book_skill_sources_skill_id", table_name="book_skill_sources")
    op.drop_table("book_skill_sources")

    op.drop_table("skill_edges")

    op.drop_index("ix_learning_skills_cefr_level", table_name="learning_skills")
    op.drop_index("ix_learning_skills_slug", table_name="learning_skills")
    op.drop_table("learning_skills")

    bind = op.get_bind()
    skill_type_enum.drop(bind, checkfirst=True)
    quiz_question_status_enum.drop(bind, checkfirst=True)
    quiz_question_type_enum.drop(bind, checkfirst=True)
