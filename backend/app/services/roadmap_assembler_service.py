"""Assemble a CEFR-level personal roadmap from learning skills + mastery."""

from __future__ import annotations

from collections import defaultdict
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import (
    CEFRLevel,
    GoalEnum,
    ProgressStatusEnum,
    ScenarioCategoryEnum,
    WeakPointEnum,
)
from app.models.learning_skill import LearningSkillDB, SkillEdgeDB
from app.models.profile import UserProfileDB
from app.models.roadmap_step_skill import RoadmapStepSkillDB
from app.models.scenario import RoadmapStepDB, ScenarioDB, UserProgressDB
from app.models.user_skill_mastery import UserSkillMasteryDB
from app.services.mastery_service import DEFAULT_PRIOR, MASTERY_STRONG

GOAL_TO_CATEGORY: dict[GoalEnum, ScenarioCategoryEnum] = {
    GoalEnum.job_interview: ScenarioCategoryEnum.job_interview,
    GoalEnum.daily_conversation: ScenarioCategoryEnum.small_talk,
    GoalEnum.travel: ScenarioCategoryEnum.travel,
    GoalEnum.ielts: ScenarioCategoryEnum.custom,
    GoalEnum.business: ScenarioCategoryEnum.job_interview,
}

DEFAULT_DIFFICULTY = 5
ZPD_WINDOW = 2


def _skill_type_value(skill: dict[str, Any] | LearningSkillDB) -> str:
    if isinstance(skill, dict):
        raw = skill.get("skill_type") or ""
    else:
        raw = skill.skill_type
    return raw.value if hasattr(raw, "value") else str(raw)


def _skill_as_dict(skill: LearningSkillDB | dict[str, Any]) -> dict[str, Any]:
    if isinstance(skill, dict):
        out = dict(skill)
        if out.get("difficulty_in_level") is None:
            out["difficulty_in_level"] = DEFAULT_DIFFICULTY
        return out
    difficulty = skill.difficulty_in_level
    return {
        "id": int(skill.id),
        "slug": skill.slug,
        "title": skill.title,
        "cefr_level": skill.cefr_level.value
        if hasattr(skill.cefr_level, "value")
        else str(skill.cefr_level),
        "skill_type": _skill_type_value(skill),
        "is_active": bool(skill.is_active),
        "difficulty_in_level": int(difficulty)
        if difficulty is not None
        else DEFAULT_DIFFICULTY,
    }


def _clamp_placement_score(placement_score: int | None) -> int:
    if placement_score is None:
        return 1
    score = int(placement_score)
    if score <= 0:
        return 1
    return min(10, score)


def _prereqs_met(
    skill_id: int,
    mastery: dict[int, float],
    prereq_from_by_to: dict[int, list[int]],
) -> bool:
    for from_id in prereq_from_by_to.get(skill_id, []):
        if float(mastery.get(int(from_id), DEFAULT_PRIOR)) < MASTERY_STRONG:
            return False
    return True


