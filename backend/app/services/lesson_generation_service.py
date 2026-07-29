"""Offline generate skill lesson mini-units (text only) → draft / publish."""

from __future__ import annotations

import logging
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.book import BookDB
from app.models.book_skill_source import BookSkillSourceDB
from app.models.learning_skill import LearningSkillDB
from app.models.skill_lesson import SkillLessonDB
from app.services.book_chunk_service import get_unit_context
from app.services.lesson_content_validate import assert_publishable, normalize_content
from app.services.llm_client import chat_json

logger = logging.getLogger(__name__)

BASE_SYSTEM_PROMPT = """You are an ESL mini-unit author for ONE skill.
Teach in English only (English→English). Do NOT use Vietnamese or any other L1.

Learner CEFR level: {cefr}
All explanations, glosses, check prompts, options, notes, title, objective, and writing
instructions must be clear English that a {cefr} learner can understand — short words,
simple sentences; do not use harder vocabulary than the targets themselves when defining them.

Return JSON only:
{{
  "title": string (English),
  "objective": string (English can-do, e.g. "You can talk about your morning routine."),
  "passage": {{
    "text": "English paragraph 80-160 words at {cefr}",
    "gloss": "optional short English context tip at {cefr}"
  }},
  "targets": [
    {{
      "surface": "English word/phrase from the passage",
      "gloss": "simple English definition or paraphrase at {cefr} (not a translation)",
      "note": "optional short English usage tip at {cefr}"
    }}
  ],
  "checks": [
    {{
      "type": "mcq" or "cloze",
      "prompt": "English question at {cefr}",
      "options": ["..."] (required for mcq: 3-4 English options at {cefr}; empty for cloze),
      "answer": "exact correct string"
    }}
  ],
  "writing": {{
    "prompt": "English instruction asking the learner to write in English",
    "min_words": 15,
    "must_use": ["subset of target surfaces"]
  }}
}}
Rules:
- Exactly 4-7 targets that APPEAR in the passage.
- Exactly 1-2 checks testing those targets (meaning, form, or usage) in English.
- For mcq meaning checks: options must be English paraphrases/definitions, never translations.
- Passage English at {cefr}; ground in book excerpt when provided.
- Do not invent long plots; keep language-teaching focus.
- writing.must_use must be 1-3 items from targets.
"""

SKILL_TYPE_GUIDANCE: dict[str, str] = {
    "reading": """
Focus: comprehension of HOW language works in the passage.
- Passage may adapt/simplify the excerpt; keep teachable phrases.
- Targets = reusable phrases/patterns from the passage.
- Target gloss = simple English paraphrase at the learner CEFR level.
- Checks test phrase meaning or pattern in context (English), not plot trivia.
""",
    "grammar": """
Focus: one clear grammar target.
- Passage must showcase the target grammar naturally several times.
- Targets include form + example phrases; gloss explains the form in simple English.
- Checks test the grammar choice directly (English prompts/options).
""",
    "vocabulary": """
Focus: 4-7 concrete words or collocations.
- Passage uses each target naturally.
- Target gloss = learner-friendly English definition at CEFR (synonym or short paraphrase).
- Checks test meaning or collocation choice in English.
""",
    "functional": """
Focus: what the learner can say in a real situation.
- Passage is a short situational dialogue or email-like paragraph.
- Targets are reusable functional phrases; gloss explains when to say them (English).
- Checks test choosing the right phrase for the situation (English).
""",
}


def _build_system_prompt(*, skill_type: str, cefr: str = "A1") -> str:
    guidance = SKILL_TYPE_GUIDANCE.get(skill_type, SKILL_TYPE_GUIDANCE["functional"])
    return BASE_SYSTEM_PROMPT.format(cefr=cefr) + "\n" + guidance


