"""One-off: ensure skill 229 has form in published lesson + skill_drill published quizzes.

Run inside API container:
  python -m scripts.seed_skill_drill_smoke --skill-id 229
"""

from __future__ import annotations

import argparse
import asyncio
import uuid

from sqlalchemy import select, update

from app.core.database import AsyncSessionLocal
from app.models.book_skill_source import BookSkillSourceDB
from app.models.enums import QuizQuestionStatusEnum, QuizQuestionTypeEnum
from app.models.quiz_question import QuizQuestionDB
from app.models.skill_lesson import SkillLessonDB


CONTENT = {
    "hook": "Use am, is, and are to talk about people and things.",
    "passage": {
        "text": (
            "I am a student. She is my teacher. They are friends. "
            "The class is fun. We are happy here."
        ),
        "gloss": "Simple present of be.",
    },
    "form": {
        "title": "Verb to be",
        "rows": [
            {"label": "I", "pattern": "am", "example": "I am a student."},
            {"label": "he / she / it", "pattern": "is", "example": "She is my teacher."},
            {"label": "you / we / they", "pattern": "are", "example": "They are friends."},
        ],
    },
    "targets": [
        {"surface": "am", "gloss": "form of be for I"},
        {"surface": "is", "gloss": "form of be for he/she/it"},
        {"surface": "are", "gloss": "form of be for you/we/they"},
        {"surface": "student", "gloss": "a person who learns"},
    ],
    "checks": [
        {
            "type": "mcq",
            "prompt": "I ___ a student.",
            "options": ["am", "is", "are"],
            "answer": "am",
        }
    ],
    "writing": {
        "prompt": "Write two sentences about you and a friend using am/is/are.",
        "min_words": 10,
        "must_use": ["am", "is"],
    },
    "exit_check": {
        "type": "mcq",
        "prompt": "They ___ friends.",
        "options": ["am", "is", "are"],
        "answer": "are",
    },
}


DRILLS = [
    {
        "type": "mcq",
        "item_kind": "form_choose",
        "stem": "She ___ kind.",
        "options": ["am", "is", "are", "be"],
        "answer": "is",
    },
    {
        "type": "cloze",
        "item_kind": "cloze_form",
        "stem": "I ___ happy today.",
        "options": ["am", "is", "are"],
        "answer": "am",
    },
    {
        "type": "fix_grammar",
        "item_kind": "fix_grammar",
        "stem": "They is my friends.",
        "options": [],
        "answer": "They are my friends.",
    },
    {
        "type": "mcq",
        "item_kind": "contrast",
        "stem": "Choose the correct form: We ___ ready.",
        "options": ["am", "is", "are", "be"],
        "answer": "are",
    },
    {
        "type": "mcq",
        "item_kind": "paraphrase",
        "stem": "Which word means the form of be for I?",
        "options": ["am", "is", "are", "be"],
        "answer": "am",
    },
]


async def main(skill_id: int) -> None:
    async with AsyncSessionLocal() as db:
        source = (
            await db.execute(
                select(BookSkillSourceDB).where(
                    BookSkillSourceDB.skill_id == skill_id,
                    BookSkillSourceDB.is_excluded.is_(False),
                )
            )
        ).scalars().first()
        if source is None:
            raise SystemExit(f"No book_skill_source for skill {skill_id}")

        lesson = (
            await db.execute(
                select(SkillLessonDB).where(SkillLessonDB.skill_id == skill_id)
            )
        ).scalar_one_or_none()
        if lesson is None:
            lesson = SkillLessonDB(skill_id=skill_id)
            db.add(lesson)
        lesson.title = "Verb to be — present"
        lesson.objective = "You can use am, is, and are in short sentences."
        lesson.content = CONTENT
        lesson.source = "llm_reviewed"
        lesson.status = "published"
        lesson.book_source_id = int(source.id)

        # Unpublish old reading trivia so practice shows drills
        await db.execute(
            update(QuizQuestionDB)
            .where(
                QuizQuestionDB.skill_id == skill_id,
                QuizQuestionDB.status == QuizQuestionStatusEnum.published,
            )
            .values(status=QuizQuestionStatusEnum.draft)
        )

        batch_id = uuid.uuid4().hex
        surfaces = ["am", "is", "are", "student"]
        for item in DRILLS:
            db.add(
                QuizQuestionDB(
                    skill_id=skill_id,
                    book_id=int(source.book_id),
                    unit_id=int(source.unit_id),
                    question_type=QuizQuestionTypeEnum(item["type"]),
                    stem=item["stem"],
                    options=item["options"],
                    answer=item["answer"],
                    explanation="Practice be (am/is/are).",
                    difficulty="easy",
                    status=QuizQuestionStatusEnum.published,
                    generation_batch_id=batch_id,
                    task_brief={
                        "mode": "skill_drill",
                        "item_kind": item["item_kind"],
                        "alignment": "lesson",
                        "surfaces": surfaces,
                    },
                )
            )
        await db.commit()
        print(f"seeded lesson+{len(DRILLS)} skill_drill quizzes for skill {skill_id}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--skill-id", type=int, default=229)
    args = parser.parse_args()
    asyncio.run(main(args.skill_id))