def select_skills_for_roadmap(
    skills: list[dict[str, Any]] | list[LearningSkillDB],
    mastery: dict[int, float],
    *,
    placement_score: int | None,
    prereq_from_by_to: dict[int, list[int]],
    max_steps: int = 10,
    weak_point: WeakPointEnum | str | None = None,
    window: int = ZPD_WINDOW,
) -> list[dict[str, Any]]:
    """Pick weak skills in ZPD window that have prerequisites mastered."""
    wp = weak_point.value if hasattr(weak_point, "value") else (weak_point or "")
    sub = _clamp_placement_score(placement_score)
    lo = max(1, sub)
    hi = min(10, sub + max(0, int(window)))
    max_steps = max(0, int(max_steps))

    prepared: list[dict[str, Any]] = []
    for raw in skills:
        skill = _skill_as_dict(raw)
        if not skill.get("is_active", True):
            continue
        skill_id = int(skill["id"])
        score = float(mastery.get(skill_id, DEFAULT_PRIOR))
        if score >= MASTERY_STRONG:
            continue
        if not _prereqs_met(skill_id, mastery, prereq_from_by_to):
            continue
        prepared.append(skill)

    def collect(low: int, high: int) -> list[tuple[dict[str, Any], float, int]]:
        out: list[tuple[dict[str, Any], float, int]] = []
        for skill in prepared:
            diff = int(skill.get("difficulty_in_level") or DEFAULT_DIFFICULTY)
            if diff < low or diff > high:
                continue
            skill_id = int(skill["id"])
            score = float(mastery.get(skill_id, DEFAULT_PRIOR))
            out.append((skill, score, diff))
        return out

    candidates = collect(lo, hi)
    while len(candidates) < max_steps and hi < 10:
        hi += 1
        candidates = collect(lo, hi)

    def sort_key(item: tuple[dict[str, Any], float, int]) -> tuple[int, int, float, int]:
        skill, score, diff = item
        matches_weak = 0 if wp and skill.get("skill_type") == wp else 1
        return (matches_weak, diff, score, int(skill["id"]))

    candidates.sort(key=sort_key)
    return [skill for skill, _score, _diff in candidates[:max_steps]]


async def load_active_skills(db: AsyncSession, level: CEFRLevel) -> list[LearningSkillDB]:
    result = await db.execute(
        select(LearningSkillDB).where(
            LearningSkillDB.cefr_level == level,
            LearningSkillDB.is_active.is_(True),
        )
    )
    return list(result.scalars().all())


async def load_mastery_map(db: AsyncSession, user_id: int) -> dict[int, float]:
    rows = list(
        (
            await db.execute(
                select(UserSkillMasteryDB).where(UserSkillMasteryDB.user_id == user_id)
            )
        )
        .scalars()
        .all()
    )
    return {int(r.skill_id): float(r.mastery) for r in rows}


async def load_prereq_map(
    db: AsyncSession, skill_ids: set[int]
) -> dict[int, list[int]]:
    """Map to_skill_id -> [from_skill_id, ...] for prerequisite edges within skill_ids."""
    if not skill_ids:
        return {}
    edges = list(
        (
            await db.execute(
                select(SkillEdgeDB).where(SkillEdgeDB.relation == "prerequisite")
            )
        )
        .scalars()
        .all()
    )
    prereq_from_by_to: dict[int, list[int]] = defaultdict(list)
    for edge in edges:
        frm = int(edge.from_skill_id)
        to = int(edge.to_skill_id)
        if frm in skill_ids and to in skill_ids:
            prereq_from_by_to[to].append(frm)
    return dict(prereq_from_by_to)


async def pick_scenario(
    db: AsyncSession,
    goal: GoalEnum | None,
    level: CEFRLevel,
) -> ScenarioDB:
    category = GOAL_TO_CATEGORY.get(goal) if goal is not None else None
    if category is not None:
        matched = (
            await db.execute(
                select(ScenarioDB)
                .where(
                    ScenarioDB.is_active.is_(True),
                    ScenarioDB.level == level,
                    ScenarioDB.category == category,
                )
                .order_by(ScenarioDB.order_index, ScenarioDB.id)
                .limit(1)
            )
        ).scalar_one_or_none()
        if matched is not None:
            return matched

    fallback = (
        await db.execute(
            select(ScenarioDB)
            .where(ScenarioDB.is_active.is_(True), ScenarioDB.level == level)
            .order_by(ScenarioDB.order_index, ScenarioDB.id)
            .limit(1)
        )
    ).scalar_one_or_none()
    if fallback is None:
        # Last resort: any active scenario
        fallback = (
            await db.execute(
                select(ScenarioDB)
                .where(ScenarioDB.is_active.is_(True))
                .order_by(ScenarioDB.order_index, ScenarioDB.id)
                .limit(1)
            )
        ).scalar_one_or_none()
    if fallback is None:
        raise ValueError("Chưa có scenario — seed scenarios trước khi assemble lộ trình")
    return fallback


