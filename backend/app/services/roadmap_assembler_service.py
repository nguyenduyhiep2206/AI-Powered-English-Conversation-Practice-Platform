"""Assemble a CEFR-level personal roadmap from learning skills + mastery."""

from __future__ import annotations

from collections import defaultdict
from typing import Any

from sqlalchemy import case, delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import (
    CEFRLevel,
    GoalEnum,
    ProgressStatusEnum,
    ScenarioCategoryEnum,
)
from app.models.learning_skill import LearningSkillDB, SkillEdgeDB
from app.models.book_skill_source import BookSkillSourceDB
from app.models.profile import UserProfileDB
from app.models.roadmap_step_skill import RoadmapStepSkillDB
from app.models.scenario import RoadmapStepDB, ScenarioDB, UserProgressDB
from app.models.user_skill_mastery import UserSkillMasteryDB
from app.models.theme_unit import LearningThemeUnitDB, ThemeUnitSkillDB
from app.services.mastery_service import DEFAULT_PRIOR, MASTERY_STRONG

GOAL_TO_CATEGORY: dict[GoalEnum, ScenarioCategoryEnum] = {
    GoalEnum.job_interview: ScenarioCategoryEnum.job_interview,
    GoalEnum.daily_conversation: ScenarioCategoryEnum.small_talk,
    GoalEnum.travel: ScenarioCategoryEnum.travel,
    GoalEnum.ielts: ScenarioCategoryEnum.custom,
    GoalEnum.business: ScenarioCategoryEnum.job_interview,
    GoalEnum.work: ScenarioCategoryEnum.job_interview,
    GoalEnum.school: ScenarioCategoryEnum.custom,
    GoalEnum.culture: ScenarioCategoryEnum.small_talk,
    GoalEnum.family: ScenarioCategoryEnum.small_talk,
    GoalEnum.challenge: ScenarioCategoryEnum.small_talk,
    GoalEnum.other: ScenarioCategoryEnum.small_talk,
}

DEFAULT_DIFFICULTY = 5
# Full band path: enough for ~all covered weak skills at one CEFR level.
DEFAULT_PATH_STEPS = 30
MAX_PATH_STEPS = 40
# Back-compat alias (older adaptive-horizon naming).
DEFAULT_HORIZON = DEFAULT_PATH_STEPS


def _clamp_path_steps(value: int | None) -> int:
    n = DEFAULT_PATH_STEPS if value is None else int(value)
    return max(1, min(MAX_PATH_STEPS, n))


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


