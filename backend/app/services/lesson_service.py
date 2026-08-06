"""Serve published mini-unit lessons and lesson progress (incl. LessonPack)."""

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
from app.models.skill_lesson import (
    SkillLessonDB,
    UserLessonPackProgressDB,
    UserLessonProgressDB,
)
from app.models.user_skill_mastery import UserSkillMasteryDB
from app.services.lesson_generation_service import lesson_to_dict
from app.services.lesson_writing_feedback import (
    feedback_on_writing,
    writing_context_from_lesson_content,
)
from app.services.mastery_service import MASTERY_STRONG


def compute_learn_available(*, flag: bool, has_published: bool) -> bool:
    return bool(flag and has_published)


def compute_can_skip(*, lesson_completed: bool, mastery: float) -> bool:
    return bool(lesson_completed or mastery >= MASTERY_STRONG)


def compute_pack_completed(
    *, published_indices: list[int], completed_indices: set[int]
) -> bool:
    if not published_indices:
        return False
    return set(published_indices).issubset(completed_indices)


def attach_quiz_book_badges(
    rows: list[dict[str, Any]],
    *,
    draft_by_skill: dict[int, int],
    published_by_skill: dict[int, int],
    skills_with_book: set[int],
) -> list[dict[str, Any]]:
    """Attach quiz counts + book-source flag onto skill list rows (pure)."""
    out: list[dict[str, Any]] = []
    for row in rows:
        sid = int(row["skill_id"])
        enriched = dict(row)
        enriched["quiz_draft_count"] = int(draft_by_skill.get(sid, 0))
        enriched["quiz_published_count"] = int(published_by_skill.get(sid, 0))
        enriched["has_book_source"] = sid in skills_with_book
        out.append(enriched)
    return out


def _pick_lesson_status(lessons: list[SkillLessonDB]) -> tuple[str | None, int | None]:
    if not lessons:
        return None, None
    published = [x for x in lessons if x.status == "published"]
    if published:
        first = sorted(published, key=lambda x: int(x.pack_index or 0))[0]
        return "published", int(first.id)
    draft = [x for x in lessons if x.status == "draft"]
    if draft:
        first = sorted(draft, key=lambda x: int(x.pack_index or 0))[0]
        return "draft", int(first.id)
    first = sorted(lessons, key=lambda x: int(x.pack_index or 0))[0]
    return first.status, int(first.id)


async def _require_skill(db: AsyncSession, skill_id: int) -> LearningSkillDB:
    skill = (
        await db.execute(select(LearningSkillDB).where(LearningSkillDB.id == skill_id))
    ).scalar_one_or_none()
    if skill is None:
        raise ValueError("Skill not found")
    return skill


def _skill_cefr(skill: LearningSkillDB | None, *, default: str = "A1") -> str:
    if skill is None:
        return default
    if hasattr(skill.cefr_level, "value"):
        return skill.cefr_level.value
    return str(skill.cefr_level or default)


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