async def clear_user_roadmap(db: AsyncSession, user_id: int) -> None:
    progress_rows = list(
        (
            await db.execute(select(UserProgressDB).where(UserProgressDB.user_id == user_id))
        )
        .scalars()
        .all()
    )
    step_ids = [int(p.roadmap_step_id) for p in progress_rows]
    if progress_rows:
        await db.execute(delete(UserProgressDB).where(UserProgressDB.user_id == user_id))

    for step_id in step_ids:
        remaining = (
            await db.execute(
                select(UserProgressDB.id).where(UserProgressDB.roadmap_step_id == step_id).limit(1)
            )
        ).scalar_one_or_none()
        if remaining is not None:
            continue
        await db.execute(
            delete(RoadmapStepSkillDB).where(RoadmapStepSkillDB.roadmap_step_id == step_id)
        )
        await db.execute(delete(RoadmapStepDB).where(RoadmapStepDB.id == step_id))


async def assemble_user_roadmap(
    db: AsyncSession,
    user_id: int,
    level: CEFRLevel | None = None,
    max_steps: int = 10,
) -> list[dict[str, Any]]:
    profile = (
        await db.execute(select(UserProfileDB).where(UserProfileDB.user_id == user_id))
    ).scalar_one_or_none()
    if profile is None:
        raise ValueError("User chưa có profile — hoàn thành onboarding trước")

    target_level = level or profile.current_level
    if target_level is None:
        raise ValueError("Thiếu CEFR level để lắp lộ trình")

    max_steps = max(8, min(12, int(max_steps)))
    skills = await load_active_skills(db, target_level)
    if not skills:
        raise ValueError(f"Chưa có learning_skills active cho level {target_level}")

    skill_ids = {int(s.id) for s in skills}
    mastery = await load_mastery_map(db, user_id)
    prereq_from_by_to = await load_prereq_map(db, skill_ids)
    selected = select_skills_for_roadmap(
        skills,
        mastery,
        placement_score=profile.placement_score,
        prereq_from_by_to=prereq_from_by_to,
        max_steps=max_steps,
        weak_point=profile.weak_point,
    )
    if not selected:
        raise ValueError("Không còn skill yếu để lắp lộ trình ở level này")

    scenario = await pick_scenario(db, profile.goal, target_level)
    await clear_user_roadmap(db, user_id)

    weeks: list[dict[str, Any]] = []
    for index, skill in enumerate(selected, start=1):
        step = RoadmapStepDB(
            level=target_level,
            week_number=index,
            title=f"Week {index}: {skill.get('title') or skill['slug']}",
            scenario_id=scenario.id,
            unlock_condition=None if index == 1 else f"complete_week_{index - 1}",
        )
        db.add(step)
        await db.flush()

        db.add(
            RoadmapStepSkillDB(
                roadmap_step_id=step.id,
                skill_id=int(skill["id"]),
                role="quiz",
            )
        )
        status = (
            ProgressStatusEnum.in_progress if index == 1 else ProgressStatusEnum.locked
        )
        db.add(
            UserProgressDB(
                user_id=user_id,
                roadmap_step_id=step.id,
                status=status,
            )
        )
        weeks.append(
            {
                "week_number": index,
                "roadmap_step_id": int(step.id),
                "title": step.title,
                "skill_id": int(skill["id"]),
                "skill_slug": skill["slug"],
                "skill_title": skill.get("title"),
                "skill_type": skill.get("skill_type"),
                "difficulty_in_level": int(
                    skill.get("difficulty_in_level") or DEFAULT_DIFFICULTY
                ),
                "scenario_id": int(scenario.id),
                "scenario_title": scenario.title,
                "status": status.value,
                "mastery": float(mastery.get(int(skill["id"]), DEFAULT_PRIOR)),
                "level": target_level.value
                if hasattr(target_level, "value")
                else str(target_level),
            }
        )

    await db.commit()
    return weeks


