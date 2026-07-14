"""Update learner skill mastery after each quiz answer."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user_skill_mastery import UserSkillMasteryDB

ALPHA = 0.25
BETA = 0.20
MASTERY_WEAK = 0.4
MASTERY_STRONG = 0.7
DEFAULT_PRIOR = 0.35


def next_mastery(current: float, correct: bool) -> float:
    m = max(0.0, min(1.0, current))
    if correct:
        m = m + ALPHA * (1.0 - m)
    else:
        m = m - BETA * m
    return max(0.0, min(1.0, m))


def grade_mcq(question_answer: str, user_answer: str) -> bool:
    return question_answer.strip().lower() == user_answer.strip().lower()


async def apply_answer(
    db: AsyncSession,
    user_id: int,
    skill_id: int,
    correct: bool,
) -> UserSkillMasteryDB:
    row = (
        await db.execute(
            select(UserSkillMasteryDB).where(
                UserSkillMasteryDB.user_id == user_id,
                UserSkillMasteryDB.skill_id == skill_id,
            )
        )
    ).scalar_one_or_none()
    if row is None:
        row = UserSkillMasteryDB(
            user_id=user_id,
            skill_id=skill_id,
            mastery=0.0,
            attempts=0,
            correct=0,
        )
        db.add(row)
        await db.flush()

    row.mastery = next_mastery(float(row.mastery), correct)
    row.attempts = int(row.attempts) + 1
    if correct:
        row.correct = int(row.correct) + 1
    await db.commit()
    await db.refresh(row)
    return row
