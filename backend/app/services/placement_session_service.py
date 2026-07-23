"""Adaptive placement sessions: start / resume / answer / retake."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import PlacementAttemptStatusEnum
from app.models.learning_skill import LearningSkillDB
from app.models.placement_attempt import PlacementAttemptAnswerDB, PlacementAttemptDB
from app.models.profile import UserProfileDB
from app.models.quiz_question import QuizQuestionDB
from app.services.mastery_service import apply_answer
from app.services.placement_adaptive_engine import (
    MAX_QUESTIONS,
    MIN_QUESTIONS,
    cefr_index,
    map_ability_to_profile,
    pick_next_candidate,
    should_stop,
    update_ability,
)
from app.services.placement_service import (
    PlacementCandidate,
    grade_placement_answer,
    load_published_candidates,
    placement_public_dict,
    row_to_candidate,
)

RETAKE_COOLDOWN_DAYS = 7
INSUFFICIENT_ADAPTIVE_BANK_MSG = (
    "Không còn câu hỏi published phù hợp cho placement adaptive."
)


def progress_dict(asked: int) -> dict[str, int]:
    return {
        "asked": int(asked),
        "min_questions": MIN_QUESTIONS,
        "max_questions": MAX_QUESTIONS,
    }


def retake_allowed(
    last_completed_at: datetime | None,
    now: datetime | None = None,
) -> bool:
    if last_completed_at is None:
        return True
    current = now or datetime.now(timezone.utc)
    completed = last_completed_at
    if completed.tzinfo is None:
        completed = completed.replace(tzinfo=timezone.utc)
    return current - completed >= timedelta(days=RETAKE_COOLDOWN_DAYS)


def _retry_after_at(last_completed_at: datetime) -> datetime:
    completed = last_completed_at
    if completed.tzinfo is None:
        completed = completed.replace(tzinfo=timezone.utc)
    return completed + timedelta(days=RETAKE_COOLDOWN_DAYS)


async def _get_profile(db: AsyncSession, user_id: int) -> UserProfileDB | None:
    return (
        await db.execute(select(UserProfileDB).where(UserProfileDB.user_id == user_id))
    ).scalar_one_or_none()


async def _require_survey_done(db: AsyncSession, user_id: int) -> UserProfileDB:
    profile = await _get_profile(db, user_id)
    if profile is None or not profile.survey_done:
        raise PermissionError("Hoàn thành survey trước khi làm placement")
    return profile


async def _get_in_progress(db: AsyncSession, user_id: int) -> PlacementAttemptDB | None:
    return (
        await db.execute(
            select(PlacementAttemptDB).where(
                PlacementAttemptDB.user_id == user_id,
                PlacementAttemptDB.status == PlacementAttemptStatusEnum.in_progress,
            )
        )
    ).scalar_one_or_none()


async def _last_completed_at(db: AsyncSession, user_id: int) -> datetime | None:
    row = (
        await db.execute(
            select(PlacementAttemptDB.completed_at)
            .where(
                PlacementAttemptDB.user_id == user_id,
                PlacementAttemptDB.status == PlacementAttemptStatusEnum.completed,
            )
            .order_by(PlacementAttemptDB.completed_at.desc())
            .limit(1)
        )
    ).scalar_one_or_none()
    return row


async def get_retake_status(db: AsyncSession, user_id: int) -> dict[str, Any]:
    await _require_survey_done(db, user_id)
    in_progress = await _get_in_progress(db, user_id)
    last_done = await _last_completed_at(db, user_id)
    now = datetime.now(timezone.utc)
    allowed = in_progress is None and retake_allowed(last_done, now)
    # First-time users (no completed attempt, no placement_score) can always start
    profile = await _get_profile(db, user_id)
    if profile is not None and profile.placement_score is None and in_progress is None:
        allowed = True
    retry_after = None
    if not allowed and in_progress is None and last_done is not None:
        retry_after = _retry_after_at(last_done)
    return {
        "allowed": allowed,
        "has_in_progress": in_progress is not None,
        "retry_after_at": retry_after,
    }


async def _skill_types_map(db: AsyncSession, skill_ids: set[int]) -> dict[int, str]:
    if not skill_ids:
        return {}
    rows = (
        await db.execute(select(LearningSkillDB).where(LearningSkillDB.id.in_(skill_ids)))
    ).scalars().all()
    out: dict[int, str] = {}
    for row in rows:
        st = row.skill_type
        out[int(row.id)] = st.value if hasattr(st, "value") else str(st)
    return out


async def _used_skill_ids(db: AsyncSession, attempt_id: int) -> set[int]:
    rows = (
        await db.execute(
            select(PlacementAttemptAnswerDB.skill_id).where(
                PlacementAttemptAnswerDB.attempt_id == attempt_id
            )
        )
    ).scalars().all()
    return {int(s) for s in rows}


def _seen_ids(attempt: PlacementAttemptDB) -> set[int]:
    raw = attempt.seen_question_ids or []
    return {int(x) for x in raw}


async def _candidate_by_id(
    candidates: list[PlacementCandidate], question_id: int
) -> PlacementCandidate | None:
    for c in candidates:
        if int(c.id) == int(question_id):
            return c
    return None


async def _serve_next_question(
    db: AsyncSession,
    attempt: PlacementAttemptDB,
    weak_point: Any,
) -> PlacementCandidate:
    candidates = await load_published_candidates(db)
    skill_types = await _skill_types_map(db, {int(c.skill_id) for c in candidates})
    used = await _used_skill_ids(db, int(attempt.id)) if attempt.id else set()
    try:
        picked = pick_next_candidate(
            candidates,
            ability_index=float(attempt.ability_index),
            seen_ids=_seen_ids(attempt),
            used_skill_ids=used,
            weak_point=weak_point,
            skill_types_by_skill_id=skill_types,
        )
    except ValueError as exc:
        raise ValueError(INSUFFICIENT_ADAPTIVE_BANK_MSG) from exc

    seen = list(_seen_ids(attempt))
    if int(picked.id) not in seen:
        seen.append(int(picked.id))
    attempt.seen_question_ids = seen
    attempt.current_question_id = int(picked.id)
    return picked


async def _load_question_candidate(
    db: AsyncSession, question_id: int
) -> PlacementCandidate:
    row = (
        await db.execute(
            select(QuizQuestionDB, LearningSkillDB)
            .join(LearningSkillDB, LearningSkillDB.id == QuizQuestionDB.skill_id)
            .where(QuizQuestionDB.id == question_id)
        )
    ).one_or_none()
    if row is None:
        raise ValueError("Câu hỏi không tồn tại")
    question, skill = row
    return row_to_candidate(question, skill)


def _mid_payload(attempt: PlacementAttemptDB, question: PlacementCandidate) -> dict[str, Any]:
    return {
        "done": False,
        "attempt_id": int(attempt.id),
        "question": placement_public_dict(question),
        "progress": progress_dict(int(attempt.questions_asked)),
    }


def _done_payload(attempt: PlacementAttemptDB, profile: UserProfileDB) -> dict[str, Any]:
    level = profile.current_level
    return {
        "done": True,
        "attempt_id": int(attempt.id),
        "placement_score": int(profile.placement_score or 0),
        "current_level": level.value if hasattr(level, "value") else str(level),
        "questions_asked": int(attempt.questions_asked),
        "onboarding_complete": True,
    }


async def _session_payload(
    db: AsyncSession, attempt: PlacementAttemptDB, *, done: bool = False
) -> dict[str, Any]:
    if done:
        profile = await _get_profile(db, int(attempt.user_id))
        if profile is None:
            raise RuntimeError("Profile missing")
        return _done_payload(attempt, profile)

    qid = attempt.current_question_id
    if qid is None:
        raise RuntimeError("Attempt thiếu current_question_id")
    question = await _load_question_candidate(db, int(qid))
    return _mid_payload(attempt, question)


async def _create_attempt(db: AsyncSession, profile: UserProfileDB) -> PlacementAttemptDB:
    wp = profile.weak_point
    wp_value = wp.value if wp is not None and hasattr(wp, "value") else (str(wp) if wp else None)
    attempt = PlacementAttemptDB(
        user_id=int(profile.user_id),
        status=PlacementAttemptStatusEnum.in_progress,
        ability_index=1.0,
        confidence=0.0,
        questions_asked=0,
        seen_question_ids=[],
        current_question_id=None,
        weak_point_bias=wp_value,
    )
    db.add(attempt)
    await db.flush()
    return attempt


async def _abandon_in_progress(db: AsyncSession, user_id: int) -> None:
    current = await _get_in_progress(db, user_id)
    if current is None:
        return
    current.status = PlacementAttemptStatusEnum.abandoned
    current.current_question_id = None


async def get_current_session(db: AsyncSession, user_id: int) -> dict[str, Any] | None:
    await _require_survey_done(db, user_id)
    attempt = await _get_in_progress(db, user_id)
    if attempt is None:
        return None
    return await _session_payload(db, attempt, done=False)


async def start_or_resume_session(db: AsyncSession, user_id: int) -> dict[str, Any]:
    profile = await _require_survey_done(db, user_id)
    current = await _get_in_progress(db, user_id)
    if current is not None:
        return await _session_payload(db, current, done=False)

    if profile.placement_score is not None:
        status = await get_retake_status(db, user_id)
        if not status["allowed"]:
            raise RuntimeError("Chưa đến lúc làm lại placement")
        await _abandon_in_progress(db, user_id)

    attempt = await _create_attempt(db, profile)
    question = await _serve_next_question(db, attempt, profile.weak_point)
    await db.commit()
    await db.refresh(attempt)
    return _mid_payload(attempt, question)


async def _require_in_progress_owned(
    db: AsyncSession, user_id: int, attempt_id: int
) -> PlacementAttemptDB:
    attempt = (
        await db.execute(
            select(PlacementAttemptDB).where(PlacementAttemptDB.id == attempt_id)
        )
    ).scalar_one_or_none()
    if attempt is None:
        raise ValueError("Attempt không tồn tại")
    if int(attempt.user_id) != int(user_id):
        raise PermissionError("Attempt không thuộc user")
    if attempt.status != PlacementAttemptStatusEnum.in_progress:
        raise RuntimeError("Attempt không còn in_progress")
    return attempt


async def _complete_attempt(
    db: AsyncSession,
    profile: UserProfileDB,
    attempt: PlacementAttemptDB,
) -> None:
    level, sub = map_ability_to_profile(float(attempt.ability_index))
    attempt.status = PlacementAttemptStatusEnum.completed
    attempt.completed_at = datetime.now(timezone.utc)
    attempt.current_question_id = None
    attempt.result_level = level
    attempt.result_sublevel = sub
    profile.current_level = level
    profile.placement_score = sub

    answers = (
        await db.execute(
            select(PlacementAttemptAnswerDB).where(
                PlacementAttemptAnswerDB.attempt_id == int(attempt.id)
            )
        )
    ).scalars().all()
    await db.commit()
    for ans in answers:
        await apply_answer(db, int(profile.user_id), int(ans.skill_id), bool(ans.is_correct))


async def submit_session_answer(
    db: AsyncSession,
    user_id: int,
    attempt_id: int,
    question_id: int,
    answer: str,
) -> dict[str, Any]:
    profile = await _require_survey_done(db, user_id)
    attempt = await _require_in_progress_owned(db, user_id, attempt_id)
    if attempt.current_question_id is None or int(attempt.current_question_id) != int(
        question_id
    ):
        raise ValueError("question_id không khớp câu hiện tại")

    question = await _load_question_candidate(db, int(question_id))
    ok = grade_placement_answer(question.answer, answer)
    item_level = float(cefr_index(question.cefr_level))
    ability, confidence = update_ability(
        float(attempt.ability_index),
        float(attempt.confidence),
        item_level=item_level,
        correct=ok,
    )
    attempt.ability_index = ability
    attempt.confidence = confidence
    attempt.questions_asked = int(attempt.questions_asked) + 1

    db.add(
        PlacementAttemptAnswerDB(
            attempt_id=int(attempt.id),
            question_id=int(question.id),
            skill_id=int(question.skill_id),
            cefr_level=question.cefr_level,
            given_answer=str(answer),
            is_correct=ok,
            ability_after=ability,
            confidence_after=confidence,
        )
    )

    if should_stop(int(attempt.questions_asked), float(attempt.confidence)):
        await _complete_attempt(db, profile, attempt)
        await db.refresh(profile)
        await db.refresh(attempt)
        return _done_payload(attempt, profile)

    next_q = await _serve_next_question(db, attempt, profile.weak_point)
    await db.commit()
    await db.refresh(attempt)
    return _mid_payload(attempt, next_q)
