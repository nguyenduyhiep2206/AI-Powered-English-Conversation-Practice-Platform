"""Shared quiz-bank helpers for adaptive placement and level challenge."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import CEFRLevel, QuizQuestionStatusEnum
from app.models.learning_skill import LearningSkillDB
from app.models.quiz_question import QuizQuestionDB
from app.services.mastery_service import grade_mcq

CEFR_ORDER: tuple[CEFRLevel, ...] = (
    CEFRLevel.A1,
    CEFRLevel.A2,
    CEFRLevel.B1,
    CEFRLevel.B2,
    CEFRLevel.C1,
)


@dataclass(frozen=True)
class PlacementCandidate:
    id: int
    skill_id: int
    cefr_level: CEFRLevel
    question_type: str
    stem: str
    options: list[str] | None
    difficulty: str
    answer: str
    passage: str | None = None


def grade_placement_answer(expected: str, given: str) -> bool:
    return grade_mcq(expected, given)


def placement_public_dict(c: PlacementCandidate) -> dict[str, Any]:
    """Serialize a candidate for the learner API without leaking the answer."""
    return {
        "id": c.id,
        "skill_id": c.skill_id,
        "cefr_level": c.cefr_level.value if hasattr(c.cefr_level, "value") else str(c.cefr_level),
        "question_type": c.question_type,
        "stem": c.stem,
        "passage": c.passage,
        "options": c.options,
        "difficulty": c.difficulty,
    }


def row_to_candidate(question: QuizQuestionDB, skill: LearningSkillDB) -> PlacementCandidate:
    qtype = question.question_type
    return PlacementCandidate(
        id=int(question.id),
        skill_id=int(question.skill_id),
        cefr_level=skill.cefr_level,
        question_type=qtype.value if hasattr(qtype, "value") else str(qtype),
        stem=question.stem,
        options=list(question.options) if question.options else None,
        difficulty=question.difficulty or "medium",
        answer=question.answer,
        passage=question.passage,
    )


async def load_published_candidates(db: AsyncSession) -> list[PlacementCandidate]:
    q = (
        select(QuizQuestionDB, LearningSkillDB)
        .join(LearningSkillDB, LearningSkillDB.id == QuizQuestionDB.skill_id)
        .where(
            QuizQuestionDB.status == QuizQuestionStatusEnum.published,
            LearningSkillDB.is_active.is_(True),
        )
    )
    rows = (await db.execute(q)).all()
    return [row_to_candidate(question, skill) for question, skill in rows]
