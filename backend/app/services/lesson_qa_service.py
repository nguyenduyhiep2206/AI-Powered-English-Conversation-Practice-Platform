"""Lesson Q&A session ensure / get / clear + turn SSE orchestration."""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any, Literal

from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.enums import LessonQaMessageRoleEnum, LessonQaSessionStatusEnum
from app.models.learning_skill import LearningSkillDB
from app.models.lesson_qa import LessonQaMessageDB, LessonQaSessionDB
from app.models.profile import UserProfileDB
from app.models.skill_lesson import SkillLessonDB
from app.services.lesson_qa_cache import cache_get, cache_key, cache_set, normalize_query
from app.services.lesson_qa_gates import should_retrieve
from app.services.lesson_qa_prompt import (
    build_qa_system_prompt,
    build_qa_user_payload,
    sources_from_chunks,
)
from app.services.lesson_qa_suggest import build_suggested_prompts
from app.services.lesson_service import get_current_published_lesson_for_user
from app.services.llm_client import chat_stream_text
from app.services.tutor_memory import estimate_tokens, window_transcript
from app.services.tutor_prompt import META_DELIMITER, split_reply_and_meta
from app.services.tutor_rag import (
    format_retrieved_block,
    is_off_topic,
    resolve_unit_scope,
    retrieve_for_session,
)

_TRANSCRIPT_TAIL = 40
_META_HOLD_BACK = len(META_DELIMITER) - 1

RouteName = Literal["off_topic", "rag", "retrieval_empty", "smalltalk"]


async def get_or_create_session(
    db: AsyncSession, user_id: int, skill_id: int
) -> LessonQaSessionDB:
    await _require_skill(db, skill_id)
    existing = await _load_session(db, user_id, skill_id)
    if existing is not None:
        return existing
    return await _insert_session(db, user_id, skill_id)


async def get_qa_bundle(db: AsyncSession, user_id: int, skill_id: int) -> dict[str, Any]:
    skill = await _require_skill(db, skill_id)
    session = await get_or_create_session(db, user_id, skill_id)
    messages = await _load_messages(db, int(session.id))
    prompts = await _build_suggestions(db, user_id, skill)
    return {
        "session": session,
        "messages": messages,
        "suggested_prompts": prompts,
    }


async def clear_messages(db: AsyncSession, user_id: int, skill_id: int) -> None:
    await _require_skill(db, skill_id)
    session = await get_or_create_session(db, user_id, skill_id)
    await _delete_session_messages(db, session)
    await db.commit()


async def iter_qa_turn_sse(
    db: AsyncSession,
    user_id: int,
    skill_id: int,
    content: str,
    *,
    debug: bool = False,
) -> AsyncIterator[tuple[str, dict]]:
    session = await get_or_create_session(db, user_id, skill_id)
    text = _validate_turn_content(content)
    user_msg = await _persist_user(db, session, text)
    await db.commit()
    yield ("user_message", {"id": user_msg.id, "content": user_msg.content})

    try:
        cefr = await _load_cefr(db, user_id)
        skill_title = await _load_skill_title(db, skill_id)
        ctx = await _build_turn_context(db, session, text, skill_id)
        ctx["cefr_level"] = cefr
        system = build_qa_system_prompt(
            cefr_level=cefr,
            skill_title=skill_title,
            retrieved_context=ctx["retrieved_block"],
            force_off_topic=ctx["force_off_topic"],
            force_smalltalk=ctx["route"] == "smalltalk",
        )
        user_payload = build_qa_user_payload(transcript=ctx["transcript"])
        async for event in _stream_llm_and_persist(
            db, session, system=system, user_payload=user_payload, ctx=ctx, debug=debug
        ):
            yield event
    except Exception as exc:
        yield ("error", {"code": "llm_error", "message": str(exc)})


async def _require_skill(db: AsyncSession, skill_id: int) -> LearningSkillDB:
    skill = (
        await db.execute(select(LearningSkillDB).where(LearningSkillDB.id == skill_id))
    ).scalar_one_or_none()
    if skill is None:
        raise ValueError("Skill not found")
    return skill


def _validate_turn_content(content: str) -> str:
    text = (content or "").strip()
    if not text:
        raise ValueError("Message content is required")
    return text


async def _persist_user(
    db: AsyncSession, session: LessonQaSessionDB, content: str
) -> LessonQaMessageDB:
    msg = LessonQaMessageDB(
        session_id=session.id,
        role=LessonQaMessageRoleEnum.user,
        content=content,
        meta=None,
    )
    db.add(msg)
    await db.flush()
    session.message_count = int(session.message_count or 0) + 1
    return msg


