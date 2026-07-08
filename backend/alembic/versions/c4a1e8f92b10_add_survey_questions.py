"""add survey_questions table and seed default survey

Revision ID: c4a1e8f92b10
Revises: b8f3b22e1c8a
Create Date: 2026-07-07 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "c4a1e8f92b10"
down_revision: Union[str, Sequence[str], None] = "b8f3b22e1c8a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

survey_question_type_enum = postgresql.ENUM(
    "single_choice",
    "text",
    name="survey_question_type_enum",
    create_type=False,
)

SURVEY_QUESTIONS = [
    {
        "prompt": "What is your occupation?",
        "question_type": "single_choice",
        "options": [
            {"value": "Developer", "label": "Developer"},
            {"value": "Marketing", "label": "Marketing"},
            {"value": "Student", "label": "Student"},
            {"value": "Business", "label": "Business"},
            {"value": "Other", "label": "Other"},
        ],
        "maps_to_profile_field": "occupation",
        "priority": 100,
    },
    {
        "prompt": "What is your main learning goal?",
        "question_type": "single_choice",
        "options": [
            {"value": "job_interview", "label": "Job interview"},
            {"value": "daily_conversation", "label": "Daily conversation"},
            {"value": "travel", "label": "Travel"},
            {"value": "ielts", "label": "IELTS"},
            {"value": "business", "label": "Business English"},
        ],
        "maps_to_profile_field": "goal",
        "priority": 90,
    },
    {
        "prompt": "Which area do you want to improve most?",
        "question_type": "single_choice",
        "options": [
            {"value": "grammar", "label": "Grammar"},
            {"value": "vocabulary", "label": "Vocabulary"},
            {"value": "confidence", "label": "Speaking confidence"},
            {"value": "writing", "label": "Writing"},
        ],
        "maps_to_profile_field": "weak_point",
        "priority": 80,
    },
    {
        "prompt": "How much time can you study each day?",
        "question_type": "single_choice",
        "options": [
            {"value": "15", "label": "15 minutes"},
            {"value": "30", "label": "30 minutes"},
            {"value": "60", "label": "60+ minutes"},
        ],
        "maps_to_profile_field": "daily_time_min",
        "priority": 70,
    },
]


def upgrade() -> None:
    survey_question_type_enum.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "survey_questions",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("prompt", sa.String(length=500), nullable=False),
        sa.Column("question_type", survey_question_type_enum, nullable=False),
        sa.Column("options", postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column("maps_to_profile_field", sa.String(length=50), nullable=True),
        sa.Column("priority", sa.SmallInteger(), server_default="0", nullable=False),
        sa.Column("is_required", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
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
        sa.PrimaryKeyConstraint("id"),
    )

    survey_questions = sa.table(
        "survey_questions",
        sa.column("prompt", sa.String),
        sa.column("question_type", sa.String),
        sa.column("options", postgresql.JSON),
        sa.column("maps_to_profile_field", sa.String),
        sa.column("priority", sa.SmallInteger),
        sa.column("is_required", sa.Boolean),
        sa.column("is_active", sa.Boolean),
    )
    op.bulk_insert(survey_questions, SURVEY_QUESTIONS)


def downgrade() -> None:
    op.drop_table("survey_questions")
    survey_question_type_enum.drop(op.get_bind(), checkfirst=True)