def select_skills_for_roadmap(
    skills: list[dict[str, Any]] | list[LearningSkillDB],
    mastery: dict[int, float],
    *,
    placement_score: int | None,
    prereq_from_by_to: dict[int, list[int]],
    max_steps: int = 10,
    theme_unit_by_skill_id: dict[int, dict[str, Any]] | None = None,
    prefer_unit_slug: str | None = None,
) -> list[dict[str, Any]]:
    """Build an ordered curriculum path of weak skills.

    The placement sub-level acts as a floor: easier skills are assumed already
    learned and are not re-taught. A skill joins the path once its prerequisites
    are satisfied by known skills (strong mastery or below the floor) **or** by
    skills already placed in earlier weeks — so a prerequisite chain unfolds into
    consecutive weeks instead of collapsing to a single unlockable skill.

    When theme-unit metadata is provided, the path finishes the current Theme Unit
    (by catalog position) before starting another, still respecting prereqs/ZPD.
    Without unit metadata, difficulty orders the path; mastery then id break ties.
    """
    floor = _clamp_placement_score(placement_score)
    max_steps = max(0, int(max_steps))
    unit_map = theme_unit_by_skill_id or {}

    by_id: dict[int, dict[str, Any]] = {}
    for raw in skills:
        skill = _skill_as_dict(raw)
        if skill.get("is_active", True):
            by_id[int(skill["id"])] = skill

    def difficulty_of(sid: int) -> int:
        return int(by_id[sid].get("difficulty_in_level") or DEFAULT_DIFFICULTY)

    def unit_slug_of(sid: int) -> str | None:
        meta = unit_map.get(sid)
        if not meta:
            return None
        slug = meta.get("slug")
        return str(slug) if slug else None

    def unit_sort_of(sid: int) -> int:
        meta = unit_map.get(sid) or {}
        return int(meta.get("sort_order") if meta.get("sort_order") is not None else 10**6)

    def unit_position_of(sid: int) -> int:
        meta = unit_map.get(sid) or {}
        return int(meta.get("position") if meta.get("position") is not None else 10**6)

    known: set[int] = {
        sid
        for sid in by_id
        if float(mastery.get(sid, DEFAULT_PRIOR)) >= MASTERY_STRONG
        or difficulty_of(sid) < floor
    }
    pool = {sid for sid in by_id if sid not in known}

    def prereqs_satisfied(sid: int) -> bool:
        return all(from_id in known for from_id in prereq_from_by_to.get(sid, []))

    def order_key(sid: int, *, anchor: str | None) -> tuple:
        diff = difficulty_of(sid)
        mast = float(mastery.get(sid, DEFAULT_PRIOR))
        if not unit_map:
            return (diff, mast, sid)
        slug = unit_slug_of(sid)
        if anchor is not None:
            leave = 0 if slug == anchor else 1
            if leave == 0:
                return (0, unit_position_of(sid), diff, mast, sid)
            return (1, unit_sort_of(sid), unit_position_of(sid), diff, mast, sid)
        return (unit_sort_of(sid), unit_position_of(sid), diff, mast, sid)

    def pool_has_unit(slug: str | None) -> bool:
        if not slug:
            return False
        return any(unit_slug_of(sid) == slug for sid in pool)

    anchor = prefer_unit_slug
    selected: list[dict[str, Any]] = []
    while len(selected) < max_steps:
        eligible = [sid for sid in pool if prereqs_satisfied(sid)]
        if not eligible:
            break
        if unit_map and anchor:
            same_unit = [sid for sid in eligible if unit_slug_of(sid) == anchor]
            pick_from = same_unit or eligible
        else:
            pick_from = eligible
        pick = min(pick_from, key=lambda sid: order_key(sid, anchor=anchor))
        selected.append(by_id[pick])
        known.add(pick)
        pool.discard(pick)
        if unit_map:
            if anchor is None or not pool_has_unit(anchor):
                anchor = unit_slug_of(pick)
    return selected


async def load_active_skills(db: AsyncSession, level: CEFRLevel) -> list[LearningSkillDB]:
    result = await db.execute(
        select(LearningSkillDB).where(
            LearningSkillDB.cefr_level == level,
            LearningSkillDB.is_active.is_(True),
        )
    )
    return list(result.scalars().all())


def filter_skills_with_coverage(
    skills: list[dict[str, Any]] | list[LearningSkillDB],
    covered_ids: set[int],
) -> list[Any]:
    """Keep only skills that have at least one non-excluded book source."""
    out: list[Any] = []
    for skill in skills:
        sid = int(skill["id"] if isinstance(skill, dict) else skill.id)
        if sid in covered_ids:
            out.append(skill)
    return out


async def load_covered_skill_ids(db: AsyncSession, level: CEFRLevel) -> set[int]:
    result = await db.execute(
        select(BookSkillSourceDB.skill_id)
        .join(LearningSkillDB, LearningSkillDB.id == BookSkillSourceDB.skill_id)
        .where(
            LearningSkillDB.cefr_level == level,
            LearningSkillDB.is_active.is_(True),
            BookSkillSourceDB.is_excluded.is_(False),
        )
    )
    return {int(x) for x in result.scalars().all()}


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