async def _get_legacy_progress(
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


async def _completed_pack_indices(
    db: AsyncSession, user_id: int, skill_id: int
) -> set[int]:
    rows = list(
        (
            await db.execute(
                select(UserLessonPackProgressDB).where(
                    UserLessonPackProgressDB.user_id == user_id,
                    UserLessonPackProgressDB.skill_id == skill_id,
                )
            )
        )
        .scalars()
        .all()
    )
    indices = {int(r.pack_index) for r in rows}
    # Legacy: skill-level complete counts as pack_index 0 done.
    if 0 not in indices:
        legacy = await _get_legacy_progress(db, user_id, skill_id)
        if legacy is not None:
            indices.add(0)
    return indices


async def list_published_pack(db: AsyncSession, skill_id: int) -> list[SkillLessonDB]:
    return list(
        (
            await db.execute(
                select(SkillLessonDB)
                .where(
                    SkillLessonDB.skill_id == skill_id,
                    SkillLessonDB.status == "published",
                )
                .order_by(SkillLessonDB.pack_index.asc())
            )
        )
        .scalars()
        .all()
    )


async def get_published_lesson(
    db: AsyncSession, skill_id: int, *, pack_index: int | None = None
) -> SkillLessonDB | None:
    """Return one published lesson; default lowest pack_index (legacy-compatible)."""
    published = await list_published_pack(db, skill_id)
    if not published:
        return None
    if pack_index is not None:
        for row in published:
            if int(row.pack_index or 0) == int(pack_index):
                return row
        return None
    return published[0]


async def writing_feedback_for_skill(
    db: AsyncSession,
    skill_id: int,
    *,
    text: str,
    pack_index: int | None = None,
) -> dict[str, Any]:
    """Build AI writing feedback for a published lesson pack.

    Raises:
        LookupError: no published lesson for the skill/pack.
        ValueError: empty learner text (from feedback_on_writing).
        RuntimeError: LLM feedback unavailable.
    """
    lesson = await get_published_lesson(db, skill_id, pack_index=pack_index)
    if lesson is None:
        raise LookupError("Published lesson not found")
    skill = (
        await db.execute(select(LearningSkillDB).where(LearningSkillDB.id == skill_id))
    ).scalar_one_or_none()
    content = lesson.content if isinstance(lesson.content, dict) else {}
    prompt, must_use, targets, form_tips = writing_context_from_lesson_content(content)
    return feedback_on_writing(
        learner_text=text,
        writing_prompt=prompt,
        must_use=must_use,
        targets=targets,
        cefr=_skill_cefr(skill),
        form_tips=form_tips,
    )


async def get_current_published_lesson_for_user(
    db: AsyncSession, user_id: int, skill_id: int
) -> SkillLessonDB | None:
    """Published pack the learner is on (same pick as practice learn phase)."""
    published = await list_published_pack(db, skill_id)
    if not published:
        return None
    completed = await _completed_pack_indices(db, user_id, skill_id)
    for row in published:
        if int(row.pack_index or 0) not in completed:
            return row
    return published[-1]


def _assemble_lesson_payload(
    *,
    skill: LearningSkillDB,
    published: list[SkillLessonDB],
    completed: set[int],
    mastery: float,
    current: SkillLessonDB | None,
) -> dict[str, Any]:
    published_indices = [int(x.pack_index or 0) for x in published]
    pack_done = compute_pack_completed(
        published_indices=published_indices, completed_indices=completed
    )
    return {
        "skill_id": int(skill.id),
        "skill_title": str(skill.title or "").strip() or "This skill",
        "learn_available": compute_learn_available(
            flag=bool(getattr(settings, "LEARN_UNIT_ENABLED", False)),
            has_published=bool(published),
        ),
        "can_skip": compute_can_skip(lesson_completed=pack_done, mastery=mastery),
        "lesson_completed": pack_done,
        "pack_total": len(published),
        "pack_completed_count": len(set(published_indices) & completed),
        "pack": [lesson_to_dict(x) for x in published],
        "mastery": mastery,
        "lesson": lesson_to_dict(current) if current is not None else None,
    }


async def get_lesson_for_user(
    db: AsyncSession, user_id: int, skill_id: int
) -> dict[str, Any]:
    skill = await _require_skill(db, skill_id)
    published = await list_published_pack(db, skill_id)
    completed = await _completed_pack_indices(db, user_id, skill_id)
    mastery = await _get_mastery(db, user_id, skill_id)
    current = await get_current_published_lesson_for_user(db, user_id, skill_id)
    return _assemble_lesson_payload(
        skill=skill,
        published=published,
        completed=completed,
        mastery=mastery,
        current=current,
    )


async def _ensure_pack_progress_row(
    db: AsyncSession, user_id: int, skill_id: int, pack_index: int
) -> None:
    existing = (
        await db.execute(
            select(UserLessonPackProgressDB).where(
                UserLessonPackProgressDB.user_id == user_id,
                UserLessonPackProgressDB.skill_id == skill_id,
                UserLessonPackProgressDB.pack_index == pack_index,
            )
        )
    ).scalar_one_or_none()
    if existing is None:
        db.add(
            UserLessonPackProgressDB(
                user_id=user_id,
                skill_id=skill_id,
                pack_index=pack_index,
                completed_at=datetime.now(timezone.utc),
            )
        )


async def _ensure_legacy_progress_row(
    db: AsyncSession, user_id: int, skill_id: int
) -> None:
    legacy = await _get_legacy_progress(db, user_id, skill_id)
    if legacy is None:
        db.add(
            UserLessonProgressDB(
                user_id=user_id,
                skill_id=skill_id,
                completed_at=datetime.now(timezone.utc),
            )
        )


async def complete_lesson(
    db: AsyncSession,
    user_id: int,
    skill_id: int,
    *,
    pack_index: int = 0,
) -> dict[str, Any]:
    await _require_skill(db, skill_id)
    published = await list_published_pack(db, skill_id)
    published_indices = {int(x.pack_index or 0) for x in published}
    idx = int(pack_index)
    if published and idx not in published_indices:
        raise ValueError(f"pack_index {idx} is not published for this skill")

    await _ensure_pack_progress_row(db, user_id, skill_id, idx)
    # Keep legacy skill-level row when pack_index 0 completes (compat).
    if idx == 0:
        await _ensure_legacy_progress_row(db, user_id, skill_id)

    await db.flush()
    completed = await _completed_pack_indices(db, user_id, skill_id)
    if compute_pack_completed(
        published_indices=sorted(published_indices), completed_indices=completed
    ):
        await _ensure_legacy_progress_row(db, user_id, skill_id)

    await db.commit()
    return await get_lesson_for_user(db, user_id, skill_id)


async def _load_active_skills(
    db: AsyncSession, *, cefr_level: str | None
) -> list[LearningSkillDB]:
    q = select(LearningSkillDB).where(LearningSkillDB.is_active.is_(True))
    if cefr_level:
        q = q.where(LearningSkillDB.cefr_level == cefr_level)
    return list((await db.execute(q.order_by(LearningSkillDB.id))).scalars().all())


async def _load_lessons_by_skill(
    db: AsyncSession, skill_ids: list[int]
) -> dict[int, list[SkillLessonDB]]:
    lessons_by_skill: dict[int, list[SkillLessonDB]] = {sid: [] for sid in skill_ids}
    if not skill_ids:
        return lessons_by_skill
    for row in (
        await db.execute(
            select(SkillLessonDB).where(SkillLessonDB.skill_id.in_(skill_ids))
        )
    ).scalars().all():
        lessons_by_skill.setdefault(int(row.skill_id), []).append(row)
    return lessons_by_skill


async def _load_quiz_count_maps(
    db: AsyncSession, skill_ids: list[int]
) -> tuple[dict[int, int], dict[int, int]]:
    draft_by_skill: dict[int, int] = {}
    published_by_skill: dict[int, int] = {}
    if not skill_ids:
        return draft_by_skill, published_by_skill
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
    return draft_by_skill, published_by_skill


async def _load_skills_with_book(db: AsyncSession, skill_ids: list[int]) -> set[int]:
    if not skill_ids:
        return set()
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
    return {int(sid) for sid in book_ids}


def _base_skill_rows(
    skills: list[LearningSkillDB],
    lessons_by_skill: dict[int, list[SkillLessonDB]],
) -> list[dict[str, Any]]:
    base: list[dict[str, Any]] = []
    for skill in skills:
        lessons = lessons_by_skill.get(int(skill.id), [])
        status, lesson_id = _pick_lesson_status(lessons)
        published_n = sum(1 for x in lessons if x.status == "published")
        base.append(
            {
                "skill_id": int(skill.id),
                "title": skill.title,
                "skill_type": skill.skill_type.value
                if hasattr(skill.skill_type, "value")
                else str(skill.skill_type),
                "cefr_level": skill.cefr_level.value
                if hasattr(skill.cefr_level, "value")
                else str(skill.cefr_level),
                "lesson_status": status,
                "lesson_id": lesson_id,
                "pack_published_count": published_n,
            }
        )
    return base


async def list_skills_with_lesson_status(
    db: AsyncSession, *, cefr_level: str | None = None
) -> list[dict[str, Any]]:
    skills = await _load_active_skills(db, cefr_level=cefr_level)
    skill_ids = [int(s.id) for s in skills]
    lessons_by_skill = await _load_lessons_by_skill(db, skill_ids)
    draft_by_skill, published_by_skill = await _load_quiz_count_maps(db, skill_ids)
    skills_with_book = await _load_skills_with_book(db, skill_ids)
    base = _base_skill_rows(skills, lessons_by_skill)
    return attach_quiz_book_badges(
        base,
        draft_by_skill=draft_by_skill,
        published_by_skill=published_by_skill,
        skills_with_book=skills_with_book,
    )


async def get_admin_lesson(db: AsyncSession, skill_id: int) -> dict[str, Any]:
    rows = list(
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
    if not rows:
        raise ValueError("Lesson not found")
    primary = next((r for r in rows if int(r.pack_index or 0) == 0), rows[0])
    payload = lesson_to_dict(primary)
    payload["pack"] = [lesson_to_dict(r) for r in rows]
    return payload
