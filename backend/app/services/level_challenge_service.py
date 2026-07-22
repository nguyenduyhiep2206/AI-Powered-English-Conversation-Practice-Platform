"""CEFR +1 level challenge when the current level feels too easy."""

from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import CEFRLevel, QuizQuestionStatusEnum
from app.models.learning_skill import LearningSkillDB
from app.models.profile import UserProfileDB
from app.models.quiz_question import QuizQuestionDB
from app.services.mastery_service import apply_answer
from app.services.placement_service import (
    CEFR_ORDER,
    PlacementCandidate,
    grade_placement_answer,
    placement_public_dict,
)
from app.services.roadmap_assembler_service import clear_user_roadmap

CHALLENGE_SIZE = 6
CHALLENGE_PASS = 4
INSUFFICIENT_CHALLENGE_BANK_MSG = (
    f"Chưa đủ câu hỏi published cho level challenge (cần ≥{CHALLENGE_SIZE} câu ở level đích)."
)


@dataclass(frozen=True)
class ChallengeGradeResult:
    correct_count: int
    graded: tuple[tuple[QuizQuestionDB, bool], ...]

    @property
    def passed(self) -> bool:
        return self.correct_count >= CHALLENGE_PASS


def next_cefr_level(current: CEFRLevel) -> CEFRLevel | None:
    """Return the next CEFR band, or None at C1."""
    try:
        idx = CEFR_ORDER.index(current)
    except ValueError:
        return None
    if idx + 1 >= len(CEFR_ORDER):
        return None
    return CEFR_ORDER[idx + 1]


def challenge_score_to_placement(correct: int, total: int = CHALLENGE_SIZE) -> int:
    """Map challenge score onto placement_score 1..10 for the new level."""
    if total <= 0:
        return 1
    return max(1, min(10, round(int(correct) / int(total) * 10)))


def sample_challenge_candidates(
    candidates: list[PlacementCandidate],
    *,
    size: int = CHALLENGE_SIZE,
    rng_seed: int | None = None,
) -> list[PlacementCandidate]:
    if len(candidates) < size:
        raise ValueError(INSUFFICIENT_CHALLENGE_BANK_MSG)

    rng = random.Random(rng_seed)
    pool = list(candidates)
    rng.shuffle(pool)

    chosen: list[PlacementCandidate] = []
    used_skills: set[int] = set()
    for candidate in pool:
        if candidate.skill_id in used_skills:
            continue
        chosen.append(candidate)
        used_skills.add(candidate.skill_id)
        if len(chosen) >= size:
            break

    if len(chosen) < size:
        for candidate in pool:
            if candidate in chosen:
                continue
            chosen.append(candidate)
            if len(chosen) >= size:
                break

    if len(chosen) < size:
        raise ValueError(INSUFFICIENT_CHALLENGE_BANK_MSG)
    rng.shuffle(chosen)
    return chosen[:size]


async def _require_challenge_profile(
    db: AsyncSession, user_id: int
) -> UserProfileDB:
    profile = (
        await db.execute(select(UserProfileDB).where(UserProfileDB.user_id == user_id))
    ).scalar_one_or_none()
    if profile is None or profile.placement_score is None:
        raise PermissionError("Hoàn thành placement trước khi làm level challenge")
    return profile


def _resolve_target_level(
    profile: UserProfileDB, target_level: CEFRLevel | None
) -> CEFRLevel:
    expected = next_cefr_level(profile.current_level)
    if expected is None:
        raise ValueError("Đã ở level cao nhất — không thể challenge lên nữa")
    resolved = target_level or expected
    if resolved != expected:
        raise ValueError(
            f"Chỉ được challenge lên đúng 1 bậc: {expected.value} "
            f"(hiện tại {profile.current_level.value})"
        )
    return resolved


def _row_to_candidate(question: QuizQuestionDB, skill: LearningSkillDB) -> PlacementCandidate:
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