async def _first_active_scenario(
    db: AsyncSession,
    *,
    level: CEFRLevel | None = None,
    category: ScenarioCategoryEnum | None = None,
) -> ScenarioDB | None:
    stmt = select(ScenarioDB).where(ScenarioDB.is_active.is_(True))
    if level is not None:
        stmt = stmt.where(ScenarioDB.level == level)
    if category is not None:
        stmt = stmt.where(ScenarioDB.category == category)
    stmt = stmt.order_by(ScenarioDB.order_index, ScenarioDB.id).limit(1)
    return (await db.execute(stmt)).scalar_one_or_none()


async def pick_scenario(
    db: AsyncSession,
    goal: GoalEnum | None,
    level: CEFRLevel,
) -> ScenarioDB:
    category = GOAL_TO_CATEGORY.get(goal) if goal is not None else None
    scenario = (
        (await _first_active_scenario(db, level=level, category=category))
        if category is not None
        else None
    )
    scenario = (
        scenario
        or await _first_active_scenario(db, level=level)
        or await _first_active_scenario(db)
    )
    if scenario is None:
        raise ValueError("No scenarios yet — seed scenarios before assembling the roadmap.")
    return scenario


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


async def _delete_locked_tail(db: AsyncSession, user_id: int) -> None:
    locked = list(
        (
            await db.execute(
                select(UserProgressDB).where(
                    UserProgressDB.user_id == user_id,
                    UserProgressDB.status == ProgressStatusEnum.locked,
                )
            )
        )
        .scalars()
        .all()
    )
    step_ids = [int(progress.roadmap_step_id) for progress in locked]
    if locked:
        await db.execute(
            delete(UserProgressDB).where(
                UserProgressDB.user_id == user_id,
                UserProgressDB.status == ProgressStatusEnum.locked,
            )
        )

    for step_id in step_ids:
        remaining = (
            await db.execute(
                select(UserProgressDB.id)
                .where(UserProgressDB.roadmap_step_id == step_id)
                .limit(1)
            )
        ).scalar_one_or_none()
        if remaining is not None:
            continue
        await db.execute(
            delete(RoadmapStepSkillDB).where(
                RoadmapStepSkillDB.roadmap_step_id == step_id
            )
        )
        await db.execute(delete(RoadmapStepDB).where(RoadmapStepDB.id == step_id))


async def _next_week_number(db: AsyncSession, user_id: int) -> int:
    rows = list(
        (
            await db.execute(
                select(RoadmapStepDB.week_number)
                .join(
                    UserProgressDB,
                    UserProgressDB.roadmap_step_id == RoadmapStepDB.id,
                )
                .where(UserProgressDB.user_id == user_id)
            )
        )
        .scalars()
        .all()
    )
    return int(max(int(number) for number in rows)) + 1 if rows else 1


async def _require_profile(db: AsyncSession, user_id: int) -> UserProfileDB:
    profile = (
        await db.execute(select(UserProfileDB).where(UserProfileDB.user_id == user_id))
    ).scalar_one_or_none()
    if profile is None:
        raise ValueError("User has no profile — complete onboarding first.")
    return profile


def _resolve_target_level(
    profile: UserProfileDB, level: CEFRLevel | None
) -> CEFRLevel:
    target_level = level or profile.current_level
    if target_level is None:
        raise ValueError("Missing CEFR level to assemble the roadmap.")
    return target_level


async def _load_assigned_skill_ids(db: AsyncSession, user_id: int) -> set[int]:
    """Skill ids on completed or in_progress weeks for this user."""
    rows = list(
        (
            await db.execute(
                select(RoadmapStepSkillDB.skill_id)
                .join(UserProgressDB, UserProgressDB.roadmap_step_id == RoadmapStepSkillDB.roadmap_step_id)
                .where(
                    UserProgressDB.user_id == user_id,
                    UserProgressDB.status.in_(
                        [ProgressStatusEnum.completed, ProgressStatusEnum.in_progress]
                    ),
                    RoadmapStepSkillDB.role == "quiz",
                )
            )
        )
        .scalars()
        .all()
    )
    return {int(sid) for sid in rows}


