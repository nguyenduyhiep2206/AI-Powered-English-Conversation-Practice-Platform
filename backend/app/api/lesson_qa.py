"""Learner API for Lesson Q&A under a skill lesson."""

from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_active_user
from app.core.database import get_db
from app.models.lesson_qa import LessonQaMessageDB, LessonQaSessionDB
from app.models.user import UserDB
from app.schemas.lesson_qa_schema import (
    LessonQaBundleDTO,
    LessonQaMessageDTO,
    LessonQaSessionDTO,
    LessonQaTurnRequest,
)
from app.services.lesson_qa_service import (
    clear_messages,
    get_qa_bundle,
    iter_qa_turn_sse,
)

router = APIRouter()


def _sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


def _map_qa_error(exc: ValueError) -> HTTPException:
    msg = str(exc)
    if msg == "Skill not found":
        return HTTPException(status_code=404, detail=msg)
    return HTTPException(status_code=400, detail=msg)


def _enum_str(value: object) -> str:
    return value.value if hasattr(value, "value") else str(value)


def _session_to_dto(session: LessonQaSessionDB) -> LessonQaSessionDTO:
    return LessonQaSessionDTO(
        id=int(session.id),
        skill_id=int(session.skill_id),
        status=_enum_str(session.status),
        message_count=int(session.message_count or 0),
    )


def _message_to_dto(message: LessonQaMessageDB) -> LessonQaMessageDTO:
    return LessonQaMessageDTO(
        id=int(message.id),
        role=_enum_str(message.role),
        content=message.content,
        meta=message.meta if isinstance(message.meta, dict) else None,
        created_at=message.created_at,
    )


def _bundle_to_dto(bundle: dict) -> LessonQaBundleDTO:
    return LessonQaBundleDTO(
        session=_session_to_dto(bundle["session"]),
        messages=[_message_to_dto(m) for m in bundle["messages"]],
        suggested_prompts=list(bundle["suggested_prompts"]),
    )


@router.get("/{skill_id}/qa")
async def get_lesson_qa(
    skill_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: UserDB = Depends(get_current_active_user),
):
    try:
        bundle = await get_qa_bundle(db, int(current_user.id), skill_id)
    except ValueError as exc:
        raise _map_qa_error(exc) from exc
    return {"data": _bundle_to_dto(bundle)}


@router.post("/{skill_id}/qa/messages")
async def post_message(
    skill_id: int,
    body: LessonQaTurnRequest,
    db: AsyncSession = Depends(get_db),
    current_user: UserDB = Depends(get_current_active_user),
):
    user_id = int(current_user.id)

    async def gen():
        try:
            async for event, payload in iter_qa_turn_sse(
                db, user_id, skill_id, body.content, debug=body.debug
            ):
                yield _sse(event, payload)
        except ValueError as exc:
            yield _sse("error", {"code": "bad_request", "message": str(exc)})

    return StreamingResponse(gen(), media_type="text/event-stream")


@router.delete("/{skill_id}/qa/messages")
async def delete_lesson_qa_messages(
    skill_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: UserDB = Depends(get_current_active_user),
):
    try:
        await clear_messages(db, int(current_user.id), skill_id)
    except ValueError as exc:
        raise _map_qa_error(exc) from exc
    return {"data": {"ok": True}}
