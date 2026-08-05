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
    skill = (
        await db.execute(select(LearningSkillDB).where(LearningSkillDB.id == skill_id))
    ).scalar_one_or_none()
    if skill is None:
        raise ValueError("Skill not found")

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
    published = [x for x in lessons if x.status == "published"]
    primary_lesson = next(
        (x for x in published if int(x.pack_index or 0) == 0),
        published[0] if published else (lessons[0] if lessons else None),
    )
    lesson_status = (
        "published"
        if published
        else (primary_lesson.status if primary_lesson is not None else None)
    )
    lesson_payload = {
        "status": lesson_status,
        "id": int(primary_lesson.id) if primary_lesson is not None else None,
        "title": primary_lesson.title if primary_lesson is not None else None,
        "pack_published_count": len(published),
        "pack_total": len(lessons),
    }
    surfaces = surfaces_from_lessons(published)
    has_surfaces = bool(surfaces) if lesson_status == "published" else False
    # Published grammar without surfaces still blocks (same as generate path).
    if lesson_status == "published" and skill_type == "grammar":
        has_surfaces = bool(surfaces)

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
    book_source = None
    if primary is not None:
        book_source = {
            "book_id": int(primary.book_id),
            "unit_id": int(primary.unit_id),
            "unit_title": primary.unit_title,
            "is_primary": bool(primary.is_primary),
        }

    draft_count = int(
        (
            await db.execute(
                select(func.count())
                .select_from(QuizQuestionDB)
                .where(
                    QuizQuestionDB.skill_id == skill_id,
                    QuizQuestionDB.status == QuizQuestionStatusEnum.draft,
                )
            )
        ).scalar_one()
    )
    published_count = int(
        (
            await db.execute(
                select(func.count())
                .select_from(QuizQuestionDB)
                .where(
                    QuizQuestionDB.skill_id == skill_id,
                    QuizQuestionDB.status == QuizQuestionStatusEnum.published,
                )
            )
        ).scalar_one()
    )

    # Count drafts whose task_brief.mode == skill_drill (best-effort in Python)
    draft_rows = list(
        (
            await db.execute(
                select(QuizQuestionDB).where(
                    QuizQuestionDB.skill_id == skill_id,
                    QuizQuestionDB.status == QuizQuestionStatusEnum.draft,
                )
            )
        )
        .scalars()
        .all()
    )
    draft_skill_drill_count = 0
    for row in draft_rows:
        brief = row.task_brief if isinstance(row.task_brief, dict) else {}
        if brief.get("mode") == "skill_drill":
            draft_skill_drill_count += 1

    gate = compute_quiz_gate(
        skill_type=skill_type,
        lesson_status=lesson_status,
        has_book_source=primary is not None,
        has_lesson_surfaces=has_surfaces if skill_type == "grammar" else True,
    )

    return {
        "skill": {
            "id": int(skill.id),
            "title": skill.title,
            "skill_type": skill_type,
            "cefr_level": cefr,
        },
        "lesson": lesson_payload,
        "book_source": book_source,
        "quiz": {
            "draft_count": draft_count,
            "published_count": published_count,
            "draft_skill_drill_count": draft_skill_drill_count,
            "can_generate_skill_drill": gate.can_generate,
            "block_reason": gate.block_reason,
        },
    }