async def plan_next_steps(
    db: AsyncSession,
    user_id: int,
    *,
    horizon: int = DEFAULT_PATH_STEPS,
    level: CEFRLevel | None = None,
) -> tuple[list[dict[str, Any]], dict[int, float], UserProfileDB, CEFRLevel]:
    profile = await _require_profile(db, user_id)
    target_level = _resolve_target_level(profile, level)
    horizon = _clamp_path_steps(horizon)

    skills = await load_active_skills(db, target_level)
    if not skills:
        raise ValueError(f"No active learning_skills for level {target_level}.")

    covered_ids = await load_covered_skill_ids(db, target_level)
    skills = filter_skills_with_coverage(skills, covered_ids)
    if not skills:
        raise ValueError(
            f"No covered learning_skills for level {target_level} "
            "(attach book sources via sync-skills first)."
        )

    assigned = await _load_assigned_skill_ids(db, user_id)
    candidates = [s for s in skills if int(s.id) not in assigned]
    if not candidates:
        return [], await load_mastery_map(db, user_id), profile, target_level

    mastery = await load_mastery_map(db, user_id)
    candidate_ids = {int(s.id) for s in candidates}
    prereq_from_by_to = await load_prereq_map(db, candidate_ids)
    unit_map = await load_theme_unit_map_by_skill_ids(db, candidate_ids | assigned)
    prefer_unit = await _load_prefer_theme_unit_slug(db, user_id) if assigned else None
    selected = select_skills_for_roadmap(
        candidates,
        mastery,
        placement_score=profile.placement_score,
        prereq_from_by_to=prereq_from_by_to,
        max_steps=horizon,
        theme_unit_by_skill_id=unit_map,
        prefer_unit_slug=prefer_unit,
    )
    return selected, mastery, profile, target_level


async def _select_roadmap_skills(
    db: AsyncSession,
    profile: UserProfileDB,
    target_level: CEFRLevel,
    max_steps: int,
) -> tuple[list[dict[str, Any]], dict[int, float]]:
    skills = await load_active_skills(db, target_level)
    if not skills:
        raise ValueError(f"No active learning_skills for level {target_level}.")

    covered_ids = await load_covered_skill_ids(db, target_level)
    skills = filter_skills_with_coverage(skills, covered_ids)
    if not skills:
        raise ValueError(
            f"No covered learning_skills for level {target_level} "
            "(attach book sources via sync-skills first)."
        )

    mastery = await load_mastery_map(db, profile.user_id)
    skill_ids = {int(s.id) for s in skills}
    prereq_from_by_to = await load_prereq_map(db, skill_ids)
    unit_map = await load_theme_unit_map_by_skill_ids(db, skill_ids)
    selected = select_skills_for_roadmap(
        skills,
        mastery,
        placement_score=profile.placement_score,
        prereq_from_by_to=prereq_from_by_to,
        max_steps=max_steps,
        theme_unit_by_skill_id=unit_map,
    )
    if not selected:
        raise ValueError("No weak skills left to assemble the roadmap at this level.")
    return selected, mastery


async def load_theme_unit_map_by_skill_ids(
    db: AsyncSession, skill_ids: set[int]
) -> dict[int, dict[str, Any]]:
    if not skill_ids:
        return {}
    rows = (
        await db.execute(
            select(ThemeUnitSkillDB, LearningThemeUnitDB)
            .join(
                LearningThemeUnitDB,
                LearningThemeUnitDB.id == ThemeUnitSkillDB.theme_unit_id,
            )
            .where(
                ThemeUnitSkillDB.skill_id.in_(skill_ids),
                LearningThemeUnitDB.is_active.is_(True),
            )
        )
    ).all()
    out: dict[int, dict[str, Any]] = {}
    for link, unit in rows:
        out[int(link.skill_id)] = {
            "slug": unit.slug,
            "title": unit.title,
            "can_do": unit.can_do,
            "position": int(link.position or 0),
            "sort_order": int(unit.sort_order or 0),
        }
    return out


