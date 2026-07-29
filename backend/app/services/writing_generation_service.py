"""Generate draft TOEIC Writing tasks into the unified quiz bank."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import (
    QuizQuestionStatusEnum,
    QuizQuestionTypeEnum,
    ToeicPartEnum,
)
from app.models.book_skill_source import BookSkillSourceDB
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
No images / picture descriptions — never invent media_url or picture prompts.

Return JSON: {"tasks":[...]} where each task has:
toeic_part (w1|w2|w3),
stem (instructions for the learner),
prompt_words (for w1 only: exactly TWO English words/phrases the learner must use),
passage (for w2: the inbound email/request body; for w1/w3: null),
task_brief (object):
  w1: {must_use_both_words: true}
  w2: {role, must_ask, must_provide} with integer counts
  w3: {min_words: 300, prompt_focus: string}

W1 — Write a sentence based on two cue words (no picture):
- stem like: "Write one sentence using the two words below (any order; you may change word forms)."
- prompt_words: two workplace-related words from or inspired by the EXCERPT.

W2 — Respond to a written request (email):
- passage = full inbound email with To/From/Subject/body.
- stem tells the learner role and constraints (ask N questions / provide M pieces of information).

W3 — Opinion essay:
- stem is the essay prompt; recommend supporting with reasons and examples.
- task_brief.min_words default 300.

Use generic business names when the excerpt lacks specifics.
"""


def validate_writing_tasks(tasks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    valid: list[dict[str, Any]] = []
    for item in tasks:
        normalized = _normalize_writing_task(item)
        if normalized is not None:
            valid.append(normalized)
    return valid


def _normalize_writing_task(item: dict[str, Any]) -> dict[str, Any] | None:
    part = str(item.get("toeic_part") or "").strip()
    stem = (item.get("stem") or "").strip()
    if part not in {"w1", "w2", "w3"} or not stem:
        return None
    brief = item.get("task_brief") if isinstance(item.get("task_brief"), dict) else {}
    passage = item.get("passage")
    passage_text = passage.strip() if isinstance(passage, str) else ""
    prompt_words = item.get("prompt_words")

    if part == "w1":
        if not isinstance(prompt_words, list) or len(prompt_words) != 2:
            return None
        words = [str(w).strip() for w in prompt_words if str(w).strip()]
        if len(words) != 2:
            return None
        return {
            "toeic_part": part,
            "stem": stem,
            "passage": None,
            "prompt_words": words,
            "task_brief": {**brief, "must_use_both_words": True},
        }

    if part == "w2" and not passage_text:
        return None
    if part == "w3":
        brief = {**brief, "min_words": int(brief.get("min_words") or 300)}
    return {
        "toeic_part": part,
        "stem": stem,
        "passage": passage_text or None,
        "prompt_words": None,
        "task_brief": brief,
    }


def _request_validated_writing_tasks(
    primary: BookSkillSourceDB,
    skill: LearningSkillDB,
    ctx: dict[str, Any],
    count: int,
) -> list[dict[str, Any]]:
    payload = chat_json(
        SYSTEM_PROMPT,
        f"Unit: {primary.unit_title or skill.title}\n"
        f"Generate exactly {count} writing tasks (prefer a mix of w1, w2, w3 when count>=2).\n"
        f"EXCERPT:\n{ctx['text']}\n",
    )
    raw = payload.get("tasks") if isinstance(payload, dict) else payload
    if not isinstance(raw, list):
        raise ValueError("LLM didn't return writing tasks.")
    validated = validate_writing_tasks(raw)
    if not validated:
        raise ValueError("No valid writing tasks after validation.")
    return validated


async def _ensure_writing_passage(
    db: AsyncSession,
    primary: BookSkillSourceDB,
    item: dict[str, Any],
) -> int | None:
    passage_text = item.get("passage")
    if not passage_text:
        return None
    passage = QuizPassageDB(
        book_id=primary.book_id,
        unit_id=primary.unit_id,
        toeic_part=ToeicPartEnum(item["toeic_part"]),
        body=passage_text,
        status=QuizQuestionStatusEnum.draft,
    )
    db.add(passage)
    await db.flush()
    return int(passage.id)


def _build_writing_draft_row(
    skill: LearningSkillDB,
    primary: BookSkillSourceDB,
    ctx: dict[str, Any],
    batch_id: str,
    item: dict[str, Any],
    *,
    passage_id: int | None,
) -> QuizQuestionDB:
    return QuizQuestionDB(
        skill_id=skill.id,
        book_id=primary.book_id,
        unit_id=primary.unit_id,
        question_type=QuizQuestionTypeEnum.writing,
        toeic_part=ToeicPartEnum(item["toeic_part"]),
        stem=item["stem"],
        passage=item.get("passage"),
        passage_id=passage_id,
        prompt_words=item.get("prompt_words"),
        media_url=None,
        task_brief=item.get("task_brief"),
        options=None,
        answer="",
        cefr_level=skill.cefr_level,
        difficulty="medium",
        status=QuizQuestionStatusEnum.draft,
        generation_batch_id=batch_id,
        source_chunk_ids=ctx["chunk_ids"],
    )


async def _persist_writing_drafts(
    db: AsyncSession,
    skill: LearningSkillDB,
    primary: BookSkillSourceDB,
    ctx: dict[str, Any],
    validated: list[dict[str, Any]],
) -> list[QuizQuestionDB]:
    batch_id = uuid.uuid4().hex
    rows: list[QuizQuestionDB] = []
    for item in validated:
        passage_id = await _ensure_writing_passage(db, primary, item)
        rows.append(
            _build_writing_draft_row(
                skill, primary, ctx, batch_id, item, passage_id=passage_id
            )
        )
    db.add_all(rows)
    await db.commit()
    for row in rows:
        await db.refresh(row)
    return rows


async def generate_writing_for_skill(
    db: AsyncSession, skill_id: int, *, count: int = 2
) -> list[QuizQuestionDB]:
    """Create draft W1 (cue words only) / W2 / W3 writing items — no images."""
    if count < 1:
        raise ValueError("count must be >= 1")

    skill = await _require_skill(db, skill_id)
    primary = await _resolve_primary_source(db, skill_id)
    book = await _require_source_book(db, int(primary.book_id))
    ctx = _load_unit_context(skill, book, primary)

    validated = _request_validated_writing_tasks(primary, skill, ctx, count)
    return await _persist_writing_drafts(db, skill, primary, ctx, validated)


def writing_publishable(item: QuizQuestionDB) -> bool:
    """W1 needs stem + two prompt_words (no image); W2/W3 as before."""
    part = item.toeic_part.value if item.toeic_part else None
    if part == "w1":
        words = item.prompt_words if isinstance(item.prompt_words, list) else []
        return bool(item.stem) and len(words) == 2
    if part == "w2":
        return bool(item.stem) and bool(item.passage or item.passage_id)
    if part == "w3":
        return bool(item.stem)
    return False