async def _load_published_for_level(
    db: AsyncSession, level: CEFRLevel
) -> list[PlacementCandidate]:
    rows = (
        await db.execute(
            select(QuizQuestionDB, LearningSkillDB)
            .join(LearningSkillDB, LearningSkillDB.id == QuizQuestionDB.skill_id)
            .where(
                QuizQuestionDB.status == QuizQuestionStatusEnum.published,
                LearningSkillDB.is_active.is_(True),
                LearningSkillDB.cefr_level == level,
            )
        )
    ).all()
    return [_row_to_candidate(question, skill) for question, skill in rows]


async def get_level_challenge_questions(
    db: AsyncSession,
    user_id: int,
    target_level: CEFRLevel | None = None,
) -> dict[str, Any]:
    profile = await _require_challenge_profile(db, user_id)
    resolved = _resolve_target_level(profile, target_level)
    pool = await _load_published_for_level(db, resolved)
    picked = sample_challenge_candidates(pool)
    return {
        "target_level": resolved.value,
        "question_count": len(picked),
        "questions": [placement_public_dict(c) for c in picked],
    }


def _parse_challenge_answer_ids(answers: list[dict[str, Any]]) -> list[int]:
    if len(answers) != CHALLENGE_SIZE:
        raise ValueError(f"Cần đúng {CHALLENGE_SIZE} câu trả lời")
    ids = [int(a["question_id"]) for a in answers]
    if len(set(ids)) != CHALLENGE_SIZE:
        raise ValueError("question_id trùng hoặc thiếu")
    return ids


async def _fetch_challenge_questions(
    db: AsyncSession, level: CEFRLevel, ids: list[int]
) -> dict[int, QuizQuestionDB]:
    rows = (
        await db.execute(
            select(QuizQuestionDB, LearningSkillDB)
            .join(LearningSkillDB, LearningSkillDB.id == QuizQuestionDB.skill_id)
            .where(
                QuizQuestionDB.id.in_(ids),
                QuizQuestionDB.status == QuizQuestionStatusEnum.published,
                LearningSkillDB.cefr_level == level,
            )
        )
    ).all()
    by_id = {int(q.id): q for q, _skill in rows}
    if len(by_id) != CHALLENGE_SIZE:
        raise ValueError("Một số câu không tồn tại, chưa published, hoặc sai level đích")
    return by_id


def _grade_challenge(
    ids: list[int],
    by_id: dict[int, QuizQuestionDB],
    answers: list[dict[str, Any]],
) -> ChallengeGradeResult:
    answer_map = {int(a["question_id"]): str(a["answer"]) for a in answers}
    graded: list[tuple[QuizQuestionDB, bool]] = []
    correct_count = 0
    for qid in ids:
        question = by_id[qid]
        ok = grade_placement_answer(question.answer, answer_map[qid])
        if ok:
            correct_count += 1
        graded.append((question, ok))
    return ChallengeGradeResult(correct_count=correct_count, graded=tuple(graded))


async def _apply_challenge_pass(
    db: AsyncSession,
    profile: UserProfileDB,
    user_id: int,
    target_level: CEFRLevel,
    correct_count: int,
) -> None:
    profile.current_level = target_level
    profile.placement_score = challenge_score_to_placement(correct_count)
    await clear_user_roadmap(db, user_id)


async def _seed_challenge_mastery(
    db: AsyncSession,
    user_id: int,
    graded: tuple[tuple[QuizQuestionDB, bool], ...],
) -> None:
    for question, ok in graded:
        await apply_answer(db, user_id, int(question.skill_id), ok)


async def submit_level_challenge(
    db: AsyncSession,
    user_id: int,
    target_level: CEFRLevel,
    answers: list[dict[str, Any]],
) -> dict[str, Any]:
    profile = await _require_challenge_profile(db, user_id)
    resolved = _resolve_target_level(profile, target_level)
    ids = _parse_challenge_answer_ids(answers)
    by_id = await _fetch_challenge_questions(db, resolved, ids)
    result = _grade_challenge(ids, by_id, answers)

    if result.passed:
        await _apply_challenge_pass(
            db, profile, user_id, resolved, result.correct_count
        )

    await db.commit()
    await _seed_challenge_mastery(db, user_id, result.graded)

    return {
        "passed": result.passed,
        "correct_count": result.correct_count,
        "total": CHALLENGE_SIZE,
        "current_level": profile.current_level.value,
        "placement_score": profile.placement_score,
        "target_level": resolved.value,
    }