async def _load_prefer_theme_unit_slug(
    db: AsyncSession, user_id: int
) -> str | None:
    """Theme unit of the learner's current (or latest completed) roadmap skill."""
    row = (
        await db.execute(
            select(ThemeUnitSkillDB.skill_id, LearningThemeUnitDB.slug)
            .join(
                LearningThemeUnitDB,
                LearningThemeUnitDB.id == ThemeUnitSkillDB.theme_unit_id,
            )
            .join(
                RoadmapStepSkillDB,
                RoadmapStepSkillDB.skill_id == ThemeUnitSkillDB.skill_id,
            )
            .join(
                UserProgressDB,
                UserProgressDB.roadmap_step_id == RoadmapStepSkillDB.roadmap_step_id,
            )
            .join(RoadmapStepDB, RoadmapStepDB.id == UserProgressDB.roadmap_step_id)
            .where(
                UserProgressDB.user_id == user_id,
                UserProgressDB.status.in_(
                    [ProgressStatusEnum.in_progress, ProgressStatusEnum.completed]
                ),
                RoadmapStepSkillDB.role == "quiz",
                LearningThemeUnitDB.is_active.is_(True),
            )
            .order_by(
                # Prefer the active week; otherwise the latest completed week.
                case(
                    (UserProgressDB.status == ProgressStatusEnum.in_progress, 0),
                    else_=1,
                ),
                RoadmapStepDB.week_number.desc(),
                RoadmapStepDB.id.desc(),
            )
            .limit(1)
        )
    ).first()
    if row is None:
        return None
    slug = row[1]
    return str(slug) if slug else None


def attach_theme_unit_fields(
    week: dict[str, Any],
    unit_by_skill_id: dict[int, dict[str, Any]],
) -> dict[str, Any]:
    """Add theme unit metadata onto a roadmap week dict (pure)."""
    out = dict(week)
    meta = unit_by_skill_id.get(int(week["skill_id"]))
    if not meta:
        out["theme_unit_slug"] = None
        out["theme_unit_title"] = None
        out["theme_unit_can_do"] = None
        out["theme_unit_position"] = None
        return out
    out["theme_unit_slug"] = meta.get("slug")
    out["theme_unit_title"] = meta.get("title")
    out["theme_unit_can_do"] = meta.get("can_do")
    out["theme_unit_position"] = meta.get("position")
    return out


