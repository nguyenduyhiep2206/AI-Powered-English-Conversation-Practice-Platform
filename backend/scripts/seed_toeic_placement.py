"""Seed a minimal published TOEIC R+W pool for local placement (placeholder content).

Usage (from backend/ with DATABASE_URL set):
  PYTHONPATH=. .venv/bin/python -m scripts.seed_toeic_placement

Requires at least one learning_skill (+ book/unit FKs on that skill's primary source
or falls back to first skill/book/unit rows in DB).
"""

from __future__ import annotations

import asyncio
import sys

from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.models.book import BookDB
from app.models.book_structure_preview import BookStructurePreviewDB
from app.models.enums import (
    QuizQuestionStatusEnum,
    QuizQuestionTypeEnum,
    ToeicPartEnum,
)
from app.models.learning_skill import LearningSkillDB
from app.models.quiz_passage import QuizPassageDB
from app.models.quiz_question import QuizQuestionDB
from app.services.placement.quotas import READING_QUOTA, WRITING_QUOTA


async def _resolve_fks(db):
    skill = (await db.execute(select(LearningSkillDB).limit(1))).scalar_one_or_none()
    book = (await db.execute(select(BookDB).limit(1))).scalar_one_or_none()
    unit = (
        await db.execute(select(BookStructurePreviewDB).limit(1))
    ).scalar_one_or_none()
    if not skill or not book or not unit:
        raise SystemExit(
            "Need at least one learning_skill, book, and book_structure_preview row."
        )
    return int(skill.id), int(book.id), int(unit.id)


def _mcq_options(i: int) -> list[str]:
    return [f"opt{i}a", f"opt{i}b", f"opt{i}c", f"opt{i}d"]


async def seed() -> None:
    async with AsyncSessionLocal() as db:
        skill_id, book_id, unit_id = await _resolve_fks(db)
        existing = (
            await db.execute(
                select(QuizQuestionDB.id).where(
                    QuizQuestionDB.toeic_part.is_not(None),
                    QuizQuestionDB.status == QuizQuestionStatusEnum.published,
                ).limit(1)
            )
        ).scalar_one_or_none()
        if existing is not None:
            print("Published TOEIC items already exist; skip seed.")
            return

        for part, need in READING_QUOTA.items():
            if part in {"r6", "r7"}:
                per_group = 4 if part == "r6" else 3
                made = 0
                group = 0
                while made < need:
                    group += 1
                    passage = QuizPassageDB(
                        book_id=book_id,
                        unit_id=unit_id,
                        toeic_part=ToeicPartEnum(part),
                        body=f"Placeholder {part} passage {group}. "
                        f"The team submitted the report before Friday.",
                        status=QuizQuestionStatusEnum.published,
                    )
                    db.add(passage)
                    await db.flush()
                    take = min(per_group, need - made)
                    for j in range(take):
                        idx = made + j
                        db.add(
                            QuizQuestionDB(
                                skill_id=skill_id,
                                book_id=book_id,
                                unit_id=unit_id,
                                question_type=QuizQuestionTypeEnum.mcq,
                                toeic_part=ToeicPartEnum(part),
                                passage_id=int(passage.id),
                                passage=passage.body,
                                stem=f"[{part.upper()}] Question {idx + 1}: choose the best answer.",
                                options=_mcq_options(idx),
                                answer=_mcq_options(idx)[0],
                                status=QuizQuestionStatusEnum.published,
                                difficulty="medium",
                            )
                        )
                    made += take
            else:
                for i in range(need):
                    db.add(
                        QuizQuestionDB(
                            skill_id=skill_id,
                            book_id=book_id,
                            unit_id=unit_id,
                            question_type=QuizQuestionTypeEnum.mcq,
                            toeic_part=ToeicPartEnum.r5,
                            stem=f"[R5] Incomplete sentence {i + 1}: They ____ the meeting.",
                            options=_mcq_options(i),
                            answer=_mcq_options(i)[0],
                            status=QuizQuestionStatusEnum.published,
                            difficulty="medium",
                        )
                    )

        for i in range(WRITING_QUOTA["w1"]):
            db.add(
                QuizQuestionDB(
                    skill_id=skill_id,
                    book_id=book_id,
                    unit_id=unit_id,
                    question_type=QuizQuestionTypeEnum.writing,
                    toeic_part=ToeicPartEnum.w1,
                    stem="Write one sentence about the picture using the two words.",
                    prompt_words=["office", "meeting"],
                    media_url="https://placehold.co/600x400/png",
                    answer="",
                    status=QuizQuestionStatusEnum.published,
                    difficulty="medium",
                )
            )
        for i in range(WRITING_QUOTA["w2"]):
            passage = QuizPassageDB(
                book_id=book_id,
                unit_id=unit_id,
                toeic_part=ToeicPartEnum.w2,
                body=(
                    f"From: Client {i+1}\nTo: You\nSubject: Meeting\n\n"
                    "Could we meet next week to discuss the proposal?"
                ),
                status=QuizQuestionStatusEnum.published,
            )
            db.add(passage)
            await db.flush()
            db.add(
                QuizQuestionDB(
                    skill_id=skill_id,
                    book_id=book_id,
                    unit_id=unit_id,
                    question_type=QuizQuestionTypeEnum.writing,
                    toeic_part=ToeicPartEnum.w2,
                    passage_id=int(passage.id),
                    passage=passage.body,
                    stem="Respond to the email. Ask TWO questions and provide ONE meeting time.",
                    task_brief={"must_ask": 2, "must_provide": 1},
                    answer="",
                    status=QuizQuestionStatusEnum.published,
                    difficulty="medium",
                )
            )
        db.add(
            QuizQuestionDB(
                skill_id=skill_id,
                book_id=book_id,
                unit_id=unit_id,
                question_type=QuizQuestionTypeEnum.writing,
                toeic_part=ToeicPartEnum.w3,
                stem=(
                    "Some people prefer working from home. What are the advantages "
                    "and disadvantages? Support your answer with reasons and examples."
                ),
                task_brief={"min_words": 300},
                answer="",
                status=QuizQuestionStatusEnum.published,
                difficulty="medium",
            )
        )
        await db.commit()
        print("Seeded published TOEIC placement pool.")


if __name__ == "__main__":
    asyncio.run(seed())
    sys.exit(0)
