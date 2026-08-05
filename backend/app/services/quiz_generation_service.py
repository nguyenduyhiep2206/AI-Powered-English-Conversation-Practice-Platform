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
from app.models.skill_lesson import SkillLessonDB
from app.services.book_chunk_service import PackMode, get_unit_context
from app.services.cefr_descriptors import (
    blueprint_as_prompt_lines,
    blueprint_for,
    get_can_do,
    passage_length_range,
)
from app.services.llm_client import chat_json
from app.services.skill_drill_align import (
    align_score,
    batch_align_ratio,
    expand_surfaces,
)
from app.services.skill_drill_blueprint import blueprint_for_skill_drill

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
_ALLOWED_SKILL_DRILL_TYPES = {"mcq", "cloze", "fix_grammar"}
_SKILL_DRILL_ALIGN_MIN = 0.8

SKILL_DRILL_SYSTEM_PROMPT = """You are an ESL skill-drill item writer (English→English).
Write practice items that train ONE skill's target forms/words — NOT TOEIC Parts 5–7
unless item_kind is reading_target.

Return JSON: {{"questions":[...]}} with fields per item:
type (mcq|cloze|fix_grammar), item_kind (from blueprint),
stem, options (mcq: exactly 4 strings; cloze: 0–4 optional hints; fix_grammar: []),
answer (exact correct string), explanation (short English),
difficulty (easy|medium|hard), passage (optional short context; usually null),
toeic_part (omit / null).

Item kinds:
- form_choose (mcq): choose the correct form for a blank or short prompt.
- cloze_form (cloze): stem has a blank; answer is the missing word/phrase.
- fix_grammar (fix_grammar): stem is a wrong sentence; answer is the corrected sentence.
- contrast (mcq): choose which form fits (am/is/are, a/an, etc.).
- paraphrase (mcq): meaning/paraphrase of a target.
- reading_target (mcq): short mini-passage OK; still must use a target surface.

Rules:
- Follow the blueprint order: matching type + item_kind for each index.
- Every item MUST use at least one TARGET surface (word-boundary) in stem, answer, or options.
- CEFR {cefr}; skill type {skill_type}; keep language simple.
- No Vietnamese. No unrelated corporate reading trivia.
"""

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


def _fuzzy_window_match(
    needle: str, haystack: str, *, min_ratio: float
) -> bool:
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
    return _fuzzy_window_match(needle, haystack, min_ratio=min_ratio)