def _assemble_week_dict(
    step: RoadmapStepDB,
    status: ProgressStatusEnum,
    skill: dict[str, Any],
    scenario: ScenarioDB,
    target_level: CEFRLevel,
    mastery: dict[int, float],
    *,
    unit_by_skill_id: dict[int, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    skill_id = int(skill["id"])
    week = {
        "week_number": int(step.week_number),
        "roadmap_step_id": int(step.id),
        "title": step.title,
        "skill_id": skill_id,
        "skill_slug": skill["slug"],
        "skill_title": skill.get("title"),
        "skill_type": skill.get("skill_type"),
        "difficulty_in_level": int(
            skill.get("difficulty_in_level") or DEFAULT_DIFFICULTY
        ),
        "scenario_id": int(scenario.id),
        "scenario_title": scenario.title,
        "status": status.value,
        "mastery": float(mastery.get(skill_id, DEFAULT_PRIOR)),
        "level": target_level.value
        if hasattr(target_level, "value")
        else str(target_level),
    }
    return attach_theme_unit_fields(week, unit_by_skill_id or {})


async def _persist_week(
    db: AsyncSession,
    user_id: int,
    index: int,
    skill: dict[str, Any],
    scenario: ScenarioDB,
    target_level: CEFRLevel,
    mastery: dict[int, float],
    *,
    is_current: bool = False,
    unit_by_skill_id: dict[int, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    step = RoadmapStepDB(
        level=target_level,
        week_number=index,
        title=f"Week {index}: {skill.get('title') or skill['slug']}",
        scenario_id=scenario.id,
        unlock_condition=None if is_current else f"complete_week_{index - 1}",
    )
    db.add(step)
    await db.flush()

    db.add(
        RoadmapStepSkillDB(
            roadmap_step_id=step.id, skill_id=int(skill["id"]), role="quiz"
        )
    )
    status = ProgressStatusEnum.in_progress if is_current else ProgressStatusEnum.locked
    db.add(UserProgressDB(user_id=user_id, roadmap_step_id=step.id, status=status))
    return _assemble_week_dict(
        step,
        status,
        skill,
        scenario,
        target_level,
        mastery,
        unit_by_skill_id=unit_by_skill_id,
    )


async def assemble_user_roadmap(
    db: AsyncSession,
    user_id: int,
    level: CEFRLevel | None = None,
    max_steps: int = DEFAULT_PATH_STEPS,
) -> list[dict[str, Any]]:
    horizon = _clamp_path_steps(max_steps)
    await clear_user_roadmap(db, user_id)
    selected, mastery, profile, target_level = await plan_next_steps(
        db, user_id, horizon=horizon, level=level
    )
    if not selected:
        raise ValueError("No weak skills left to assemble the roadmap at this level.")
    scenario = await pick_scenario(db, profile.goal, target_level)
    unit_map = await load_theme_unit_map_by_skill_ids(
        db, {int(s["id"]) for s in selected}
    )

    weeks = [
        await _persist_week(
            db,
            user_id,
            index,
            skill,
            scenario,
            target_level,
            mastery,
            is_current=(index == 1),
            unit_by_skill_id=unit_map,
        )
        for index, skill in enumerate(selected, start=1)
    ]
    await db.commit()
    return weeks


async def replan_locked_tail(
    db: AsyncSession,
    user_id: int,
    *,
    horizon: int = DEFAULT_PATH_STEPS,
    commit: bool = True,
) -> list[dict[str, Any]]:
    await _delete_locked_tail(db, user_id)
    has_in_progress = (
        await db.execute(
            select(UserProgressDB.id)
            .where(
                UserProgressDB.user_id == user_id,
                UserProgressDB.status == ProgressStatusEnum.in_progress,
            )
            .limit(1)
        )
    ).scalar_one_or_none() is not None
    capped = _clamp_path_steps(horizon)
    planning_horizon = max(1, capped - 1) if has_in_progress else capped
    selected, mastery, profile, target_level = await plan_next_steps(
        db, user_id, horizon=planning_horizon
    )
    if selected:
        scenario = await pick_scenario(db, profile.goal, target_level)
        unit_map = await load_theme_unit_map_by_skill_ids(
            db, {int(s["id"]) for s in selected}
        )
        start = await _next_week_number(db, user_id)
        for offset, skill in enumerate(selected):
            await _persist_week(
                db,
                user_id,
                start + offset,
                skill,
                scenario,
                target_level,
                mastery,
                is_current=(not has_in_progress and offset == 0),
                unit_by_skill_id=unit_map,
            )
    if commit:
        await db.commit()
    return await get_user_roadmap(db, user_id)


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
    unit_by_skill_id: dict[int, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    skill_dict = _skill_as_dict(skill) if skill is not None else _fallback_skill_dict(skill_id)
    status = progress.status
    level = step.level
    week = {
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
    return attach_theme_unit_fields(week, unit_by_skill_id or {})


async def get_user_roadmap(db: AsyncSession, user_id: int) -> list[dict[str, Any]]:
    """Return the learner's current path (same week dict shape as assemble)."""
    rows = await _load_progress_step_rows(db, user_id)
    if not rows:
        return []

    step_ids = [int(step.id) for _progress, step, _scenario in rows]
    skill_id_by_step = await _load_quiz_skill_id_by_step(db, step_ids)
    skills = await _load_skills_by_id(db, set(skill_id_by_step.values()))
    mastery = await load_mastery_map(db, user_id)
    unit_map = await load_theme_unit_map_by_skill_ids(
        db, set(skill_id_by_step.values())
    )

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
                unit_by_skill_id=unit_map,
            )
        )
    return weeks