async def _load_progress_step_rows(
    db: AsyncSession, user_id: int
) -> list[tuple[UserProgressDB, RoadmapStepDB, ScenarioDB]]:
    return list(
        (
            await db.execute(
                select(UserProgressDB, RoadmapStepDB, ScenarioDB)
                .join(RoadmapStepDB, RoadmapStepDB.id == UserProgressDB.roadmap_step_id)
                .join(ScenarioDB, ScenarioDB.id == RoadmapStepDB.scenario_id)
                .where(UserProgressDB.user_id == user_id)
                .order_by(RoadmapStepDB.week_number, RoadmapStepDB.id)
            )
        ).all()
    )


async def _load_quiz_skill_id_by_step(
    db: AsyncSession, step_ids: list[int]
) -> dict[int, int]:
    if not step_ids:
        return {}
    link_rows = list(
        (
            await db.execute(
                select(RoadmapStepSkillDB).where(
                    RoadmapStepSkillDB.roadmap_step_id.in_(step_ids),
                    RoadmapStepSkillDB.role == "quiz",
                )
            )
        )
        .scalars()
        .all()
    )
    return {int(link.roadmap_step_id): int(link.skill_id) for link in link_rows}


async def _load_skills_by_id(
    db: AsyncSession, skill_ids: set[int]
) -> dict[int, LearningSkillDB]:
    if not skill_ids:
        return {}
    skill_rows = list(
        (
            await db.execute(select(LearningSkillDB).where(LearningSkillDB.id.in_(skill_ids)))
        )
        .scalars()
        .all()
    )
    return {int(s.id): s for s in skill_rows}


def _fallback_skill_dict(skill_id: int) -> dict[str, Any]:
    return {
        "id": skill_id,
        "slug": f"skill-{skill_id}",
        "title": None,
        "skill_type": None,
        "difficulty_in_level": DEFAULT_DIFFICULTY,
    }


def _week_dict_from_row(
    progress: UserProgressDB,
    step: RoadmapStepDB,
    scenario: ScenarioDB,
    *,
    skill_id: int,
    skill: LearningSkillDB | None,
    mastery: dict[int, float],
) -> dict[str, Any]:
    skill_dict = _skill_as_dict(skill) if skill is not None else _fallback_skill_dict(skill_id)
    status = progress.status
    level = step.level
    return {
        "week_number": int(step.week_number),
        "roadmap_step_id": int(step.id),
        "title": step.title,
        "skill_id": skill_id,
        "skill_slug": skill_dict["slug"],
        "skill_title": skill_dict.get("title"),
        "skill_type": skill_dict.get("skill_type"),
        "difficulty_in_level": int(
            skill_dict.get("difficulty_in_level") or DEFAULT_DIFFICULTY
        ),
        "scenario_id": int(scenario.id),
        "scenario_title": scenario.title,
        "status": status.value if hasattr(status, "value") else str(status),
        "mastery": float(mastery.get(skill_id, DEFAULT_PRIOR)),
        "level": level.value if hasattr(level, "value") else str(level),
    }


async def get_user_roadmap(db: AsyncSession, user_id: int) -> list[dict[str, Any]]:
    """Return the learner's current path (same week dict shape as assemble)."""
    rows = await _load_progress_step_rows(db, user_id)
    if not rows:
        return []

    step_ids = [int(step.id) for _progress, step, _scenario in rows]
    skill_id_by_step = await _load_quiz_skill_id_by_step(db, step_ids)
    skills = await _load_skills_by_id(db, set(skill_id_by_step.values()))
    mastery = await load_mastery_map(db, user_id)

    weeks: list[dict[str, Any]] = []
    for progress, step, scenario in rows:
        skill_id = skill_id_by_step.get(int(step.id))
        if skill_id is None:
            continue
        weeks.append(
            _week_dict_from_row(
                progress,
                step,
                scenario,
                skill_id=skill_id,
                skill=skills.get(skill_id),
                mastery=mastery,
            )
        )
    return weeks
