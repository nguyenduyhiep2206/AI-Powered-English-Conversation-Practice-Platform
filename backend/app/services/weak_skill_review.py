"""Light Review hub: weak skills at current CEFR level with published quiz."""

from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import QuizQuestionStatusEnum
from app.models.learning_skill import LearningSkillDB
from app.models.profile import UserProfileDB
from app.models.quiz_question import QuizQuestionDB
from app.models.user_skill_mastery import UserSkillMasteryDB
from app.services.mastery_service import MASTERY_STRONG


def pick_weak(
    rows: list[dict[str, Any]],
    *,
    threshold: float = MASTERY_STRONG,
    limit: int = 5,
) -> list[dict[str, Any]]:
    """Pure: keep mastery below threshold, sort ascending, apply limit."""
    weak = [r for r in rows if float(r.get("mastery") or 0.0) < float(threshold)]
    weak.sort(key=lambda r: (float(r.get("mastery") or 0.0), int(r.get("skill_id") or 0)))
    return weak[: max(0, int(limit))]


async def list_weak_skills(
    db: AsyncSession,
    user_id: int,
    *,
    limit: int = 5,
    threshold: float = MASTERY_STRONG,
) -> list[dict[str, Any]]:
    """Skills at profile.current_level with published quiz and mastery below threshold."""
    level = await _load_profile_level(db, user_id)
    if level is None:
        return []
    published_ids = await _published_skill_ids(db)
    if not published_ids:
        return []
    skills = await _skills_at_level_with_quiz(db, level=level, skill_ids=published_ids)
    if not skills:
        return []
    mastery_by_id = await _mastery_by_skill(
        db, user_id, [int(s.id) for s in skills]
    )
    candidates = _practiced_candidates(skills, mastery_by_id)
    return pick_weak(candidates, threshold=threshold, limit=limit)


async def _load_profile_level(db: AsyncSession, user_id: int) -> Any | None:
    profile = (
        await db.execute(select(UserProfileDB).where(UserProfileDB.user_id == user_id))
    ).scalar_one_or_none()
    if profile is None or profile.current_level is None:
        return None
    return profile.current_level


async def _published_skill_ids(db: AsyncSession) -> set[int]:
    return set(
        (
            await db.execute(
                select(QuizQuestionDB.skill_id)
                .where(QuizQuestionDB.status == QuizQuestionStatusEnum.published)
                .distinct()
            )
        )
        .scalars()
        .all()
    )


async def _skills_at_level_with_quiz(
    db: AsyncSession, *, level: Any, skill_ids: set[int]
) -> list[LearningSkillDB]:
    return list(
        (
            await db.execute(
                select(LearningSkillDB).where(
                    LearningSkillDB.is_active.is_(True),
                    LearningSkillDB.cefr_level == level,
                    LearningSkillDB.id.in_(skill_ids),
                )
            )
        )
        .scalars()
        .all()
    )


async def _mastery_by_skill(
    db: AsyncSession, user_id: int, skill_ids: list[int]
) -> dict[int, UserSkillMasteryDB]:
    if not skill_ids:
        return {}
    rows = list(
        (
            await db.execute(
                select(UserSkillMasteryDB).where(
                    UserSkillMasteryDB.user_id == user_id,
                    UserSkillMasteryDB.skill_id.in_(skill_ids),
                )
            )
        )
        .scalars()
        .all()
    )
    return {int(r.skill_id): r for r in rows}


def _practiced_candidates(
    skills: list[LearningSkillDB],
    mastery_by_id: dict[int, UserSkillMasteryDB],
) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    for skill in skills:
        sid = int(skill.id)
        row = mastery_by_id.get(sid)
        # Review only skills the learner has practiced at least once.
        if row is None or int(row.attempts or 0) < 1:
            continue
        candidates.append(
            {
                "skill_id": sid,
                "title": skill.title,
                "skill_slug": skill.slug,
                "mastery": float(row.mastery or 0.0),
                "attempts": int(row.attempts or 0),
            }
        )
    return candidates
