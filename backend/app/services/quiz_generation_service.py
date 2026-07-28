"""Generate draft quiz questions for a learning skill from primary book unit context."""

from __future__ import annotations

import re
import uuid
from difflib import SequenceMatcher
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.book import BookDB
from app.models.book_skill_source import BookSkillSourceDB
from app.models.enums import (
    BookTypeEnum,
    CEFRLevel,
    QuizQuestionStatusEnum,
    QuizQuestionTypeEnum,
    SkillTypeEnum,
    ToeicPartEnum,
)
from app.models.learning_skill import LearningSkillDB
from app.models.quiz_passage import QuizPassageDB
from app.models.quiz_question import QuizQuestionDB
from app.services.book_chunk_service import PackMode, get_unit_context
from app.services.cefr_descriptors import (
    blueprint_as_prompt_lines,
    blueprint_for,
    get_can_do,
    passage_length_range,
)
from app.services.llm_client import chat_json

SYSTEM_PROMPT = """You are an expert TOEIC Reading (RC) item writer.
Write items ONLY from the provided textbook EXCERPT (business/workplace English tone like official TOEIC RC).
Follow official TOEIC Reading form exactly — Parts 5, 6, and 7 only. Never use cloze or fix_grammar.

PART 5 (toeic_part=r5) — Incomplete Sentences:
- One standalone sentence with a single blank marked exactly as: -------
- Four short options (word / phrase / word-form variants). Do NOT prefix options with (A)/(B)/(C)/(D) in the JSON.
- Target: grammar (word form, tense, pronoun), vocabulary, preposition, or connector.
- No passage field (null/omit). No multi-sentence stem.

PART 6 (toeic_part=r6) — Text Completion:
- One short workplace document (email, letter, memo, flyer, or notice), ~80–140 words, grounded in the EXCERPT.
- Put 3–4 blanks inside the passage, each marked like: ------- (1)  then ------- (2) etc.
- Start the passage with a document cue line when helpful, e.g. "E-mail" / "Memo" / "Flyer:" and headers (To/From/Subject) for emails.
- For EACH blank, emit a separate question item with the SAME passage text and SAME passage_group.
- Stem examples: "Choose the best answer for blank (1)." (match blank numbers).
- Options: mix types across the set — at least one full-sentence insertion, plus word form / vocab / transition / pronoun as appropriate.
- Four options each; answer must match one option exactly.

PART 7 (toeic_part=r7) — Reading Comprehension:
- One short text (notice, e-mail, memo, article excerpt, advertisement) grounded in the EXCERPT.
- Prefatory style in passage is fine: "Notice:" / "E-mail:" with To/From/Subject when relevant.
- Several MCQ items may share the same passage via the same passage_group.
- Stems: purpose/main idea, detail (who/when/what), or inference ("What is suggested about...?").
- Four plausible options; only one correct; distractors may reuse words from the text.

Return JSON: {"questions":[...]} with fields:
type (must be "mcq"), toeic_part (r5|r6|r7),
passage (string; required for r6/r7; null for r5),
stem, options (exactly 4 strings), answer, explanation,
skill, difficulty (easy|medium|hard), cefr_focus (string),
passage_group (required string for r6/r7 items that share one text; omit for r5).
For mcq, answer must exactly match one option string.
Follow the item blueprint order, toeic_part, and cefr_focus exactly.
For r6/r7 passages: adapt the EXCERPT into a TOEIC notice/email/memo — keep the same
topic and reuse concrete vocabulary/names from the EXCERPT (paraphrase OK). Do not invent
an unrelated corporate story with zero words from the EXCERPT.
"""

_ALLOWED_READING_TYPES = {"mcq"}
_ALLOWED_TOEIC_PARTS = {"r5", "r6", "r7"}
_LEGACY_REJECTED_TYPES = {"cloze", "fix_grammar"}

_NON_ALNUM = re.compile(r"[^a-z0-9]+")
PASSAGE_GROUNDING_RATIO = 0.55
# Soft theme check for TOEIC-style paraphrase of the excerpt.
_PASSAGE_MIN_OVERLAP_WORDS = 4
_PASSAGE_MIN_OVERLAP_RATIO = 0.12
_STOPWORDS = frozenset(
    {
        "about",
        "after",
        "again",
        "also",
        "been",
        "before",
        "being",
        "between",
        "could",
        "does",
        "from",
        "have",
        "into",
        "just",
        "more",
        "most",
        "other",
        "over",
        "same",
        "should",
        "some",
        "such",
        "than",
        "that",
        "their",
        "them",
        "then",
        "there",
        "these",
        "they",
        "this",
        "those",
        "through",
        "under",
        "very",
        "were",
        "what",
        "when",
        "where",
        "which",
        "while",
        "will",
        "with",
        "would",
        "your",
    }
)
CONTEXT_CHAR_CAP = 8000


