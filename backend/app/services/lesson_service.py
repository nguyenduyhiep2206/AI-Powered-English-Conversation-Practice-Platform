"""Serve published mini-unit lessons and lesson progress."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.book_skill_source import BookSkillSourceDB
from app.models.enums import QuizQuestionStatusEnum
from app.models.learning_skill import LearningSkillDB
from app.models.quiz_question import QuizQuestionDB
from app.models.skill_lesson import SkillLessonDB, UserLessonProgressDB
from app.models.user_skill_mastery import UserSkillMasteryDB
from app.services.lesson_generation_service import lesson_to_dict
from app.services.mastery_service import MASTERY_STRONG


def compute_learn_available(*, flag: bool, has_published: bool) -> bool:
    return bool(flag and has_published)


def compute_can_skip(*, lesson_completed: bool, mastery: float) -> bool:
    return bool(lesson_completed or mastery >= MASTERY_STRONG)


async def _get_mastery(db: AsyncSession, user_id: int, skill_id: int) -> float:
    row = (
        await db.execute(
            select(UserSkillMasteryDB).where(
                UserSkillMasteryDB.user_id == user_id,
                UserSkillMasteryDB.skill_id == skill_id,
            )
        )
    ).scalar_one_or_none()
    if row is None:
        return 0.0
    return float(row.mastery or 0.0)


async def _get_progress(
    db: AsyncSession, user_id: int, skill_id: int
) -> UserLessonProgressDB | None:
    return (
        await db.execute(
            select(UserLessonProgressDB).where(
                UserLessonProgressDB.user_id == user_id,
                UserLessonProgressDB.skill_id == skill_id,
            )
        )
    ).scalar_one_or_none()


async def get_published_lesson(db: AsyncSession, skill_id: int) -> SkillLessonDB | None:
    return (
        await db.execute(
            select(SkillLessonDB).where(
                SkillLessonDB.skill_id == skill_id,
                SkillLessonDB.status == "published",
            )
        )
    ).scalar_one_or_none()


async def get_lesson_for_user(
    db: AsyncSession, user_id: int, skill_id: int
) -> dict[str, Any]:
    skill = (
        await db.execute(select(LearningSkillDB).where(LearningSkillDB.id == skill_id))
    ).scalar_one_or_none()
    if skill is None:
        raise ValueError("Skill not found")

    lesson = await get_published_lesson(db, skill_id)
    progress = await _get_progress(db, user_id, skill_id)
    mastery = await _get_mastery(db, user_id, skill_id)
    lesson_completed = progress is not None
    learn_available = compute_learn_available(
        flag=bool(getattr(settings, "LEARN_UNIT_ENABLED", False)),
        has_published=lesson is not None,
    )
    can_skip = compute_can_skip(lesson_completed=lesson_completed, mastery=mastery)

    return {
        "learn_available": learn_available,
        "can_skip": can_skip,
        "lesson_completed": lesson_completed,
        "mastery": mastery,
        "lesson": lesson_to_dict(lesson) if lesson is not None else None,
    }


async def complete_lesson(db: AsyncSession, user_id: int, skill_id: int) -> dict[str, Any]:
    skill = (
        await db.execute(select(LearningSkillDB).where(LearningSkillDB.id == skill_id))
    ).scalar_one_or_none()
    if skill is None:
        raise ValueError("Skill not found")

    progress = await _get_progress(db, user_id, skill_id)
    if progress is None:
        progress = UserLessonProgressDB(
            user_id=user_id,
            skill_id=skill_id,
            completed_at=datetime.now(timezone.utc),
        )
        db.add(progress)
        await db.commit()
    return await get_lesson_for_user(db, user_id, skill_id)



def attach_quiz_book_badges(
    rows: list[dict[str, Any]],
    *,
    draft_by_skill: dict[int, int],
    published_by_skill: dict[int, int],
    skills_with_book: set[int],
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for row in rows:
        enriched = dict(row)
        sid = int(enriched["skill_id"])
        enriched["quiz_draft_count"] = int(draft_by_skill.get(sid, 0))
        enriched["quiz_published_count"] = int(published_by_skill.get(sid, 0))
        enriched["has_book_source"] = sid in skills_with_book
        out.append(enriched)
    return out


async def list_skills_with_lesson_status(
    db: AsyncSession, *, cefr_level: str | None = None
) -> list[dict[str, Any]]:
    q = select(LearningSkillDB).where(LearningSkillDB.is_active.is_(True))
    if cefr_level:
        q = q.where(LearningSkillDB.cefr_level == cefr_level)
    skills = list((await db.execute(q.order_by(LearningSkillDB.id))).scalars().all())
    skill_ids = [int(s.id) for s in skills]
    lessons = {
        int(row.skill_id): row
        for row in (
            await db.execute(
                select(SkillLessonDB).where(SkillLessonDB.skill_id.in_(skill_ids))
            )
        ).scalars().all()
    } if skill_ids else {}

    draft_by_skill: dict[int, int] = {}
    published_by_skill: dict[int, int] = {}
    skills_with_book: set[int] = set()
    if skill_ids:
        count_rows = (
            await db.execute(
                select(
                    QuizQuestionDB.skill_id,
                    QuizQuestionDB.status,
                    func.count().label("n"),
                )
                .where(QuizQuestionDB.skill_id.in_(skill_ids))
                .group_by(QuizQuestionDB.skill_id, QuizQuestionDB.status)
            )
        ).all()
        for skill_id, status, n in count_rows:
            sid = int(skill_id)
            status_val = status.value if hasattr(status, "value") else str(status)
            if status_val == QuizQuestionStatusEnum.draft.value or status_val == "draft":
                draft_by_skill[sid] = int(n)
            elif (
                status_val == QuizQuestionStatusEnum.published.value
                or status_val == "published"
            ):
                published_by_skill[sid] = int(n)

        book_ids = (
            await db.execute(
                select(BookSkillSourceDB.skill_id)
                .where(
                    BookSkillSourceDB.skill_id.in_(skill_ids),
                    BookSkillSourceDB.is_excluded.is_(False),
                )
                .distinct()
            )
        ).scalars().all()
        skills_with_book = {int(sid) for sid in book_ids}

    out: list[dict[str, Any]] = []
    for skill in skills:
        lesson = lessons.get(int(skill.id))
        out.append(
            {
                "skill_id": int(skill.id),
                "title": skill.title,
                "skill_type": skill.skill_type.value
                if hasattr(skill.skill_type, "value")
                else str(skill.skill_type),
                "cefr_level": skill.cefr_level.value
                if hasattr(skill.cefr_level, "value")
                else str(skill.cefr_level),
                "lesson_status": lesson.status if lesson else None,
                "lesson_id": int(lesson.id) if lesson else None,
            }
        )
    return attach_quiz_book_badges(
        out,
        draft_by_skill=draft_by_skill,
        published_by_skill=published_by_skill,
        skills_with_book=skills_with_book,
    )


async def get_admin_lesson(db: AsyncSession, skill_id: int) -> dict[str, Any]:
    lesson = (
        await db.execute(select(SkillLessonDB).where(SkillLessonDB.skill_id == skill_id))
    ).scalar_one_or_none()
    if lesson is None:
        raise ValueError("Lesson not found")
    return lesson_to_dict(lesson)