async def _load_cefr(db: AsyncSession, user_id: int) -> str:
    profile = (
        await db.execute(select(UserProfileDB).where(UserProfileDB.user_id == user_id))
    ).scalar_one_or_none()
    if profile is not None and profile.current_level is not None:
        return profile.current_level.value
    return "A1"


async def _load_skill_title(db: AsyncSession, skill_id: int) -> str:
    skill = await _require_skill(db, skill_id)
    return str(skill.title or "this lesson")


async def _build_turn_context(
    db: AsyncSession,
    session: LessonQaSessionDB,
    content: str,
    skill_id: int,
) -> dict[str, Any]:
    transcript = await _windowed_transcript(db, int(session.id))
    route, chunks, cache_hit, retrieved_block, force_off_topic = await _resolve_route(
        db, content=content, skill_id=skill_id
    )
    return {
        "transcript": transcript,
        "route": route,
        "chunks": chunks,
        "cache_hit": cache_hit,
        "retrieved_block": retrieved_block,
        "force_off_topic": force_off_topic,
        "sources": sources_from_chunks(chunks),
        "memory_tokens": estimate_tokens(
            "\n".join(f"{m.get('role')}: {m.get('content')}" for m in transcript)
        ),
        "retrieved_tokens": estimate_tokens(retrieved_block or ""),
    }


async def _windowed_transcript(
    db: AsyncSession, session_id: int
) -> list[dict[str, Any]]:
    full_transcript = await _load_transcript(db, session_id)
    return window_transcript(
        full_transcript,
        max_turns=settings.LESSON_QA_MEMORY_MAX_TURNS,
        keep_first_assistant=True,
    )


async def _resolve_route(
    db: AsyncSession, *, content: str, skill_id: int
) -> tuple[RouteName, list[dict[str, Any]], bool, str | None, bool]:
    if is_off_topic(content):
        return "off_topic", [], False, None, True
    if settings.LESSON_QA_RAG_ENABLED and should_retrieve(content):
        chunks, cache_hit = await _retrieve_with_cache(
            db, skill_ids=[int(skill_id)], query=content
        )
        if chunks:
            return "rag", chunks, cache_hit, format_retrieved_block(chunks), False
        return "retrieval_empty", chunks, cache_hit, None, False
    return "smalltalk", [], False, None, False


async def _retrieve_with_cache(
    db: AsyncSession,
    *,
    skill_ids: list[int],
    query: str,
) -> tuple[list[dict[str, Any]], bool]:
    scope = await resolve_unit_scope(db, skill_ids)
    key = cache_key(normalize_query(query), skill_ids, scope=scope)
    hit = await cache_get(key)
    if hit is not None and isinstance(hit.get("chunks"), list):
        return hit["chunks"], True
    chunks = await retrieve_for_session(
        db, skill_ids=skill_ids, query=query, enabled=True
    )
    await cache_set(key, {"chunks": chunks})
    return chunks, False


async def _load_transcript(db: AsyncSession, session_id: int) -> list[dict[str, Any]]:
    rows = (
        await db.execute(
            select(LessonQaMessageDB)
            .where(LessonQaMessageDB.session_id == session_id)
            .order_by(LessonQaMessageDB.id.desc())
            .limit(_TRANSCRIPT_TAIL)
        )
    ).scalars().all()
    rows = list(reversed(rows))
    return [
        {
            "role": r.role.value if hasattr(r.role, "value") else str(r.role),
            "content": r.content,
        }
        for r in rows
    ]


def _stream_safe_delta(accumulated: str, emitted_len: int) -> tuple[str, int]:
    if META_DELIMITER in accumulated:
        visible = accumulated.split(META_DELIMITER, 1)[0]
        new_part = visible[emitted_len:]
        return new_part, len(visible)

    emit_upto = len(accumulated) - _META_HOLD_BACK
    if emit_upto <= emitted_len:
        return "", emitted_len
    return accumulated[emitted_len:emit_upto], emit_upto


async def _stream_llm_and_persist(
    db: AsyncSession,
    session: LessonQaSessionDB,
    *,
    system: str,
    user_payload: str,
    ctx: dict[str, Any],
    debug: bool,
) -> AsyncIterator[tuple[str, dict]]:
    accumulated = ""
    async for event in _stream_tokens(system=system, user_payload=user_payload):
        if event[0] == "token":
            yield event
        else:
            accumulated = event[1]["text"]

    reply, meta = _finalize_reply_meta(accumulated, ctx)
    yield ("meta", meta)

    assistant = await _persist_assistant(db, session, reply=reply, meta=meta)
    yield (
        "assistant_message",
        {"id": assistant.id, "content": assistant.content, "meta": meta},
    )
    if debug:
        yield ("debug", _debug_payload(ctx))
    yield ("done", {"ok": True})