def context_budget_for_level(cefr_level: CEFRLevel | str | None) -> int:
    """Larger context for higher levels, capped at 8k."""
    base = settings.QUIZ_CONTEXT_MAX_CHARS
    level = cefr_level.value if hasattr(cefr_level, "value") else cefr_level
    bump = {
        "A1": 0,
        "A2": 500,
        "B1": 1500,
        "B2": 2500,
        "C1": 3000,
    }.get(str(level or "B1"), 1500)
    return min(CONTEXT_CHAR_CAP, base + bump)


def context_mode_for(
    book_type: BookTypeEnum | str | None,
    skill_type: SkillTypeEnum | str | None,
) -> PackMode:
    bt = book_type.value if hasattr(book_type, "value") else book_type
    st = skill_type.value if hasattr(skill_type, "value") else skill_type
    if bt == BookTypeEnum.reading_practice.value or st == SkillTypeEnum.reading.value:
        return "stride"
    return "prefix"


def build_generation_prompt(
    unit_title: str,
    cefr_level: str | None,
    context: str,
    count: int,
    *,
    can_do: str | None = None,
    blueprint: list[dict[str, Any]] | None = None,
    skill_type: str | None = None,
    book_type: str | None = None,
) -> str:
    level = cefr_level or "B1"
    min_chars, max_chars = passage_length_range(level)
    parts = [
        f"Unit: {unit_title}",
        f"CEFR level: {level}",
        f"Skill type: {skill_type or 'grammar'}",
        f"Book type: {book_type or 'freeform'}",
        f"Can-do target: {can_do or get_can_do(level, skill_type or 'grammar')}",
        f"For r6/r7 passages, aim about {min_chars}-{max_chars} characters "
        f"(stay within that band). r5 has no passage.",
        "Match official TOEIC RC layout: Part 5 = one sentence + ------- blank; "
        "Part 6 = document with numbered blanks + options below; "
        "Part 7 = notice/email/article + comprehension questions.",
        f"Generate exactly {count} questions matching the blueprint below.",
    ]
    if blueprint:
        parts.append(blueprint_as_prompt_lines(blueprint))
    else:
        parts.append("Prefer TOEIC mcq parts r5/r6/r7 only.")
    parts.append(f"\nEXCERPT:\n{context}\n")
    return "\n".join(parts)


def _normalize_text(text: str) -> str:
    return _NON_ALNUM.sub(" ", text.lower()).strip()


def _content_tokens(text: str) -> set[str]:
    return {
        tok
        for tok in _normalize_text(text).split()
        if len(tok) >= 4 and tok not in _STOPWORDS
    }


def passage_theme_overlap(passage: str, excerpt: str) -> bool:
    """True if passage reuses enough content words from the excerpt (TOEIC paraphrase)."""
    p_toks = _content_tokens(passage)
    e_toks = _content_tokens(excerpt)
    if not p_toks or not e_toks:
        return False
    overlap = p_toks & e_toks
    if len(overlap) < _PASSAGE_MIN_OVERLAP_WORDS:
        return False
    return (len(overlap) / len(p_toks)) >= _PASSAGE_MIN_OVERLAP_RATIO


