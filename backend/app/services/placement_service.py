"""Placement test helpers: sample published quiz bank and map score to CEFR.

Roadmap assemble is intentionally out of scope here.
"""

from __future__ import annotations

import random
from collections import defaultdict
from dataclasses import dataclass
from typing import Any, Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import CEFRLevel, QuizQuestionStatusEnum
from app.models.learning_skill import LearningSkillDB
from app.models.profile import UserProfileDB
from app.models.quiz_question import QuizQuestionDB
from app.services.mastery_service import apply_answer, grade_mcq

PLACEMENT_SIZE = 10
PER_LEVEL = 2
CEFR_ORDER: tuple[CEFRLevel, ...] = (
    CEFRLevel.A1,
    CEFRLevel.A2,
    CEFRLevel.B1,
    CEFRLevel.B2,
    CEFRLevel.C1,
)
INSUFFICIENT_BANK_MSG = (
    "Chưa đủ câu hỏi published cho placement (cần 10 câu trải A1–C1)."
)


@dataclass(frozen=True)
class PlacementCandidate:
    id: int
    skill_id: int
    cefr_level: CEFRLevel
    question_type: str
    stem: str
    options: list[str] | None
    difficulty: str
    answer: str
    passage: str | None = None


def score_to_level(score: int) -> CEFRLevel:
    if score <= 3:
        return CEFRLevel.A1
    if score <= 5:
        return CEFRLevel.A2
    if score <= 7:
        return CEFRLevel.B1
    if score <= 9:
        return CEFRLevel.B2
    return CEFRLevel.C1


def select_from_candidates(
    candidates: Sequence[PlacementCandidate],
    *,
    rng_seed: int | None = None,
) -> list[PlacementCandidate]:
    """Pick 2 questions per CEFR level without preferring any question_type.

    Within each level, prefer unused skills. Across the whole set, prefer
    question types that are currently under-represented so types spread evenly.
    """
    rng = random.Random(rng_seed)
    by_level: dict[CEFRLevel, list[PlacementCandidate]] = defaultdict(list)
    for c in candidates:
        by_level[c.cefr_level].append(c)

    picked: list[PlacementCandidate] = []
    for level in CEFR_ORDER:
        pool = list(by_level.get(level, []))
        if len(pool) < PER_LEVEL:
            raise ValueError(INSUFFICIENT_BANK_MSG)

        rng.shuffle(pool)
        chosen: list[PlacementCandidate] = []
        used_skills: set[int] = set()

        def type_count_so_far(question_type: str) -> int:
            return sum(
                1
                for item in (*picked, *chosen)
                if item.question_type == question_type
            )

        def take(*, require_unique_skill: bool) -> None:
            remaining = [c for c in pool if c not in chosen]
            while len(chosen) < PER_LEVEL and remaining:
                scored = sorted(
                    remaining,
                    key=lambda c: (
                        1
                        if require_unique_skill and c.skill_id in used_skills
                        else 0,
                        type_count_so_far(c.question_type),
                        rng.random(),
                    ),
                )
                candidate = None
                for c in scored:
                    if require_unique_skill and c.skill_id in used_skills:
                        continue
                    candidate = c
                    break
                if candidate is None:
                    break
                chosen.append(candidate)
                used_skills.add(candidate.skill_id)
                remaining = [c for c in remaining if c.id != candidate.id]

        take(require_unique_skill=True)
        if len(chosen) < PER_LEVEL:
            take(require_unique_skill=False)

        if len(chosen) < PER_LEVEL:
            raise ValueError(INSUFFICIENT_BANK_MSG)
        picked.extend(chosen[:PER_LEVEL])

    if len(picked) != PLACEMENT_SIZE:
        raise ValueError(INSUFFICIENT_BANK_MSG)

    rng.shuffle(picked)
    return picked


def grade_placement_answer(expected: str, given: str) -> bool:
    return grade_mcq(expected, given)