def passage_length_ok(passage: str, cefr_level: CEFRLevel | str | None) -> bool:
    """Reject passages wildly outside the CEFR length band (min/2 .. max*2)."""
    if cefr_level is None:
        return True
    min_chars, max_chars = passage_length_range(cefr_level)
    n = len(passage.strip())
    return (min_chars // 2) <= n <= (max_chars * 2)


def _resolve_toeic_part(
    item: dict[str, Any],
    *,
    index: int,
    blueprint: list[dict[str, Any]] | None,
) -> str | None:
    toeic_part = item.get("toeic_part")
    if blueprint is not None and index < len(blueprint):
        toeic_part = toeic_part or blueprint[index].get("toeic_part")
    toeic_part = str(toeic_part).strip() if toeic_part else None
    if toeic_part is not None and toeic_part not in _ALLOWED_TOEIC_PARTS:
        return None
    if blueprint is not None and toeic_part not in _ALLOWED_TOEIC_PARTS:
        return None
    return toeic_part


def _item_requires_passage(
    toeic_part: str | None,
    *,
    index: int,
    blueprint: list[dict[str, Any]] | None,
) -> bool:
    if toeic_part in {"r6", "r7"}:
        return True
    if blueprint is None or toeic_part is not None:
        return False
    if index < len(blueprint):
        return bool(blueprint[index].get("requires_passage"))
    return any(bool(b.get("requires_passage")) for b in blueprint)


def _passage_passes_checks(
    passage: str,
    *,
    excerpt: str | None,
    cefr_level: CEFRLevel | str | None,
) -> bool:
    if not passage or excerpt is None:
        return False
    if not passage_grounded(passage, excerpt):
        return False
    return passage_length_ok(passage, cefr_level)


def _normalize_generated_item(
    item: dict[str, Any],
    *,
    index: int,
    excerpt: str | None,
    blueprint: list[dict[str, Any]] | None,
    cefr_level: CEFRLevel | str | None,
) -> dict[str, Any] | None:
    qtype = item.get("type")
    if qtype in _LEGACY_REJECTED_TYPES:
        return None
    stem = (item.get("stem") or "").strip()
    answer = str(item.get("answer") or "").strip()
    if not stem or not answer or qtype not in _ALLOWED_READING_TYPES:
        return None

    toeic_part = _resolve_toeic_part(item, index=index, blueprint=blueprint)
    if blueprint is not None and toeic_part not in _ALLOWED_TOEIC_PARTS:
        return None

    options = item.get("options")
    if not isinstance(options, list) or len(options) != 4:
        return None
    if answer not in options:
        return None

    passage_raw = item.get("passage")
    passage = (passage_raw or "").strip() if isinstance(passage_raw, str) else ""
    requires_passage = _item_requires_passage(
        toeic_part, index=index, blueprint=blueprint
    )

    if requires_passage:
        if not _passage_passes_checks(passage, excerpt=excerpt, cefr_level=cefr_level):
            return None
    elif toeic_part == "r5":
        if "-------" not in stem:
            return None
        passage = ""
    elif passage and excerpt is not None:
        if not passage_grounded(passage, excerpt):
            return None
        if cefr_level is not None and not passage_length_ok(passage, cefr_level):
            return None

    return {
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
        normalized = _normalize_generated_item(
            item,
            index=index,
            excerpt=excerpt,
            blueprint=blueprint,
            cefr_level=cefr_level,
        )
        if normalized is not None:
            valid.append(normalized)
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


def _build_quiz_user_prompt(
    skill: LearningSkillDB,
    book: BookDB,
    primary: BookSkillSourceDB,
    ctx: dict[str, Any],
    count: int,
    blueprint: list[dict[str, Any]],
) -> str:
    cefr = skill.cefr_level
    skill_type = skill.skill_type or SkillTypeEnum.grammar
    book_type = book.book_type or BookTypeEnum.freeform
    return build_generation_prompt(
        primary.unit_title or skill.title,
        cefr.value if hasattr(cefr, "value") else str(cefr),
        ctx["text"],
        count,
        can_do=get_can_do(cefr, skill_type),
        blueprint=blueprint,
        skill_type=skill_type.value if hasattr(skill_type, "value") else str(skill_type),
        book_type=book_type.value if hasattr(book_type, "value") else str(book_type),
    )


def _validate_llm_payload(
    payload: Any,
    *,
    excerpt: str,
    blueprint: list[dict[str, Any]],
    cefr_level: CEFRLevel | str | None,
) -> list[dict[str, Any]]:
    raw_questions = payload.get("questions") if isinstance(payload, dict) else payload
    if not isinstance(raw_questions, list):
        return []
    return validate_generated_questions(
        raw_questions,
        excerpt=excerpt,
        blueprint=blueprint,
        cefr_level=cefr_level,
    )


def _best_validated_from_llm(
    user_prompt: str,
    *,
    excerpt: str,
    blueprint: list[dict[str, Any]],
    cefr_level: CEFRLevel | str | None,
    count: int,
) -> list[dict[str, Any]]:
    best: list[dict[str, Any]] = []
    for attempt in range(2):
        prompt = user_prompt
        if attempt > 0:
            prompt += (
                f"\nRETRY: previous attempt kept only {len(best)}/{count} valid items. "
                "Return exactly the full set. For every r6/r7 item include a passage that "
                "reuses topic words from the EXCERPT. Every r5 stem must contain ------- .\n"
            )
        validated = _validate_llm_payload(
            chat_json(SYSTEM_PROMPT, prompt),
            excerpt=excerpt,
            blueprint=blueprint,
            cefr_level=cefr_level,
        )
        if len(validated) > len(best):
            best = validated
        if len(best) >= count:
            break
    return best


def _require_enough_items(best: list[dict[str, Any]], count: int) -> list[dict[str, Any]]:
    if not best:
        raise ValueError("No valid questions after validation.")
    if len(best) < max(2, count // 2):
        raise ValueError(
            f"Only {len(best)}/{count} questions passed validation "
            "(passages must reuse EXCERPT vocabulary; r5 needs -------). Try again."
        )
    return best[:count]


def _request_validated_items(
    skill: LearningSkillDB,
    book: BookDB,
    primary: BookSkillSourceDB,
    ctx: dict[str, Any],
    count: int,
) -> list[dict[str, Any]]:
    """Build the CEFR-aware prompt, call the LLM, and keep only grounded items."""
    skill_type = skill.skill_type or SkillTypeEnum.grammar
    book_type = book.book_type or BookTypeEnum.freeform
    blueprint = blueprint_for(book_type, skill_type, count)
    user_prompt = _build_quiz_user_prompt(skill, book, primary, ctx, count, blueprint)
    best = _best_validated_from_llm(
        user_prompt,
        excerpt=ctx["text"],
        blueprint=blueprint,
        cefr_level=skill.cefr_level,
        count=count,
    )
    return _require_enough_items(best, count)


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
    options = item.get("options")
    if options is None:
        options = []
    return QuizQuestionDB(
        skill_id=skill.id,
        book_id=primary.book_id,
        unit_id=primary.unit_id,
        question_type=QuizQuestionTypeEnum(item["type"]),
        stem=item["stem"],
        passage=item.get("passage"),
        passage_id=passage_id,
        toeic_part=toeic_part,
        options=options,
        answer=item["answer"],
        explanation=item.get("explanation"),
        cefr_level=skill.cefr_level,
        difficulty=item["difficulty"],
        status=QuizQuestionStatusEnum.draft,
        generation_batch_id=batch_id,
        source_chunk_ids=ctx.get("chunk_ids"),
        task_brief=item.get("task_brief"),
    )


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


def _form_row_surfaces(row: dict[str, Any]) -> set[str]:
    """Prefer form examples; keep short form tokens only (skip prose explanations)."""
    out: set[str] = set()
    example = str(row.get("example") or "").strip()
    if example:
        out.add(example)
    pattern = str(row.get("pattern") or "").strip()
    # Keep "am / is" style tokens; drop "Before consonant sounds".
    words = pattern.split()
    if pattern and (("/" in pattern and len(words) <= 5) or len(words) == 1):
        out.add(pattern)
    return out


def surfaces_from_lesson_content(content: dict[str, Any] | None) -> set[str]:
    """Collect target surfaces + usable form tokens from a lesson content object."""
    if not isinstance(content, dict):
        return set()
    out: set[str] = set()
    for t in content.get("targets") or []:
        if isinstance(t, dict):
            s = str(t.get("surface") or "").strip()
            if s:
                out.add(s)
    form = content.get("form")
    if isinstance(form, dict):
        for row in form.get("rows") or []:
            if isinstance(row, dict):
                out |= _form_row_surfaces(row)
    return expand_surfaces(out)


def surfaces_from_lessons(lessons: list[dict[str, Any]] | list[Any]) -> set[str]:
    """Union surfaces across LessonPack items (dict with content or ORM-like)."""
    out: set[str] = set()
    for lesson in lessons:
        content = None
        if isinstance(lesson, dict):
            content = lesson.get("content")
        else:
            content = getattr(lesson, "content", None)
        out |= surfaces_from_lesson_content(
            content if isinstance(content, dict) else None
        )
    return expand_surfaces(out)


def heuristic_surfaces_from_skill(skill: LearningSkillDB) -> set[str]:
    """Fallback surfaces when no published lesson (non-grammar)."""
    title = str(skill.title or "").strip()
    parts = [p for p in re.split(r"[\s/|,;:]+", title) if len(p) >= 2]
    return set(parts[:8]) if parts else {title} if title else set()


async def _load_published_lessons(
    db: AsyncSession, skill_id: int
) -> list[SkillLessonDB]:
    return list(
        (
            await db.execute(
                select(SkillLessonDB)
                .where(
                    SkillLessonDB.skill_id == skill_id,
                    SkillLessonDB.status == "published",
                )
                .order_by(SkillLessonDB.pack_index.asc())
            )
        )
        .scalars()
        .all()
    )


async def _load_published_lesson(
    db: AsyncSession, skill_id: int
) -> SkillLessonDB | None:
    rows = await _load_published_lessons(db, skill_id)
    return rows[0] if rows else None


def validate_skill_drill_questions(
    items: list[dict[str, Any]],
    *,
    blueprint: list[dict[str, Any]],
    surfaces: set[str],
    alignment: str,
) -> list[dict[str, Any]]:
    """Validate LLM skill-drill items (mcq/cloze/fix_grammar)."""
    valid: list[dict[str, Any]] = []
    for index, item in enumerate(items):
        if not isinstance(item, dict):
            continue
        qtype = str(item.get("type") or "").strip().lower()
        if qtype not in _ALLOWED_SKILL_DRILL_TYPES:
            continue
        stem = str(item.get("stem") or "").strip()
        answer = str(item.get("answer") or "").strip()
        if not stem or not answer:
            continue

        expected_type = None
        expected_kind = None
        if index < len(blueprint):
            expected_type = blueprint[index].get("question_type")
            expected_kind = blueprint[index].get("item_kind")
            if expected_type and qtype != expected_type:
                # Allow LLM type if still in allowed set and kind matches loosely
                if qtype not in _ALLOWED_SKILL_DRILL_TYPES:
                    continue

        item_kind = str(item.get("item_kind") or expected_kind or "form_choose").strip()

        options_raw = item.get("options")
        options: list[str] = []
        if isinstance(options_raw, list):
            options = [str(o).strip() for o in options_raw if str(o).strip()]

        if qtype == "mcq":
            if len(options) < 2:
                continue
            if answer not in options:
                continue
            if len(options) > 4:
                options = options[:4]
            # Pad to 4 if needed is not required for skill_drill; keep as-is if >=2
        elif qtype in {"cloze", "fix_grammar"}:
            # options optional
            pass

        difficulty = str(item.get("difficulty") or "medium").strip() or "medium"
        passage_raw = item.get("passage")
        passage = (
            (passage_raw or "").strip() if isinstance(passage_raw, str) else None
        ) or None

        normalized = {
            "type": qtype,
            "toeic_part": None,
            "stem": stem,
            "passage": passage,
            "passage_group": None,
            "options": options,
            "answer": answer,
            "explanation": item.get("explanation"),
            "skill": item.get("skill") or "grammar",
            "difficulty": difficulty,
            "cefr_focus": item.get("cefr_focus"),
            "item_kind": item_kind,
            "task_brief": {
                "mode": "skill_drill",
                "item_kind": item_kind,
                "alignment": alignment,
                "surfaces": sorted(surfaces),
            },
        }
        valid.append(normalized)
    return valid


def _build_skill_drill_user_prompt(
    skill: LearningSkillDB,
    ctx: dict[str, Any],
    count: int,
    blueprint: list[dict[str, Any]],
    surfaces: set[str],
) -> str:
    cefr = skill.cefr_level
    cefr_s = cefr.value if hasattr(cefr, "value") else str(cefr)
    st = skill.skill_type or SkillTypeEnum.grammar
    st_s = st.value if hasattr(st, "value") else str(st)
    lines = [
        f"Skill title: {skill.title}",
        f"CEFR: {cefr_s}",
        f"Skill type: {st_s}",
        f"TARGETS (must appear in items): {', '.join(sorted(surfaces))}",
        f"Generate exactly {count} questions matching this blueprint:",
    ]
    for i, b in enumerate(blueprint, start=1):
        lines.append(
            f"{i}. item_kind={b['item_kind']} type={b['question_type']}"
        )
    lines.append(f"\nEXCERPT (optional grounding):\n{ctx.get('text') or '(none)'}\n")
    return "\n".join(lines)


def _request_skill_drill_items(
    skill: LearningSkillDB,
    ctx: dict[str, Any],
    count: int,
    surfaces: set[str],
    alignment: str,
) -> list[dict[str, Any]]:
    skill_type = skill.skill_type or SkillTypeEnum.grammar
    st_s = (
        skill_type.value if hasattr(skill_type, "value") else str(skill_type)
    )
    cefr = skill.cefr_level
    cefr_s = cefr.value if hasattr(cefr, "value") else str(cefr or "A1")
    blueprint = blueprint_for_skill_drill(st_s, count)
    system = SKILL_DRILL_SYSTEM_PROMPT.format(cefr=cefr_s, skill_type=st_s)
    user_prompt = _build_skill_drill_user_prompt(
        skill, ctx, count, blueprint, surfaces
    )

    best: list[dict[str, Any]] = []
    last_ratio = 0.0
    for attempt in range(2):
        prompt = user_prompt
        if attempt > 0:
            prompt += (
                f"\nRETRY: previous alignment ratio was {last_ratio:.2f} "
                f"(need ≥ {_SKILL_DRILL_ALIGN_MIN}). "
                "Every item must include a TARGET as a whole word in stem/answer/options.\n"
            )
        payload = chat_json(system, prompt)
        raw = payload.get("questions") if isinstance(payload, dict) else payload
        if not isinstance(raw, list):
            raw = []
        validated = validate_skill_drill_questions(
            raw,
            blueprint=blueprint,
            surfaces=surfaces,
            alignment=alignment,
        )
        if surfaces:
            last_ratio = batch_align_ratio(validated, surfaces)
            if last_ratio < _SKILL_DRILL_ALIGN_MIN:
                if attempt == 0:
                    continue
                raise ValueError(
                    f"Skill-drill alignment too low ({last_ratio:.2f} < "
                    f"{_SKILL_DRILL_ALIGN_MIN}). Regenerate or fix lesson targets."
                )
        if len(validated) > len(best):
            best = validated
        if len(best) >= count:
            break

    if not best:
        raise ValueError("No valid skill-drill questions after validation.")
    if len(best) < max(2, count // 2):
        raise ValueError(
            f"Only {len(best)}/{count} skill-drill questions passed validation."
        )
    return best[:count]


async def generate_quiz_for_skill(
    db: AsyncSession,
    skill_id: int,
    count: int = 10,
    mode: str = "skill_drill",
) -> list[QuizQuestionDB]:
    """Generate quiz drafts. Default mode=skill_drill; use mode=toeic for TOEIC RC."""
    skill = await _require_skill(db, skill_id)
    primary = await _resolve_primary_source(db, skill_id)
    book = await _require_source_book(db, int(primary.book_id))
    ctx = _load_unit_context(skill, book, primary)

    mode_norm = (mode or "skill_drill").strip().lower()
    if mode_norm == "toeic":
        validated = _request_validated_items(skill, book, primary, ctx, count)
        return await _persist_draft_questions(db, skill, primary, ctx, validated)

    skill_type = skill.skill_type or SkillTypeEnum.grammar
    st_s = skill_type.value if hasattr(skill_type, "value") else str(skill_type)
    lessons = await _load_published_lessons(db, skill_id)
    surfaces = surfaces_from_lessons(lessons)
    alignment = "lesson"
    if not surfaces:
        if st_s == "grammar":
            raise ValueError(
                "Grammar skill_drill requires a published lesson with targets/form."
            )
        surfaces = heuristic_surfaces_from_skill(skill)
        alignment = "heuristic"
        if not surfaces:
            raise ValueError("No target surfaces available for skill_drill.")

    validated = _request_skill_drill_items(
        skill, ctx, count, surfaces, alignment
    )
    return await _persist_draft_questions(db, skill, primary, ctx, validated)


def should_skip_skill_drill_publish(row: QuizQuestionDB) -> bool:
    """True if skill_drill row fails alignment against its stored surfaces."""
    brief = row.task_brief if isinstance(row.task_brief, dict) else None
    if not brief or brief.get("mode") != "skill_drill":
        return False
    surfaces_raw = brief.get("surfaces") or []
    surfaces = {str(s).strip() for s in surfaces_raw if str(s).strip()}
    if not surfaces:
        return False
    item = {
        "stem": row.stem or "",
        "passage": row.passage or "",
        "answer": row.answer or "",
        "options": row.options if isinstance(row.options, list) else [],
    }
    return not align_score(item, surfaces)
