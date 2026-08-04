"""Orchestrators for AI Tutor text role-play sessions."""

from __future__ import annotations

from collections.abc import AsyncIterator
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.enums import ProgressStatusEnum, TutorMessageRoleEnum, TutorSessionStatusEnum
from app.models.learning_skill import LearningSkillDB
from app.models.profile import UserProfileDB
from app.models.roadmap_step_skill import RoadmapStepSkillDB
from app.models.scenario import RoadmapStepDB, ScenarioDB, UserProgressDB
from app.models.tutor import TutorMessageDB, TutorSessionDB
from app.models.user_skill_mastery import UserSkillMasteryDB
from app.services.llm_client import chat_json, chat_stream_text
from app.services.tutor_prompt import (
    META_DELIMITER,
    build_end_prompts,
    build_turn_system_prompt,
    build_turn_user_payload,
    filter_soft_signals,
    split_reply_and_meta,
)

_TRANSCRIPT_TAIL = 20
_META_HOLD_BACK = len(META_DELIMITER) - 1


async def start_session(
    db: AsyncSession, user_id: int, roadmap_step_id: int
) -> TutorSessionDB:
    await _require_in_progress_progress(db, user_id, roadmap_step_id)
    step, scenario = await _load_step_and_scenario(db, roadmap_step_id)
    skill_ids = await _load_target_skill_ids(db, roadmap_step_id)
    session = await _insert_session(db, user_id, step, scenario, skill_ids)
    await _insert_opener_message(db, session.id, scenario)
    await db.commit()
    await db.refresh(session)
    return session


async def get_session_for_user(
    db: AsyncSession, user_id: int, session_id: int
) -> TutorSessionDB:
    session = await _load_owned_session(db, user_id, session_id)
    return session


async def iter_turn_sse(
    db: AsyncSession,
    user_id: int,
    session_id: int,
    content: str,
) -> AsyncIterator[tuple[str, dict]]:
    session = await _load_owned_session(db, user_id, session_id)
    _require_active_session(session)
    _validate_turn_input(session, content)

    user_msg = await _persist_user_message(db, session_id, content)
    await db.commit()
    yield ("user_message", {"id": user_msg.id, "content": user_msg.content})

    try:
        async for event in _stream_assistant_turn(db, session, content):
            yield event
    except Exception as exc:
        yield ("error", {"code": "llm_error", "message": str(exc)})


async def end_session(db: AsyncSession, user_id: int, session_id: int) -> dict:
    session = await _load_owned_session(db, user_id, session_id)
    _require_active_session(session)
    summary = await _build_end_summary(db, session)
    session.status = TutorSessionStatusEnum.completed
    session.ended_at = datetime.now(timezone.utc)
    session.summary = summary
    await db.commit()
    return summary


async def snapshot_user_mastery(db: AsyncSession, user_id: int) -> list[tuple[int, float, int, int]]:
    rows = (
        await db.execute(
            select(UserSkillMasteryDB).where(UserSkillMasteryDB.user_id == user_id)
        )
    ).scalars().all()
    return [(int(r.skill_id), float(r.mastery), int(r.attempts), int(r.correct)) for r in rows]


async def _require_in_progress_progress(
    db: AsyncSession, user_id: int, roadmap_step_id: int
) -> UserProgressDB:
    progress = (
        await db.execute(
            select(UserProgressDB).where(
                UserProgressDB.user_id == user_id,
                UserProgressDB.roadmap_step_id == roadmap_step_id,
            )
        )
    ).scalar_one_or_none()
    if progress is None:
        raise ValueError("Roadmap step progress not found")
    if progress.status != ProgressStatusEnum.in_progress:
        raise ValueError("Roadmap step must be in_progress to start a tutor session")
    return progress


async def _load_step_and_scenario(
    db: AsyncSession, roadmap_step_id: int
) -> tuple[RoadmapStepDB, ScenarioDB]:
    row = (
        await db.execute(
            select(RoadmapStepDB, ScenarioDB)
            .join(ScenarioDB, ScenarioDB.id == RoadmapStepDB.scenario_id)
            .where(RoadmapStepDB.id == roadmap_step_id)
        )
    ).one_or_none()
    if row is None:
        raise ValueError("Roadmap step not found")
    return row[0], row[1]


async def _load_target_skill_ids(db: AsyncSession, roadmap_step_id: int) -> list[int]:
    rows = (
        await db.execute(
            select(RoadmapStepSkillDB.skill_id)
            .where(RoadmapStepSkillDB.roadmap_step_id == roadmap_step_id)
            .order_by(RoadmapStepSkillDB.id)
            .limit(3)
        )
    ).scalars().all()
    return [int(sid) for sid in rows]


async def _insert_session(
    db: AsyncSession,
    user_id: int,
    step: RoadmapStepDB,
    scenario: ScenarioDB,
    skill_ids: list[int],
) -> TutorSessionDB:
    session = TutorSessionDB(
        user_id=user_id,
        roadmap_step_id=step.id,
        scenario_id=scenario.id,
        status=TutorSessionStatusEnum.active,
        target_skill_ids=skill_ids,
        message_count=0,
    )
    db.add(session)
    await db.flush()
    return session


def _build_opener_content(scenario: ScenarioDB) -> str:
    return (
        f"Hello! I'm the {scenario.ai_role}. You're the {scenario.user_role}. "
        f"Our goal today: {scenario.goal_prompt.strip()}"
    )


async def _insert_opener_message(
    db: AsyncSession, session_id: int, scenario: ScenarioDB
) -> None:
    db.add(
        TutorMessageDB(
            session_id=session_id,
            role=TutorMessageRoleEnum.assistant,
            content=_build_opener_content(scenario),
            meta=None,
        )
    )