def placement_public_dict(c: PlacementCandidate) -> dict[str, Any]:
    """Serialize a candidate for the learner API without leaking the answer."""
    return {
        "id": c.id,
        "skill_id": c.skill_id,
        "cefr_level": c.cefr_level.value if hasattr(c.cefr_level, "value") else str(c.cefr_level),
        "question_type": c.question_type,
        "stem": c.stem,
        "passage": c.passage,
        "options": c.options,
        "difficulty": c.difficulty,
    }


async def load_published_candidates(db: AsyncSession) -> list[PlacementCandidate]:
    q = (
        select(QuizQuestionDB, LearningSkillDB)
        .join(LearningSkillDB, LearningSkillDB.id == QuizQuestionDB.skill_id)
        .where(
            QuizQuestionDB.status == QuizQuestionStatusEnum.published,
            LearningSkillDB.is_active.is_(True),
        )
    )
    rows = (await db.execute(q)).all()
    out: list[PlacementCandidate] = []
    for question, skill in rows:
        qtype = question.question_type
        qtype_s = qtype.value if hasattr(qtype, "value") else str(qtype)
        out.append(
            PlacementCandidate(
                id=int(question.id),
                skill_id=int(question.skill_id),
                cefr_level=skill.cefr_level,
                question_type=qtype_s,
                stem=question.stem,
                options=list(question.options) if question.options else None,
                difficulty=question.difficulty or "medium",
                answer=question.answer,
                passage=question.passage,
            )
        )
    return out


async def get_placement_questions_for_user(
    db: AsyncSession,
    user_id: int,
) -> list[PlacementCandidate]:
    profile = (
        await db.execute(select(UserProfileDB).where(UserProfileDB.user_id == user_id))
    ).scalar_one_or_none()
    if profile is None or not profile.survey_done:
        raise PermissionError("Hoàn thành survey trước khi làm placement")
    if profile.placement_score is not None:
        raise RuntimeError("Đã hoàn thành placement")

    candidates = await load_published_candidates(db)
    return select_from_candidates(candidates)


async def submit_placement(
    db: AsyncSession,
    user_id: int,
    answers: list[dict[str, Any]],
) -> dict[str, Any]:
    """Grade answers, set CEFR level + mastery. Does not assemble a roadmap."""
    profile = (
        await db.execute(select(UserProfileDB).where(UserProfileDB.user_id == user_id))
    ).scalar_one_or_none()
    if profile is None or not profile.survey_done:
        raise PermissionError("Hoàn thành survey trước khi làm placement")
    if profile.placement_score is not None:
        raise RuntimeError("Đã hoàn thành placement")

    if len(answers) != PLACEMENT_SIZE:
        raise ValueError(f"Cần đúng {PLACEMENT_SIZE} câu trả lời")

    ids = [int(a["question_id"]) for a in answers]
    if len(set(ids)) != PLACEMENT_SIZE:
        raise ValueError("question_id trùng hoặc thiếu")

    q = select(QuizQuestionDB).where(
        QuizQuestionDB.id.in_(ids),
        QuizQuestionDB.status == QuizQuestionStatusEnum.published,
    )
    rows = list((await db.execute(q)).scalars().all())
    by_id = {int(r.id): r for r in rows}
    if len(by_id) != PLACEMENT_SIZE:
        raise ValueError("Một số câu không tồn tại hoặc chưa published")

    correct_count = 0
    graded: list[tuple[QuizQuestionDB, bool]] = []
    answer_map = {int(a["question_id"]): str(a["answer"]) for a in answers}
    for qid in ids:
        row = by_id[qid]
        ok = grade_placement_answer(row.answer, answer_map[qid])
        if ok:
            correct_count += 1
        graded.append((row, ok))

    level = score_to_level(correct_count)
    profile.placement_score = correct_count
    profile.current_level = level
    await db.commit()

    for row, ok in graded:
        await apply_answer(db, user_id, int(row.skill_id), ok)

    return {
        "placement_score": correct_count,
        "current_level": level.value,
        "correct_count": correct_count,
        "total": PLACEMENT_SIZE,
        "onboarding_complete": True,
    }