def passage_grounded(
    passage: str, excerpt: str, *, min_ratio: float = PASSAGE_GROUNDING_RATIO
) -> bool:
    """True if passage appears in excerpt, fuzzy-matches a window, or shares theme words."""
    needle = _normalize_text(passage)
    haystack = _normalize_text(excerpt)
    if not needle or not haystack:
        return False
    if needle in haystack:
        return True
    if passage_theme_overlap(passage, excerpt):
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
    Validate LLM quiz items for TOEIC Reading (mcq + toeic_part r5|r6|r7).

    When ``blueprint`` is provided, items are paired by index; blueprint entries with
    ``requires_passage`` must include a passage grounded in ``excerpt``.
    Rejects cloze / fix_grammar. Without blueprint (legacy callers), still requires
    mcq + toeic_part when present; if toeic_part missing, accept mcq only for tests.
    """
    valid: list[dict[str, Any]] = []
    for index, item in enumerate(items):
        qtype = item.get("type")
        if qtype in _LEGACY_REJECTED_TYPES:
            continue
        stem = (item.get("stem") or "").strip()
        answer = str(item.get("answer") or "").strip()
        if not stem or not answer or qtype not in _ALLOWED_READING_TYPES:
            continue

        toeic_part = item.get("toeic_part")
        if blueprint is not None and index < len(blueprint):
            toeic_part = toeic_part or blueprint[index].get("toeic_part")
        toeic_part = str(toeic_part).strip() if toeic_part else None
        if toeic_part is not None and toeic_part not in _ALLOWED_TOEIC_PARTS:
            continue
        if blueprint is not None and toeic_part not in _ALLOWED_TOEIC_PARTS:
            continue

        options = item.get("options")
        if not isinstance(options, list) or len(options) != 4:
            continue
        if answer not in options:
            continue

        passage_raw = item.get("passage")
        passage = (passage_raw or "").strip() if isinstance(passage_raw, str) else ""

        # Prefer the item's declared part for passage rules (LLM may reorder vs blueprint).
        requires_passage = toeic_part in {"r6", "r7"}
        if not requires_passage and blueprint is not None and toeic_part is None:
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
        elif toeic_part == "r5":
            if "-------" not in stem:
                continue
            passage = ""  # Part 5 never stores a passage
        elif passage and excerpt is not None:
            if not passage_grounded(passage, excerpt):
                continue
            if cefr_level is not None and not passage_length_ok(passage, cefr_level):
                continue

        valid.append(
            {
                "type": qtype,
                "toeic_part": toeic_part,
                "stem": stem,
                "passage": passage or None,
                "passage_group": item.get("passage_group"),
                "options": options,
                "answer": answer,
                "explanation": item.get("explanation"),
                "skill": item.get("skill") or "grammar",
                "difficulty": item.get("difficulty") or "medium",
                "cefr_focus": item.get("cefr_focus"),
            }
        )
    return valid


async def _require_skill(db: AsyncSession, skill_id: int) -> LearningSkillDB:
    skill = (
        await db.execute(select(LearningSkillDB).where(LearningSkillDB.id == skill_id))
    ).scalar_one_or_none()
    if skill is None:
        raise ValueError("Don`t have skill")
    return skill


async def _resolve_primary_source(db: AsyncSession, skill_id: int) -> BookSkillSourceDB:
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
        raise ValueError("Skill doesn't have book source — sync book first.")

    primary = next((s for s in sources if s.is_primary), sources[0])
    if primary.is_excluded:
        raise ValueError("Primary source is excluded — can't generate quiz.")
    return primary


async def _require_source_book(db: AsyncSession, book_id: int) -> BookDB:
    book = (await db.execute(select(BookDB).where(BookDB.id == book_id))).scalar_one_or_none()
    if book is None:
        raise ValueError("Don't have source book.")
    return book


def _load_unit_context(
    skill: LearningSkillDB, book: BookDB, primary: BookSkillSourceDB
) -> dict[str, Any]:
    skill_type = skill.skill_type or SkillTypeEnum.grammar
    book_type = book.book_type or BookTypeEnum.freeform
    ctx = get_unit_context(
        int(primary.book_id),
        int(primary.unit_id),
        max_chars=context_budget_for_level(skill.cefr_level),
        mode=context_mode_for(book_type, skill_type),
    )
    if not ctx["text"]:
        raise ValueError("Source unit doesn't have text chunk.")
    return ctx


def _request_validated_items(
    skill: LearningSkillDB,
    book: BookDB,
    primary: BookSkillSourceDB,
    ctx: dict[str, Any],
    count: int,
) -> list[dict[str, Any]]:
    """Build the CEFR-aware prompt, call the LLM, and keep only grounded items."""
    cefr = skill.cefr_level
    skill_type = skill.skill_type or SkillTypeEnum.grammar
    book_type = book.book_type or BookTypeEnum.freeform
    blueprint = blueprint_for(book_type, skill_type, count)
    user_prompt = build_generation_prompt(
        primary.unit_title or skill.title,
        cefr.value if hasattr(cefr, "value") else str(cefr),
        ctx["text"],
        count,
        can_do=get_can_do(cefr, skill_type),
        blueprint=blueprint,
        skill_type=skill_type.value if hasattr(skill_type, "value") else str(skill_type),
        book_type=book_type.value if hasattr(book_type, "value") else str(book_type),
    )

    best: list[dict[str, Any]] = []
    for attempt in range(2):
        prompt = user_prompt
        if attempt > 0:
            prompt += (
                f"\nRETRY: previous attempt kept only {len(best)}/{count} valid items. "
                "Return exactly the full set. For every r6/r7 item include a passage that "
                "reuses topic words from the EXCERPT. Every r5 stem must contain ------- .\n"
            )
        payload = chat_json(SYSTEM_PROMPT, prompt)
        raw_questions = payload.get("questions") if isinstance(payload, dict) else payload
        if not isinstance(raw_questions, list):
            continue
        validated = validate_generated_questions(
            raw_questions,
            excerpt=ctx["text"],
            blueprint=blueprint,
            cefr_level=cefr,
        )
        if len(validated) > len(best):
            best = validated
        if len(best) >= count:
            break

    if not best:
        raise ValueError("No valid questions after validation.")
    if len(best) < max(2, count // 2):
        raise ValueError(
            f"Only {len(best)}/{count} questions passed validation "
            "(passages must reuse EXCERPT vocabulary; r5 needs -------). Try again."
        )
    return best[:count]


def _build_draft_row(
    skill: LearningSkillDB,
    primary: BookSkillSourceDB,
    ctx: dict[str, Any],
    batch_id: str,
    item: dict[str, Any],
    *,
    passage_id: int | None = None,
) -> QuizQuestionDB:
    toeic_raw = item.get("toeic_part")
    toeic_part = ToeicPartEnum(toeic_raw) if toeic_raw in _ALLOWED_TOEIC_PARTS else None
    return QuizQuestionDB(
        skill_id=skill.id,
        book_id=primary.book_id,
        unit_id=primary.unit_id,
        question_type=QuizQuestionTypeEnum(item["type"]),
        stem=item["stem"],
        passage=item.get("passage"),
        passage_id=passage_id,
        toeic_part=toeic_part,
        options=item["options"],
        answer=item["answer"],
        explanation=item.get("explanation"),
        cefr_level=skill.cefr_level,
        difficulty=item["difficulty"],
        status=QuizQuestionStatusEnum.draft,
        generation_batch_id=batch_id,
        source_chunk_ids=ctx["chunk_ids"],
    )


async def _persist_draft_questions(
    db: AsyncSession,
    skill: LearningSkillDB,
    primary: BookSkillSourceDB,
    ctx: dict[str, Any],
    validated: list[dict[str, Any]],
) -> list[QuizQuestionDB]:
    batch_id = uuid.uuid4().hex
    passage_ids: dict[str, int] = {}
    rows: list[QuizQuestionDB] = []
    for item in validated:
        passage_id = await _ensure_passage_for_item(
            db, primary, item, passage_ids=passage_ids
        )
        rows.append(
            _build_draft_row(
                skill, primary, ctx, batch_id, item, passage_id=passage_id
            )
        )
    db.add_all(rows)
    await db.commit()
    for row in rows:
        await db.refresh(row)
    return rows


async def _ensure_passage_for_item(
    db: AsyncSession,
    primary: BookSkillSourceDB,
    item: dict[str, Any],
    *,
    passage_ids: dict[str, int],
) -> int | None:
    """Create or reuse QuizPassageDB for r6/r7 items that share passage_group/text."""
    toeic_part = item.get("toeic_part")
    passage_text = (item.get("passage") or "").strip()
    if toeic_part not in {"r6", "r7"} or not passage_text:
        return None
    group_key = str(item.get("passage_group") or "").strip() or passage_text
    if group_key in passage_ids:
        return passage_ids[group_key]
    row = QuizPassageDB(
        book_id=primary.book_id,
        unit_id=primary.unit_id,
        toeic_part=ToeicPartEnum(toeic_part),
        body=passage_text,
        status=QuizQuestionStatusEnum.draft,
        meta={"generation": True},
    )
    db.add(row)
    await db.flush()
    passage_ids[group_key] = int(row.id)
    return int(row.id)


async def generate_quiz_for_skill(
    db: AsyncSession,
    skill_id: int,
    count: int = 8,
) -> list[QuizQuestionDB]:
    """Generate CEFR-aware quiz: blueprint + passage grounding → draft rows."""
    skill = await _require_skill(db, skill_id)
    primary = await _resolve_primary_source(db, skill_id)
    book = await _require_source_book(db, int(primary.book_id))

    ctx = _load_unit_context(skill, book, primary)
    validated = _request_validated_items(skill, book, primary, ctx, count)
    return await _persist_draft_questions(db, skill, primary, ctx, validated)