async def _load_owned_session(
    db: AsyncSession,
    user_id: int,
    session_id: int,
) -> TutorSessionDB:
    session = (
        await db.execute(select(TutorSessionDB).where(TutorSessionDB.id == session_id))
    ).scalar_one_or_none()
    if session is None:
        raise ValueError("Tutor session not found")
    if int(session.user_id) != int(user_id):
        raise ValueError("Not allowed to access this tutor session")
    return session


def _require_active_session(session: TutorSessionDB) -> None:
    if session.status != TutorSessionStatusEnum.active:
        raise ValueError("Tutor session is not active")


def _validate_turn_input(session: TutorSessionDB, content: str) -> None:
    text = content.strip()
    if not text:
        raise ValueError("Message content is required")
    if len(text) > settings.TUTOR_MAX_MESSAGE_CHARS:
        raise ValueError("Message exceeds maximum length")
    if int(session.message_count) >= settings.TUTOR_MAX_USER_TURNS:
        raise ValueError("Maximum user turns reached for this session")


async def _persist_user_message(
    db: AsyncSession, session_id: int, content: str
) -> TutorMessageDB:
    msg = TutorMessageDB(
        session_id=session_id,
        role=TutorMessageRoleEnum.user,
        content=content.strip(),
        meta=None,
    )
    db.add(msg)
    await db.flush()
    return msg


async def _resolve_cefr_level(db: AsyncSession, user_id: int, scenario: ScenarioDB) -> str:
    profile = (
        await db.execute(select(UserProfileDB).where(UserProfileDB.user_id == user_id))
    ).scalar_one_or_none()
    if profile is not None and profile.current_level is not None:
        return profile.current_level.value
    return scenario.level.value


async def _load_skill_titles(db: AsyncSession, skill_ids: list[int]) -> list[str]:
    if not skill_ids:
        return []
    rows = (
        await db.execute(
            select(LearningSkillDB.id, LearningSkillDB.title).where(
                LearningSkillDB.id.in_(skill_ids)
            )
        )
    ).all()
    by_id = {int(r[0]): r[1] for r in rows}
    return [by_id[sid] for sid in skill_ids if sid in by_id]


async def _load_transcript(db: AsyncSession, session_id: int) -> list[dict[str, Any]]:
    rows = (
        await db.execute(
            select(TutorMessageDB)
            .where(TutorMessageDB.session_id == session_id)
            .order_by(TutorMessageDB.id.desc())
            .limit(_TRANSCRIPT_TAIL)
        )
    ).scalars().all()
    rows = list(reversed(rows))
    return [{"role": r.role.value, "content": r.content} for r in rows]


def _stream_safe_delta(accumulated: str, emitted_len: int) -> tuple[str, int]:
    if META_DELIMITER in accumulated:
        visible = accumulated.split(META_DELIMITER, 1)[0]
        new_part = visible[emitted_len:]
        return new_part, len(visible)

    emit_upto = len(accumulated) - _META_HOLD_BACK
    if emit_upto <= emitted_len:
        return "", emitted_len
    return accumulated[emitted_len:emit_upto], emit_upto


async def _stream_assistant_turn(
    db: AsyncSession,
    session: TutorSessionDB,
    user_message: str,
) -> AsyncIterator[tuple[str, dict]]:
    _step, scenario = await _load_step_and_scenario(db, int(session.roadmap_step_id))
    cefr = await _resolve_cefr_level(db, int(session.user_id), scenario)
    skill_ids = [int(s) for s in (session.target_skill_ids or [])]
    skill_titles = await _load_skill_titles(db, skill_ids)
    transcript = await _load_transcript(db, int(session.id))

    system = build_turn_system_prompt(
        cefr_level=cefr,
        ai_role=scenario.ai_role,
        user_role=scenario.user_role,
        goal_prompt=scenario.goal_prompt,
        suggested_vocab=scenario.suggested_vocab,
        target_skill_titles=skill_titles,
    )
    user_payload = build_turn_user_payload(transcript=transcript, user_message=user_message)

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

    reply, meta = split_reply_and_meta(accumulated)
    yield ("meta", meta)

    assistant = TutorMessageDB(
        session_id=session.id,
        role=TutorMessageRoleEnum.assistant,
        content=reply,
        meta=meta,
    )
    db.add(assistant)
    await db.flush()
    session.message_count = int(session.message_count) + 1
    await db.commit()

    yield (
        "assistant_message",
        {"id": assistant.id, "content": assistant.content, "meta": meta},
    )
    yield ("done", {"ok": True})


async def _build_end_summary(db: AsyncSession, session: TutorSessionDB) -> dict:
    _step, scenario = await _load_step_and_scenario(db, int(session.roadmap_step_id))
    cefr = await _resolve_cefr_level(db, int(session.user_id), scenario)
    skill_ids = [int(s) for s in (session.target_skill_ids or [])]
    skill_titles = await _load_skill_titles(db, skill_ids)
    transcript = await _load_transcript(db, int(session.id))

    system, user = build_end_prompts(
        cefr_level=cefr,
        transcript=transcript,
        target_skill_ids=skill_ids,
        target_skill_titles=skill_titles,
    )
    try:
        raw = chat_json(system, user)
    except Exception:
        raw = {"went_well": [], "fix_next": [], "soft_skill_signals": []}

    if not isinstance(raw, dict):
        raw = {}

    allowed = set(skill_ids)
    signals = filter_soft_signals(raw.get("soft_skill_signals"), allowed)
    return {
        "went_well": [str(x) for x in (raw.get("went_well") or [])][:10],
        "fix_next": [str(x) for x in (raw.get("fix_next") or [])][:10],
        "soft_skill_signals": signals,
    }
