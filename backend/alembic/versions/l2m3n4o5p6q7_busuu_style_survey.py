"""Busuu-style survey: extend goal_enum and rewrite survey questions

Revision ID: l2m3n4o5p6q7
Revises: k1l2m3n4o5p6
Create Date: 2026-07-28 00:00:00.000000

"""
from typing import Sequence, Union

import json

import sqlalchemy as sa
from alembic import op

revision: str = "l2m3n4o5p6q7"
down_revision: Union[str, Sequence[str], None] = "k1l2m3n4o5p6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

NEW_GOAL_VALUES = ("work", "school", "culture", "family", "challenge", "other")

BUSUU_GOAL_OPTIONS = [
    {"value": "work", "label": "Work"},
    {"value": "school", "label": "School"},
    {"value": "travel", "label": "Travel"},
    {"value": "culture", "label": "Culture"},
    {"value": "family", "label": "Family & community"},
    {"value": "challenge", "label": "Challenge myself"},
    {"value": "other", "label": "Other"},
]

BUSUU_DAILY_TIME_OPTIONS = [
    {"value": "5", "label": "5 minutes / day — Casual"},
    {"value": "10", "label": "10 minutes / day — Regular"},
    {"value": "15", "label": "15 minutes / day — Serious"},
    {"value": "25", "label": "25 minutes / day — Intense"},
]

LEGACY_GOAL_OPTIONS = [
    {"value": "job_interview", "label": "Job interview"},
    {"value": "daily_conversation", "label": "Daily conversation"},
    {"value": "travel", "label": "Travel"},
    {"value": "ielts", "label": "IELTS"},
    {"value": "business", "label": "Business English"},
]

LEGACY_DAILY_TIME_OPTIONS = [
    {"value": "15", "label": "15 minutes"},
    {"value": "30", "label": "30 minutes"},
    {"value": "60", "label": "60+ minutes"},
]


def upgrade() -> None:
    for value in NEW_GOAL_VALUES:
        op.execute(
            sa.text(f"ALTER TYPE goal_enum ADD VALUE IF NOT EXISTS '{value}'")
        )

    op.execute(
        sa.text(
            """
            UPDATE survey_questions
            SET is_active = false
            WHERE maps_to_profile_field IN ('occupation', 'weak_point')
            """
        )
    )

    op.execute(
        sa.text(
            """
            UPDATE survey_questions
            SET prompt = :prompt,
                options = CAST(:options AS json)
            WHERE maps_to_profile_field = 'goal'
              AND is_active = true
            """
        ).bindparams(
            prompt="Why are you learning English?",
            options=json.dumps(BUSUU_GOAL_OPTIONS),
        )
    )

    op.execute(
        sa.text(
            """
            UPDATE survey_questions
            SET prompt = :prompt,
                options = CAST(:options AS json)
            WHERE maps_to_profile_field = 'daily_time_min'
              AND is_active = true
            """
        ).bindparams(
            prompt="Set a daily study goal",
            options=json.dumps(BUSUU_DAILY_TIME_OPTIONS),
        )
    )


def downgrade() -> None:
    op.execute(
        sa.text(
            """
            UPDATE survey_questions
            SET is_active = true
            WHERE maps_to_profile_field IN ('occupation', 'weak_point')
            """
        )
    )

    op.execute(
        sa.text(
            """
            UPDATE survey_questions
            SET prompt = :prompt,
                options = CAST(:options AS json)
            WHERE maps_to_profile_field = 'goal'
              AND is_active = true
            """
        ).bindparams(
            prompt="What is your main learning goal?",
            options=json.dumps(LEGACY_GOAL_OPTIONS),
        )
    )

    op.execute(
        sa.text(
            """
            UPDATE survey_questions
            SET prompt = :prompt,
                options = CAST(:options AS json)
            WHERE maps_to_profile_field = 'daily_time_min'
              AND is_active = true
            """
        ).bindparams(
            prompt="How much time can you study each day?",
            options=json.dumps(LEGACY_DAILY_TIME_OPTIONS),
        )
    )
