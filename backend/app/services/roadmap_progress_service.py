"""Complete roadmap weeks when skill mastery passes the gate; unlock next week."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import ProgressStatusEnum
from app.models.roadmap_step_skill import RoadmapStepSkillDB
from app.models.scenario import RoadmapStepDB, UserProgressDB
from app.models.user_skill_mastery import UserSkillMasteryDB
from app.services.mastery_service import DEFAULT_PRIOR, MASTERY_STRONG


def can_pass_week(mastery: float, threshold: float = MASTERY_STRONG) -> bool:
    return float(mastery) >= float(threshold)


async def _require_in_progress(
    db: AsyncSession, user_id: int, roadmap_step_id: int
) -> tuple[UserProgressDB, RoadmapStepDB]:
    progress = (
        await db.execute(
            select(UserProgressDB).where(
                UserProgressDB.user_id == user_id,
                UserProgressDB.roadmap_step_id == roadmap_step_id,
            )
        )
    ).scalar_one_or_none()
    if progress is None:
        raise ValueError("Không tìm thấy tiến độ cho bước lộ trình này")
    if progress.status != ProgressStatusEnum.in_progress:
        raise ValueError("Chỉ hoàn thành được tuần đang in_progress")

    step = (
        await db.execute(select(RoadmapStepDB).where(RoadmapStepDB.id == roadmap_step_id))
    ).scalar_one_or_none()
    if step is None:
        raise ValueError("Không tìm thấy roadmap step")
    return progress, step


async def _quiz_skill_id(db: AsyncSession, roadmap_step_id: int) -> int:
    link = (
        await db.execute(
            select(RoadmapStepSkillDB).where(
                RoadmapStepSkillDB.roadmap_step_id == roadmap_step_id,
                RoadmapStepSkillDB.role == "quiz",
            )
        )
    ).scalar_one_or_none()
    if link is None:
        raise ValueError("Bước lộ trình chưa gắn skill quiz")
    return int(link.skill_id)


async def _mastery_for_skill(
    db: AsyncSession, user_id: int, skill_id: int
) -> float:
    row = (
        await db.execute(
            select(UserSkillMasteryDB).where(
                UserSkillMasteryDB.user_id == user_id,
                UserSkillMasteryDB.skill_id == skill_id,
            )
        )
    ).scalar_one_or_none()
    return float(row.mastery) if row is not None else DEFAULT_PRIOR


async def _unlock_next_week(
    db: AsyncSession, user_id: int, current_week: int
) -> int | None:
    rows = list(
        (
            await db.execute(
                select(UserProgressDB, RoadmapStepDB)
                .join(RoadmapStepDB, RoadmapStepDB.id == UserProgressDB.roadmap_step_id)
                .where(
                    UserProgressDB.user_id == user_id,
                    RoadmapStepDB.week_number == current_week + 1,
                )
            )
        ).all()
    )
    for next_progress, _next_step in rows:
        if next_progress.status == ProgressStatusEnum.locked:
            next_progress.status = ProgressStatusEnum.in_progress
            return int(next_progress.roadmap_step_id)
    return None


async def complete_roadmap_week(
    db: AsyncSession,
    user_id: int,
    roadmap_step_id: int,
) -> dict[str, Any]:
    """Pass if mastery of the step's quiz skill >= MASTERY_STRONG; unlock next week."""
    progress, step = await _require_in_progress(db, user_id, roadmap_step_id)
    skill_id = await _quiz_skill_id(db, roadmap_step_id)
    mastery = await _mastery_for_skill(db, user_id, skill_id)
    if not can_pass_week(mastery):
        raise ValueError("Chưa đạt mastery 0.7 cho skill của tuần này")

    progress.status = ProgressStatusEnum.completed
    progress.completed_at = datetime.now(timezone.utc)
    unlocked_step_id = await _unlock_next_week(db, user_id, int(step.week_number))
    await db.commit()

    return {
        "step_id": int(roadmap_step_id),
        "status": ProgressStatusEnum.completed.value,
        "skill_id": skill_id,
        "mastery": mastery,
        "unlocked_step_id": unlocked_step_id,
    }
