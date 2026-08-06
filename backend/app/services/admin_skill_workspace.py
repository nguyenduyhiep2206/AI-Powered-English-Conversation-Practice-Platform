"""Admin skill workspace status: lesson + quiz gate in one payload."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.book_skill_source import BookSkillSourceDB
from app.models.enums import QuizQuestionStatusEnum
from app.models.learning_skill import LearningSkillDB
from app.models.quiz_question import QuizQuestionDB
from app.models.skill_lesson import SkillLessonDB
from app.services.quiz_generation_service import surfaces_from_lessons

BLOCK_GRAMMAR_LESSON = "grammar_requires_published_lesson"
BLOCK_NO_BOOK = "no_book_source"


@dataclass(frozen=True)
class QuizGate:
    can_generate: bool
    block_reason: str | None


def compute_quiz_gate(
    *,
    skill_type: str,
    lesson_status: str | None,
    has_book_source: bool,
    has_lesson_surfaces: bool = True,
) -> QuizGate:
    """Pure gate used by workspace API and tests."""
    if not has_book_source:
        return QuizGate(False, BLOCK_NO_BOOK)
    st = (skill_type or "").strip().lower()
    if st == "grammar":
        if lesson_status != "published" or not has_lesson_surfaces:
            return QuizGate(False, BLOCK_GRAMMAR_LESSON)
    return QuizGate(True, None)


async def get_skill_workspace(db: AsyncSession, skill_id: int) -> dict[str, Any]:
    skill = await _require_skill(db, skill_id)
    skill_type, cefr = _skill_type_cefr(skill)
    lesson, has_surfaces = await _load_lesson_slice(db, skill_id)
    book_source = await _load_primary_book_source(db, skill_id)
    quiz_counts = await _load_quiz_counts(db, skill_id)
    gate = compute_quiz_gate(
        skill_type=skill_type,
        lesson_status=lesson["status"],
        has_book_source=book_source is not None,
        has_lesson_surfaces=has_surfaces if skill_type == "grammar" else True,
    )
    return _assemble_workspace(
        skill=skill,
        skill_type=skill_type,
        cefr=cefr,
        lesson=lesson,
        book_source=book_source,
        quiz_counts=quiz_counts,
        gate=gate,
    )


async def _require_skill(db: AsyncSession, skill_id: int) -> LearningSkillDB:
    skill = (
        await db.execute(select(LearningSkillDB).where(LearningSkillDB.id == skill_id))
    ).scalar_one_or_none()
    if skill is None:
        raise ValueError("Skill not found")
    return skill


def _skill_type_cefr(skill: LearningSkillDB) -> tuple[str, str]:
    skill_type = (
        skill.skill_type.value
        if hasattr(skill.skill_type, "value")
        else str(skill.skill_type)
    )
    cefr = (
        skill.cefr_level.value
        if hasattr(skill.cefr_level, "value")
        else str(skill.cefr_level)
    )
    return skill_type, cefr


def build_lesson_slice(
    lessons: list[SkillLessonDB],
) -> tuple[dict[str, Any], bool]:
    """Pure: summary payload + whether published pack has extractable surfaces."""
    published = [x for x in lessons if x.status == "published"]
    primary = next(
        (x for x in published if int(x.pack_index or 0) == 0),
        published[0] if published else (lessons[0] if lessons else None),
    )
    status = (
        "published"
        if published
        else (primary.status if primary is not None else None)
    )
    payload = {
        "status": status,
        "id": int(primary.id) if primary is not None else None,
        "title": primary.title if primary is not None else None,
        "pack_published_count": len(published),
        "pack_total": len(lessons),
    }
    has_surfaces = (
        bool(surfaces_from_lessons(published)) if status == "published" else False
    )
    return payload, has_surfaces


async def _load_lesson_slice(
    db: AsyncSession, skill_id: int
) -> tuple[dict[str, Any], bool]:
    lessons = list(
        (
            await db.execute(
                select(SkillLessonDB)
                .where(SkillLessonDB.skill_id == skill_id)
                .order_by(SkillLessonDB.pack_index.asc())
            )
        )
        .scalars()
        .all()
    )
    return build_lesson_slice(lessons)


async def _load_primary_book_source(
    db: AsyncSession, skill_id: int
) -> dict[str, Any] | None:
    sources = list(
        (
            await db.execute(
                select(BookSkillSourceDB).where(
                    BookSkillSourceDB.skill_id == skill_id,
                    BookSkillSourceDB.is_excluded.is_(False),
                )
            )
        )
        .scalars()
        .all()
    )
    primary = next((s for s in sources if s.is_primary), sources[0] if sources else None)
    if primary is None:
        return None
    return {
        "book_id": int(primary.book_id),
        "unit_id": int(primary.unit_id),
        "unit_title": primary.unit_title,
        "is_primary": bool(primary.is_primary),
    }


async def _count_quiz(
    db: AsyncSession,
    skill_id: int,
    *,
    status: QuizQuestionStatusEnum,
    skill_drill_only: bool = False,
) -> int:
    q = (
        select(func.count())
        .select_from(QuizQuestionDB)
        .where(
            QuizQuestionDB.skill_id == skill_id,
            QuizQuestionDB.status == status,
        )
    )
    if skill_drill_only:
        q = q.where(QuizQuestionDB.task_brief["mode"].as_string() == "skill_drill")
    return int((await db.execute(q)).scalar_one())


async def _load_quiz_counts(db: AsyncSession, skill_id: int) -> dict[str, int]:
    return {
        "draft_count": await _count_quiz(
            db, skill_id, status=QuizQuestionStatusEnum.draft
        ),
        "published_count": await _count_quiz(
            db, skill_id, status=QuizQuestionStatusEnum.published
        ),
        "draft_skill_drill_count": await _count_quiz(
            db,
            skill_id,
            status=QuizQuestionStatusEnum.draft,
            skill_drill_only=True,
        ),
    }


def _assemble_workspace(
    *,
    skill: LearningSkillDB,
    skill_type: str,
    cefr: str,
    lesson: dict[str, Any],
    book_source: dict[str, Any] | None,
    quiz_counts: dict[str, int],
    gate: QuizGate,
) -> dict[str, Any]:
    return {
        "skill": {
            "id": int(skill.id),
            "title": skill.title,
            "skill_type": skill_type,
            "cefr_level": cefr,
        },
        "lesson": lesson,
        "book_source": book_source,
        "quiz": {
            **quiz_counts,
            "can_generate_skill_drill": gate.can_generate,
            "block_reason": gate.block_reason,
        },
    }
