"""Generate draft quiz questions for a learning skill from primary book unit context."""

from __future__ import annotations

import re
import uuid
from difflib import SequenceMatcher
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.book_skill_source import BookSkillSourceDB
from app.models.enums import CEFRLevel, QuizQuestionStatusEnum, QuizQuestionTypeEnum
from app.models.learning_skill import LearningSkillDB
from app.models.quiz_question import QuizQuestionDB
from app.services.book_chunk_service import get_unit_context
from app.services.cefr_descriptors import passage_length_range
from app.services.llm_client import chat_json

SYSTEM_PROMPT = """You are an expert English assessment writer for CEFR-aligned courses.
Generate exam questions ONLY from the provided textbook excerpt.
Do not invent rules unsupported by the excerpt.
Do not copy answer keys if present; write new stems.
Return JSON: {"questions":[...]} with fields:
type (mcq|cloze|fix_grammar), stem, options (4 strings for mcq else null),
answer, explanation, skill, difficulty (easy|medium|hard).
For mcq, answer must exactly match one option.
"""

_NON_ALNUM = re.compile(r"[^a-z0-9]+")
PASSAGE_GROUNDING_RATIO = 0.55


def build_generation_prompt(
    unit_title: str,
    cefr_level: str | None,
    context: str,
    count: int,
) -> str:
    return (
        f"Unit: {unit_title}\n"
        f"CEFR: {cefr_level or 'B1'}\n"
        f"Generate exactly {count} questions.\n"
        f"Prefer mcq; include at most 1 cloze.\n\n"
        f"EXCERPT:\n{context}\n"
    )


def _normalize_text(text: str) -> str:
    return _NON_ALNUM.sub(" ", text.lower()).strip()


def passage_grounded(
    passage: str, excerpt: str, *, min_ratio: float = PASSAGE_GROUNDING_RATIO
) -> bool:
    """True if passage appears in excerpt (substring) or fuzzy-matches a window."""
    needle = _normalize_text(passage)
    haystack = _normalize_text(excerpt)
    if not needle or not haystack:
        return False
    if needle in haystack:
        return True
    target = max(20, len(needle))
    lo = max(20, int(target * 0.8))
    hi = min(len(haystack), int(target * 1.2))
    if hi < lo:
        return SequenceMatcher(None, needle, haystack).ratio() >= min_ratio
    step = max(1, lo // 4)
    best = 0.0
    for start in range(0, max(1, len(haystack) - lo + 1), step):
        window = haystack[start : start + hi]
        if not window:
            continue
        best = max(best, SequenceMatcher(None, needle, window).ratio())
        if best >= min_ratio:
            return True
    return best >= min_ratio


def passage_length_ok(passage: str, cefr_level: CEFRLevel | str | None) -> bool:
    """Reject passages wildly outside the CEFR length band (min/2 .. max*2)."""
    if cefr_level is None:
        return True
    min_chars, max_chars = passage_length_range(cefr_level)
    n = len(passage.strip())
    return (min_chars // 2) <= n <= (max_chars * 2)


def validate_generated_questions(
    items: list[dict[str, Any]],
    *,
    excerpt: str | None = None,
    blueprint: list[dict[str, Any]] | None = None,
    cefr_level: CEFRLevel | str | None = None,
) -> list[dict[str, Any]]:
    """
    Validate LLM quiz items.

    When ``blueprint`` is provided, items are paired by index; blueprint entries with
    ``requires_passage`` must include a passage grounded in ``excerpt``.
    Without blueprint (legacy), passage is optional and not grounded.
    """
    valid: list[dict[str, Any]] = []
    for index, item in enumerate(items):
        qtype = item.get("type")
        stem = (item.get("stem") or "").strip()
        answer = str(item.get("answer") or "").strip()
        if not stem or not answer or qtype not in {"mcq", "cloze", "fix_grammar"}:
            continue
        options = item.get("options")
        if qtype == "mcq":
            if not isinstance(options, list) or len(options) != 4:
                continue
            if answer not in options:
                continue

        passage_raw = item.get("passage")
        passage = (passage_raw or "").strip() if isinstance(passage_raw, str) else ""

        requires_passage = False
        if blueprint is not None:
            if index < len(blueprint):
                requires_passage = bool(blueprint[index].get("requires_passage"))
            else:
                requires_passage = any(bool(b.get("requires_passage")) for b in blueprint)

        if requires_passage:
            if not passage or excerpt is None:
                continue
            if not passage_grounded(passage, excerpt):
                continue
            if not passage_length_ok(passage, cefr_level):
                continue
        elif passage and excerpt is not None:
            if not passage_grounded(passage, excerpt):
                continue
            if cefr_level is not None and not passage_length_ok(passage, cefr_level):
                continue

        valid.append(
            {
                "type": qtype,
                "stem": stem,
                "passage": passage or None,
                "options": options if qtype == "mcq" else None,
                "answer": answer,
                "explanation": item.get("explanation"),
                "skill": item.get("skill") or "grammar",
                "difficulty": item.get("difficulty") or "medium",
                "cefr_focus": item.get("cefr_focus"),
            }
        )
    return valid


async def generate_quiz_for_skill(
    db: AsyncSession,
    skill_id: int,
    count: int = 8,
) -> list[QuizQuestionDB]:
    """Sinh quiz cho skill chuẩn: primary source unit → context → LLM → draft rows."""
    skill = (
        await db.execute(select(LearningSkillDB).where(LearningSkillDB.id == skill_id))
    ).scalar_one_or_none()
    if skill is None:
        raise ValueError("Không tìm thấy skill")

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
        raise ValueError("Skill chưa có book source — sync sách trước")

    primary = next((s for s in sources if s.is_primary), sources[0])
    if primary.is_excluded:
        raise ValueError("Primary source bị exclude — không sinh quiz")

    ctx = get_unit_context(int(primary.book_id), int(primary.unit_id), mode="prefix")
    if not ctx["text"]:
        raise ValueError("Unit nguồn không có text chunk")

    cefr = skill.cefr_level.value if hasattr(skill.cefr_level, "value") else str(skill.cefr_level)
    unit_title = primary.unit_title or skill.title
    payload = chat_json(
        SYSTEM_PROMPT,
        build_generation_prompt(unit_title, cefr, ctx["text"], count),
    )
    raw_questions = payload.get("questions") if isinstance(payload, dict) else payload
    if not isinstance(raw_questions, list):
        raise ValueError("LLM không trả về danh sách questions")

    validated = validate_generated_questions(raw_questions)
    if not validated:
        raise ValueError("Không có câu hỏi hợp lệ sau validate")

    batch_id = uuid.uuid4().hex
    rows: list[QuizQuestionDB] = []
    for item in validated:
        row = QuizQuestionDB(
            skill_id=skill.id,
            book_id=primary.book_id,
            unit_id=primary.unit_id,
            question_type=QuizQuestionTypeEnum(item["type"]),
            stem=item["stem"],
            passage=item.get("passage"),
            options=item["options"],
            answer=item["answer"],
            explanation=item.get("explanation"),
            cefr_level=skill.cefr_level,
            difficulty=item["difficulty"],
            status=QuizQuestionStatusEnum.draft,
            generation_batch_id=batch_id,
            source_chunk_ids=ctx["chunk_ids"],
        )
        db.add(row)
        rows.append(row)
    await db.commit()
    for row in rows:
        await db.refresh(row)
    return rows
