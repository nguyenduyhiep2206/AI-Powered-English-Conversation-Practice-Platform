"""Offline generate skill lesson mini-units (text only) → draft / publish."""

from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.book import BookDB
from app.models.book_skill_source import BookSkillSourceDB
from app.models.learning_skill import LearningSkillDB
from app.models.skill_lesson import SkillLessonDB
from app.services.book_chunk_service import get_unit_context
from app.services.lesson_content_validate import (
    assert_publishable,
    normalize_content,
    target_bounds,
)
from app.services.llm_client import chat_json

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
  "hook": "optional 1 short English sentence that frames why this skill matters",
  "passage": {{
    "text": "English paragraph 40-100 words at {cefr}",
    "gloss": "optional short English context tip at {cefr}"
  }},
  "form": {{
    "title": "optional short English title for the pattern table",
    "rows": [
      {{
        "label": "who/when (e.g. I / he/she)",
        "pattern": "the form itself (e.g. am / is)",
        "example": "one short English example sentence"
      }}
    ]
  }},
  "targets": [
    {{
      "surface": "English word/phrase that APPEARS in the passage",
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
  "exit_check": {{
      "type": "mcq" or "cloze",
      "prompt": "optional final English check after writing",
      "options": ["..."],
      "answer": "exact correct string"
  }},
  "writing": {{
    "prompt": "English instruction asking the learner to write in English",
    "min_words": 15,
    "must_use": ["subset of target surfaces"]
  }}
}}
Rules:
- Exactly {min_targets}-{max_targets} targets that APPEAR in the passage (prefer {prefer_targets}).
- Exactly 1-2 checks testing those targets (meaning, form, or usage) in English.
- For mcq meaning checks: options must be English paraphrases/definitions, never translations.
- Tense / aspect checks MUST put the time/context IN the prompt (not only in the answer key).
  If the answer is past / past continuous / future, include a clear marker such as yesterday,
  last night, ago, at 8pm, when I arrived, tomorrow, next week, right now, at the moment.
  Bad: "They ____ (listen) to music." → answer "were listening" (no past context).
  Good: "Yesterday at 8pm, they ____ (listen) to music." → "were listening".
  Do not force past answers on timeless stems; match stem context to the expected tense.
- Passage English at {cefr}; 40-100 words; ground in book excerpt when provided.
- Do not invent long plots; keep language-teaching focus.
- writing.must_use must be 1-3 items from targets.
- For grammar skills: form is REQUIRED with 2-8 rows (label/pattern/example).
- hook and exit_check are optional but preferred when they fit.
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
- Passage (40-100 words) must showcase the target grammar naturally several times.
- form.rows MUST explain the pattern in simple English (2-8 rows: label / pattern / example).
- Targets include form words + example phrases; gloss explains the form in simple English.
- Checks test the grammar choice directly (English prompts/options).
- Every check prompt must make the intended time clear when testing tense/aspect
  (past / present / continuous / future). Never ask for "were listening" without a past cue.
""",
    "vocabulary": """
Focus: {min_targets}-{max_targets} concrete words or collocations.
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
    min_t, max_t = target_bounds()
    prefer = min(max_t, max(min_t, (min_t + max_t) // 2))
    guidance = SKILL_TYPE_GUIDANCE.get(skill_type, SKILL_TYPE_GUIDANCE["functional"])
    return (
        BASE_SYSTEM_PROMPT.format(
            cefr=cefr,
            min_targets=min_t,
            max_targets=max_t,
            prefer_targets=prefer,
        )
        + "\n"
        + guidance.format(min_targets=min_t, max_targets=max_t)
    )


async def _require_skill(db: AsyncSession, skill_id: int) -> LearningSkillDB:
    skill = (
        await db.execute(select(LearningSkillDB).where(LearningSkillDB.id == skill_id))
    ).scalar_one_or_none()
    if skill is None:
        raise ValueError("Skill not found")
    return skill


def _skill_type_cefr(skill: LearningSkillDB) -> tuple[str, str]:
    skill_type = (
        skill.skill_type.value
        if hasattr(skill.skill_type, "value")
        else str(skill.skill_type)
    )
    cefr = (
        skill.cefr_level.value
        if hasattr(skill.cefr_level, "value")
        else str(skill.cefr_level)
    )
    return skill_type, cefr


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


async def _load_excerpt_context(
    db: AsyncSession, skill: LearningSkillDB
) -> tuple[str, int | None]:
    primary = await _resolve_primary_source(db, int(skill.id))
    if primary is None:
        return "", None
    book = (
        await db.execute(select(BookDB).where(BookDB.id == primary.book_id))
    ).scalar_one_or_none()
    if book is None:
        return "", None
    return _load_excerpt(skill, book, primary), int(primary.id)


def _author_user_prompt(
    *, skill: LearningSkillDB, skill_type: str, cefr: str, excerpt: str
) -> str:
    return (
        f"Skill title: {skill.title}\n"
        f"Skill type: {skill_type}\n"
        f"CEFR: {cefr}\n"
        f"Book excerpt (may be empty):\n{excerpt[:3500] or '(none)'}\n"
    )


def _ensure_writing_object(raw: dict[str, Any]) -> None:
    if isinstance(raw.get("writing"), dict):
        return
    surfaces: list[str] = []
    for t in raw.get("targets") or []:
        if isinstance(t, dict):
            s = str(t.get("surface") or "").strip()
            if s:
                surfaces.append(s)
    raw["writing"] = {
        "prompt": (
            f"Write 2–3 short sentences using "
            f"{', '.join(surfaces[:3]) or 'the targets'}."
        ),
        "min_words": 12,
        "must_use": surfaces[:2] or [],
    }


def _unwrap_lesson_raw(payload: dict[str, Any]) -> dict[str, Any]:
    if isinstance(payload.get("content"), dict) and "passage" in payload["content"]:
        return dict(payload["content"])
    if "passage" in payload:
        return dict(payload)
    raise RuntimeError("LLM lesson missing passage/content")


def content_and_meta_from_llm_payload(
    payload: Any, *, skill_title: str
) -> tuple[dict[str, Any], str, str]:
    """Parse LLM JSON → validated content + title/objective. Raises ValueError/RuntimeError."""
    if not isinstance(payload, dict):
        raise RuntimeError("LLM did not return a lesson object")
    raw = _unwrap_lesson_raw(payload)
    _ensure_writing_object(raw)
    content = normalize_content(raw)
    title = str(payload.get("title") or skill_title).strip() or skill_title
    objective = str(payload.get("objective") or f"Practice: {skill_title}").strip()
    return content, title, objective


def _llm_validated_single(
    *,
    system: str,
    user: str,
    skill_title: str,
    retry_hint: str,
) -> tuple[dict[str, Any], str, str]:
    payload = chat_json(system, user)
    try:
        return content_and_meta_from_llm_payload(payload, skill_title=skill_title)
    except ValueError as first_err:
        retry_user = user + "\nRETRY: previous draft failed validation: " + str(first_err) + retry_hint
        payload = chat_json(system, retry_user)
        return content_and_meta_from_llm_payload(payload, skill_title=skill_title)


def _apply_draft_fields(
    row: SkillLessonDB,
    *,
    title: str,
    objective: str,
    content: dict[str, Any],
    book_source_id: int | None,
) -> None:
    row.title = title
    row.objective = objective
    row.content = content
    row.source = "llm_reviewed"
    row.status = "draft"
    row.book_source_id = book_source_id


async def _get_or_create_pack_row(
    db: AsyncSession, skill_id: int, pack_index: int
) -> SkillLessonDB:
    existing = (
        await db.execute(
            select(SkillLessonDB).where(
                SkillLessonDB.skill_id == skill_id,
                SkillLessonDB.pack_index == pack_index,
            )
        )
    ).scalar_one_or_none()
    if existing is None:
        existing = SkillLessonDB(skill_id=skill_id, pack_index=pack_index)
        db.add(existing)
    return existing


async def generate_lesson_draft(db: AsyncSession, skill_id: int) -> SkillLessonDB:
    skill = await _require_skill(db, skill_id)
    skill_type, cefr = _skill_type_cefr(skill)
    excerpt, book_source_id = await _load_excerpt_context(db, skill)
    user = _author_user_prompt(
        skill=skill, skill_type=skill_type, cefr=cefr, excerpt=excerpt
    )
    content, title, objective = _llm_validated_single(
        system=_build_system_prompt(skill_type=skill_type, cefr=cefr),
        user=user,
        skill_title=skill.title,
        retry_hint=(
            "\nEvery target.surface must appear EXACTLY in passage.text "
            "(same words; ASCII apostrophe ' is fine).\n"
        ),
    )
    row = await _get_or_create_pack_row(db, skill_id, 0)
    _apply_draft_fields(
        row,
        title=title,
        objective=objective,
        content=content,
        book_source_id=book_source_id,
    )
    await db.commit()
    await db.refresh(row)
    return row


async def _load_pack_index_zero(db: AsyncSession, skill_id: int) -> SkillLessonDB:
    lesson = (
        await db.execute(
            select(SkillLessonDB).where(
                SkillLessonDB.skill_id == skill_id,
                SkillLessonDB.pack_index == 0,
            )
        )
    ).scalar_one_or_none()
    if lesson is None:
        raise ValueError("Lesson not found")
    return lesson


async def publish_lesson(db: AsyncSession, skill_id: int) -> SkillLessonDB:
    lesson = await _load_pack_index_zero(db, skill_id)
    skill = await _require_skill(db, skill_id)
    skill_type, _ = _skill_type_cefr(skill)
    assert_publishable(
        lesson.content if isinstance(lesson.content, dict) else {},
        skill_type=skill_type,
    )
    lesson.status = "published"
    await db.commit()
    await db.refresh(lesson)
    return lesson


def assert_pack_publishable(*, indices_ready: set[int], required: int = 3) -> None:
    need = set(range(required))
    if not need.issubset(indices_ready):
        missing = sorted(need - indices_ready)
        raise ValueError(f"LessonPack incomplete; missing pack_index={missing}")


PACK_ROLE_HINTS = (
    "L1 focus: short situation + notice passage; light targets; optional form.",
    "L2 focus: clear form table + controlled checks; grammar form REQUIRED if grammar skill.",
    "L3 focus: meaning/targets + guided writing with must_use from targets.",
)


def _pack_system_prompt(*, skill_type: str, cefr: str, count: int = 3) -> str:
    min_t, max_t = target_bounds()
    prefer_t = min(max_t, max(min_t, (min_t + max_t) // 2))
    roles = "\n".join(
        f"- lessons[{i}]: {PACK_ROLE_HINTS[i] if i < len(PACK_ROLE_HINTS) else 'continue teaching the same skill'}"
        for i in range(count)
    )
    return f"""You are an ESL author writing a LessonPack of {count} micro-lessons for ONE skill.
Teach in English only (English→English). Do NOT use Vietnamese.

Learner CEFR: {cefr}
Skill type guidance:
{SKILL_TYPE_GUIDANCE.get(skill_type, SKILL_TYPE_GUIDANCE["grammar"])}

Return JSON only:
{{
  "lessons": [
    {{
      "title": string,
      "objective": string,
      "hook": optional string,
      "passage": {{ "text": "...", "gloss": "optional" }},
      "form": {{ "title": "...", "rows": [{{ "label": "...", "pattern": "...", "example": "..." }}] }},
      "targets": [{{ "surface": "...", "gloss": "...", "note": "optional" }}],
      "checks": [{{ "type": "mcq"|"cloze", "prompt": "...", "options": [], "answer": "..." }}],
      "exit_check": optional,
      "writing": {{ "prompt": "...", "min_words": 12, "must_use": [] }}
    }}
  ]
}}
Rules:
- Exactly {count} items in lessons, in order L1..L{count}.
{roles}
- Each lesson: {min_t}-{max_t} targets (prefer {prefer_t}) that APPEAR in that lesson's passage.
- Each lesson: 1-2 checks. For grammar skills: L2 MUST include form with 2-8 rows; L1/L3 form optional.
- Keep passages 40-100 words at {cefr}. Share the same skill focus across the pack.
- Each lesson MUST include writing as an object with prompt, min_words, must_use (1-3 target surfaces).
"""


def _extract_lessons_raw(payload: Any, *, count: int, err: str) -> list[Any]:
    lessons_raw = payload.get("lessons") if isinstance(payload, dict) else None
    if not isinstance(lessons_raw, list) or len(lessons_raw) < count:
        raise ValueError(err)
    return lessons_raw


def _parse_pack_items(
    lessons_raw: list[Any], *, skill_title: str, count: int
) -> list[tuple[dict[str, Any], str, str]]:
    parsed: list[tuple[dict[str, Any], str, str]] = []
    for index in range(count):
        item = lessons_raw[index]
        if not isinstance(item, dict):
            raise ValueError(f"LessonPack item {index} invalid")
        parsed.append(
            content_and_meta_from_llm_payload(
                item, skill_title=f"{skill_title} ({index + 1}/{count})"
            )
        )
    return parsed


def _llm_validated_pack(
    *,
    system: str,
    user: str,
    skill_title: str,
    count: int,
) -> list[tuple[dict[str, Any], str, str]]:
    payload = chat_json(system, user)
    try:
        lessons_raw = _extract_lessons_raw(
            payload, count=count, err="LLM did not return enough lessons for LessonPack"
        )
        return _parse_pack_items(lessons_raw, skill_title=skill_title, count=count)
    except (ValueError, RuntimeError) as first_err:
        retry_user = (
            user
            + "\nRETRY: previous LessonPack failed validation: "
            + str(first_err)
            + "\nEach lesson needs passage, targets in passage, checks, and writing object.\n"
        )
        payload = chat_json(system, retry_user)
        lessons_raw = _extract_lessons_raw(
            payload,
            count=count,
            err="LLM did not return enough lessons for LessonPack retry",
        )
        return _parse_pack_items(lessons_raw, skill_title=skill_title, count=count)


async def _persist_pack_drafts(
    db: AsyncSession,
    skill_id: int,
    parsed: list[tuple[dict[str, Any], str, str]],
    book_source_id: int | None,
) -> list[SkillLessonDB]:
    out: list[SkillLessonDB] = []
    for index, (content, title, objective) in enumerate(parsed):
        row = await _get_or_create_pack_row(db, skill_id, index)
        _apply_draft_fields(
            row,
            title=title,
            objective=objective,
            content=content,
            book_source_id=book_source_id,
        )
        out.append(row)
    await db.commit()
    for row in out:
        await db.refresh(row)
    return out


async def generate_lesson_pack(
    db: AsyncSession, skill_id: int, *, count: int = 3
) -> list[SkillLessonDB]:
    if count < 1 or count > 5:
        raise ValueError("LessonPack count must be 1..5")
    skill = await _require_skill(db, skill_id)
    skill_type, cefr = _skill_type_cefr(skill)
    excerpt, book_source_id = await _load_excerpt_context(db, skill)
    user = _author_user_prompt(
        skill=skill, skill_type=skill_type, cefr=cefr, excerpt=excerpt
    )
    parsed = _llm_validated_pack(
        system=_pack_system_prompt(skill_type=skill_type, cefr=cefr, count=count),
        user=user,
        skill_title=skill.title,
        count=count,
    )
    return await _persist_pack_drafts(db, skill_id, parsed, book_source_id)


async def _load_all_pack_rows(db: AsyncSession, skill_id: int) -> list[SkillLessonDB]:
    return list(
        (
            await db.execute(
                select(SkillLessonDB)
                .where(SkillLessonDB.skill_id == skill_id)
                .order_by(SkillLessonDB.pack_index.asc())
            )
        )
        .scalars()
        .all()
    )


def _publish_pack_rows(
    rows_by_index: dict[int, SkillLessonDB],
    *,
    skill_type: str,
    required: int,
) -> list[SkillLessonDB]:
    published: list[SkillLessonDB] = []
    for index in range(required):
        lesson = rows_by_index[index]
        # Grammar form is required on L2 only (pack_index=1); L1/L3 may omit.
        require_form = skill_type == "grammar" and (index == 1 or required == 1)
        assert_publishable(
            lesson.content if isinstance(lesson.content, dict) else {},
            skill_type=skill_type,
            require_grammar_form=require_form,
        )
        lesson.status = "published"
        published.append(lesson)
    return published


async def publish_lesson_pack(
    db: AsyncSession, skill_id: int, *, required: int = 3
) -> list[SkillLessonDB]:
    rows = await _load_all_pack_rows(db, skill_id)
    by_index = {int(r.pack_index or 0): r for r in rows}
    assert_pack_publishable(indices_ready=set(by_index.keys()), required=required)
    skill = await _require_skill(db, skill_id)
    skill_type, _ = _skill_type_cefr(skill)
    published = _publish_pack_rows(by_index, skill_type=skill_type, required=required)
    await db.commit()
    for row in published:
        await db.refresh(row)
    return published


def lesson_to_dict(lesson: SkillLessonDB) -> dict[str, Any]:
    return {
        "id": int(lesson.id),
        "skill_id": int(lesson.skill_id),
        "pack_index": int(lesson.pack_index or 0),
        "title": lesson.title,
        "objective": lesson.objective,
        "content": lesson.content,
        "source": lesson.source,
        "status": lesson.status,
        "book_source_id": int(lesson.book_source_id) if lesson.book_source_id else None,
    }