async def _require_skill(db: AsyncSession, skill_id: int) -> LearningSkillDB:
    skill = (
        await db.execute(select(LearningSkillDB).where(LearningSkillDB.id == skill_id))
    ).scalar_one_or_none()
    if skill is None:
        raise ValueError("Skill not found")
    return skill


async def _resolve_primary_source(
    db: AsyncSession, skill_id: int
) -> BookSkillSourceDB | None:
    sources = list(
        (
            await db.execute(
                select(BookSkillSourceDB).where(
                    BookSkillSourceDB.skill_id == skill_id,
                    BookSkillSourceDB.is_excluded.is_(False),
                )
            )
        )
        .scalars()
        .all()
    )
    if not sources:
        return None
    return next((s for s in sources if s.is_primary), sources[0])


def _load_excerpt(skill: LearningSkillDB, book: BookDB, primary: BookSkillSourceDB) -> str:
    ctx = get_unit_context(int(primary.book_id), int(primary.unit_id), max_chars=3500)
    return str(ctx.get("text") or "")


async def generate_lesson_draft(db: AsyncSession, skill_id: int) -> SkillLessonDB:
    skill = await _require_skill(db, skill_id)
    skill_type = (
        skill.skill_type.value if hasattr(skill.skill_type, "value") else str(skill.skill_type)
    )
    cefr = skill.cefr_level.value if hasattr(skill.cefr_level, "value") else str(skill.cefr_level)

    primary = await _resolve_primary_source(db, skill_id)
    excerpt = ""
    book_source_id = None
    if primary is not None:
        book = (
            await db.execute(select(BookDB).where(BookDB.id == primary.book_id))
        ).scalar_one_or_none()
        if book is not None:
            excerpt = _load_excerpt(skill, book, primary)
            book_source_id = int(primary.id)

    user = (
        f"Skill title: {skill.title}\n"
        f"Skill type: {skill_type}\n"
        f"CEFR: {cefr}\n"
        f"Book excerpt (may be empty):\n{excerpt[:3500] or '(none)'}\n"
    )
    payload = chat_json(_build_system_prompt(skill_type=skill_type, cefr=cefr), user)
    if not isinstance(payload, dict):
        raise RuntimeError("LLM did not return a lesson object")

    if isinstance(payload.get("content"), dict) and "passage" in payload["content"]:
        content = normalize_content(payload["content"])
    elif "passage" in payload:
        content = normalize_content(payload)
    else:
        raise RuntimeError("LLM lesson missing passage/content")
    title = str(payload.get("title") or skill.title).strip() or skill.title
    objective = str(payload.get("objective") or f"Practice: {skill.title}").strip()

    existing = (
        await db.execute(select(SkillLessonDB).where(SkillLessonDB.skill_id == skill_id))
    ).scalar_one_or_none()
    if existing is None:
        existing = SkillLessonDB(skill_id=skill_id)
        db.add(existing)

    existing.title = title
    existing.objective = objective
    existing.content = content
    existing.source = "llm_reviewed"
    existing.status = "draft"
    existing.book_source_id = book_source_id
    await db.commit()
    await db.refresh(existing)
    return existing


async def publish_lesson(db: AsyncSession, skill_id: int) -> SkillLessonDB:
    lesson = (
        await db.execute(select(SkillLessonDB).where(SkillLessonDB.skill_id == skill_id))
    ).scalar_one_or_none()
    if lesson is None:
        raise ValueError("Lesson not found")
    assert_publishable(lesson.content if isinstance(lesson.content, dict) else {})
    lesson.status = "published"
    await db.commit()
    await db.refresh(lesson)
    return lesson


def lesson_to_dict(lesson: SkillLessonDB) -> dict[str, Any]:
    return {
        "id": int(lesson.id),
        "skill_id": int(lesson.skill_id),
        "title": lesson.title,
        "objective": lesson.objective,
        "content": lesson.content,
        "source": lesson.source,
        "status": lesson.status,
        "book_source_id": int(lesson.book_source_id) if lesson.book_source_id else None,
    }