async def _stream_tokens(
    *, system: str, user_payload: str
) -> AsyncIterator[tuple[str, dict]]:
    accumulated = ""
    emitted_len = 0
    async for chunk in chat_stream_text(system=system, user=user_payload):
        accumulated += chunk
        delta, emitted_len = _stream_safe_delta(accumulated, emitted_len)
        if delta:
            yield ("token", {"text": delta})
    if META_DELIMITER not in accumulated:
        remaining = accumulated[emitted_len:]
        if remaining:
            yield ("token", {"text": remaining})
    yield ("_full", {"text": accumulated})


def _finalize_reply_meta(accumulated: str, ctx: dict[str, Any]) -> tuple[str, dict]:
    reply, meta = split_reply_and_meta(accumulated)
    if not isinstance(meta, dict):
        meta = {}
    if ctx["force_off_topic"]:
        meta["off_topic"] = True
    meta["route"] = ctx["route"]
    if ctx["sources"]:
        meta["sources"] = ctx["sources"]
    return reply, meta


async def _persist_assistant(
    db: AsyncSession,
    session: LessonQaSessionDB,
    *,
    reply: str,
    meta: dict,
) -> LessonQaMessageDB:
    assistant = LessonQaMessageDB(
        session_id=session.id,
        role=LessonQaMessageRoleEnum.assistant,
        content=reply,
        meta=meta,
    )
    db.add(assistant)
    await db.flush()
    await db.commit()
    return assistant


def _debug_payload(ctx: dict[str, Any]) -> dict[str, Any]:
    return {
        "route": ctx["route"],
        "cefr": ctx.get("cefr_level"),
        "cache_hit": ctx["cache_hit"],
        "memory_tokens": ctx["memory_tokens"],
        "retrieved_tokens": ctx["retrieved_tokens"],
        "chunk_count": len(ctx["chunks"]),
        "chunks": [
            {
                "score": c.get("score"),
                "unit_title": c.get("unit_title"),
                "book_id": c.get("book_id"),
                "unit_id": c.get("unit_id"),
                "preview": str(c.get("text") or "")[:160],
            }
            for c in ctx["chunks"]
        ],
    }


async def _load_session(
    db: AsyncSession, user_id: int, skill_id: int
) -> LessonQaSessionDB | None:
    return (
        await db.execute(
            select(LessonQaSessionDB).where(
                LessonQaSessionDB.user_id == user_id,
                LessonQaSessionDB.skill_id == skill_id,
            )
        )
    ).scalar_one_or_none()


async def _insert_session(
    db: AsyncSession, user_id: int, skill_id: int
) -> LessonQaSessionDB:
    session = LessonQaSessionDB(
        user_id=user_id,
        skill_id=skill_id,
        status=LessonQaSessionStatusEnum.active,
        message_count=0,
    )
    db.add(session)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        existing = await _load_session(db, user_id, skill_id)
        if existing is None:
            raise
        return existing
    await db.refresh(session)
    return session


async def _load_messages(db: AsyncSession, session_id: int) -> list[LessonQaMessageDB]:
    return list(
        (
            await db.execute(
                select(LessonQaMessageDB)
                .where(LessonQaMessageDB.session_id == session_id)
                .order_by(LessonQaMessageDB.id)
            )
        )
        .scalars()
        .all()
    )


async def _delete_session_messages(
    db: AsyncSession, session: LessonQaSessionDB
) -> None:
    await db.execute(
        delete(LessonQaMessageDB).where(LessonQaMessageDB.session_id == session.id)
    )
    session.message_count = 0


def _target_surfaces(content: dict[str, Any] | None) -> list[str]:
    if not isinstance(content, dict):
        return []
    raw = content.get("targets")
    if not isinstance(raw, list):
        return []
    out: list[str] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        surface = str(item.get("surface") or "").strip()
        if surface:
            out.append(surface)
    return out


async def _build_suggestions(
    db: AsyncSession, user_id: int, skill: LearningSkillDB
) -> list[str]:
    lesson = await get_current_published_lesson_for_user(db, user_id, int(skill.id))
    objective, targets = _lesson_suggest_inputs(lesson)
    return build_suggested_prompts(
        skill_title=str(skill.title or "this lesson"),
        objective=objective,
        targets=targets,
    )


def _lesson_suggest_inputs(
    lesson: SkillLessonDB | None,
) -> tuple[str | None, list[str]]:
    if lesson is None:
        return None, []
    objective = str(lesson.objective or "").strip() or None
    content = lesson.content if isinstance(lesson.content, dict) else {}
    return objective, _target_surfaces(content)
