"""Generate draft TOEIC Writing tasks into the unified quiz bank."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.book import BookDB
from app.models.book_skill_source import BookSkillSourceDB
from app.models.enums import (
    QuizQuestionStatusEnum,
    QuizQuestionTypeEnum,
    ToeicPartEnum,
)
from app.models.learning_skill import LearningSkillDB
from app.models.quiz_passage import QuizPassageDB
from app.models.quiz_question import QuizQuestionDB
from app.services.llm_client import chat_json
from app.services.quiz_generation_service import (
    _load_unit_context,
    _require_skill,
    _require_source_book,
    _resolve_primary_source,
)

SYSTEM_PROMPT = """You write TOEIC Writing practice tasks grounded in a textbook EXCERPT.
Return JSON: {"tasks":[...]} where each task has:
toeic_part (w2|w3 only in this endpoint),
stem (instructions for the learner),
passage (for w2: the inbound email body; for w3: null),
task_brief (object):
  w2: {role, must_ask, must_provide} with integer counts
  w3: {min_words: 300, prompt_focus: string}
Do not invent company facts absent from the excerpt when possible; otherwise use generic business names.
"""


def validate_writing_tasks(tasks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    valid: list[dict[str, Any]] = []
    for item in tasks:
        part = str(item.get("toeic_part") or "").strip()
        stem = (item.get("stem") or "").strip()
        if part not in {"w2", "w3"} or not stem:
            continue
        brief = item.get("task_brief") if isinstance(item.get("task_brief"), dict) else {}
        passage = item.get("passage")
        passage_text = passage.strip() if isinstance(passage, str) else ""
        if part == "w2" and not passage_text:
            continue
        if part == "w3":
            brief = {**brief, "min_words": int(brief.get("min_words") or 300)}
        valid.append(
            {
                "toeic_part": part,
                "stem": stem,
                "passage": passage_text or None,
                "task_brief": brief,
            }
        )
    return valid


async def generate_writing_for_skill(
    db: AsyncSession, skill_id: int, *, count: int = 2
) -> list[QuizQuestionDB]:
    """Create draft W2/W3 writing items (W1 requires media_url — admin upload separately)."""
    if count < 1:
        raise ValueError("count must be >= 1")
    skill = await _require_skill(db, skill_id)
    primary = await _resolve_primary_source(db, skill_id)
    book = await _require_source_book(db, int(primary.book_id))
    ctx = _load_unit_context(skill, book, primary)

    payload = chat_json(
        SYSTEM_PROMPT,
        f"Unit: {primary.unit_title or skill.title}\n"
        f"Generate exactly {count} writing tasks (mix w2 and w3).\n"
        f"EXCERPT:\n{ctx['text']}\n",
    )
    raw = payload.get("tasks") if isinstance(payload, dict) else payload
    if not isinstance(raw, list):
        raise ValueError("LLM didn't return writing tasks.")
    validated = validate_writing_tasks(raw)
    if not validated:
        raise ValueError("No valid writing tasks after validation.")

    batch_id = uuid.uuid4().hex
    rows: list[QuizQuestionDB] = []
    for item in validated:
        passage_id = None
        if item.get("passage"):
            passage = QuizPassageDB(
                book_id=primary.book_id,
                unit_id=primary.unit_id,
                toeic_part=ToeicPartEnum(item["toeic_part"]),
                body=item["passage"],
                status=QuizQuestionStatusEnum.draft,
            )
            db.add(passage)
            await db.flush()
            passage_id = int(passage.id)
        rows.append(
            QuizQuestionDB(
                skill_id=skill.id,
                book_id=primary.book_id,
                unit_id=primary.unit_id,
                question_type=QuizQuestionTypeEnum.writing,
                toeic_part=ToeicPartEnum(item["toeic_part"]),
                stem=item["stem"],
                passage=item.get("passage"),
                passage_id=passage_id,
                task_brief=item.get("task_brief"),
                options=None,
                answer="",
                cefr_level=skill.cefr_level,
                difficulty="medium",
                status=QuizQuestionStatusEnum.draft,
                generation_batch_id=batch_id,
                source_chunk_ids=ctx["chunk_ids"],
            )
        )
    db.add_all(rows)
    await db.commit()
    for row in rows:
        await db.refresh(row)
    return rows


def writing_publishable(item: QuizQuestionDB) -> bool:
    """W1 requires media_url before publish; W2/W3 need stem (+ passage for W2)."""
    part = item.toeic_part.value if item.toeic_part else None
    if part == "w1":
        return bool(item.media_url) and bool(item.stem) and bool(item.prompt_words)
    if part == "w2":
        return bool(item.stem) and bool(item.passage or item.passage_id)
    if part == "w3":
        return bool(item.stem)
    return False
