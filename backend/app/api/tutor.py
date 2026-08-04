"""Learner API for AI Tutor text role-play sessions."""

from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_active_user
from app.core.database import get_db
from app.models.tutor import TutorMessageDB, TutorSessionDB
from app.models.user import UserDB
from app.schemas.tutor_schema import (
    TutorEndSummaryDTO,
    TutorMessageDTO,
    TutorSessionDTO,
    TutorStartSessionRequest,
    TutorTurnMessageRequest,
)
from app.services.tutor_service import (
    _require_active_session,
    _validate_turn_input,
    end_session,
    get_session_for_user,
    iter_turn_sse,
    start_session,
)

router = APIRouter()


def _sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


def _map_tutor_error(exc: ValueError) -> HTTPException:
    msg = str(exc)
    if msg == "Tutor session not found":
        return HTTPException(status_code=404, detail=msg)
    if msg == "Not allowed to access this tutor session":
        return HTTPException(status_code=403, detail=msg)
    if msg in {"Roadmap step not found", "Roadmap step progress not found"}:
        return HTTPException(status_code=404, detail=msg)
    if msg == "Tutor session is not active":
        return HTTPException(status_code=409, detail=msg)
    return HTTPException(status_code=400, detail=msg)


async def _session_to_dto(db: AsyncSession, session: TutorSessionDB) -> TutorSessionDTO:
    messages = (
        await db.execute(
            select(TutorMessageDB)
            .where(TutorMessageDB.session_id == session.id)
            .order_by(TutorMessageDB.id)
        )
    ).scalars().all()
    dto = TutorSessionDTO.model_validate(session)
    return dto.model_copy(
        update={
            "messages": [TutorMessageDTO.model_validate(message) for message in messages],
        }
    )


@router.post("/sessions")
async def create_session(
    body: TutorStartSessionRequest,
    db: AsyncSession = Depends(get_db),
    current_user: UserDB = Depends(get_current_active_user),
):
    try:
        session = await start_session(db, int(current_user.id), body.roadmap_step_id)
    except ValueError as exc:
        raise _map_tutor_error(exc) from exc
    return {"data": await _session_to_dto(db, session)}


@router.get("/sessions/{session_id}")
async def get_session(
    session_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: UserDB = Depends(get_current_active_user),
):
    try:
        session = await get_session_for_user(db, int(current_user.id), session_id)
    except ValueError as exc:
        raise _map_tutor_error(exc) from exc
    return {"data": await _session_to_dto(db, session)}


@router.post("/sessions/{session_id}/messages")
async def post_message(
    session_id: int,
    body: TutorTurnMessageRequest,
    db: AsyncSession = Depends(get_db),
    current_user: UserDB = Depends(get_current_active_user),
):
    user_id = int(current_user.id)
    try:
        session = await get_session_for_user(db, user_id, session_id)
        _require_active_session(session)
        _validate_turn_input(session, body.content)
    except ValueError as exc:
        raise _map_tutor_error(exc) from exc

    async def gen():
        async for event, payload in iter_turn_sse(db, user_id, session_id, body.content):
            yield _sse(event, payload)

    return StreamingResponse(gen(), media_type="text/event-stream")


@router.post("/sessions/{session_id}/end")
async def end_tutor_session(
    session_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: UserDB = Depends(get_current_active_user),
):
    try:
        summary = await end_session(db, int(current_user.id), session_id)
    except ValueError as exc:
        raise _map_tutor_error(exc) from exc
    return {"data": TutorEndSummaryDTO.model_validate(summary)}
