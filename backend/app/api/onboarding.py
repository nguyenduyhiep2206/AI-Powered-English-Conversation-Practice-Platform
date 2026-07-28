from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_active_user
from app.core.database import get_db
from app.models.user import UserDB
from app.schemas.onboarding_schema import (
    OnboardingStatusResponse,
    PlacementAccessStatusData,
    PlacementAccessStatusResponse,
    PlacementFormOut,
    PlacementSessionData,
    PlacementSessionResponse,
    ReadingAnswersRequest,
    WritingAnswerRequest,
)
from app.schemas.survey_schema import (
    SubmitSurveyData,
    SubmitSurveyRequest,
    SubmitSurveyResponse,
    SurveyQuestionsData,
    SurveyQuestionsResponse,
)
from app.services.onboarding_service import get_onboarding_status
from app.services.placement.session_service import (
    INSUFFICIENT_BANK_MSG,
    advance_section,
    complete_session,
    get_current_session,
    get_placement_access_status,
    start_or_resume_session,
    submit_reading_answers,
    submit_writing_answer,
)
from app.services.survey_service import (
    LevelResolutionError,
    get_survey_questions_for_user,
    submit_survey,
)

router = APIRouter()


def _session_data(payload: dict) -> PlacementSessionData:
    form = None
    if payload.get("form"):
        form = PlacementFormOut(**payload["form"])
    return PlacementSessionData(
        done=bool(payload["done"]),
        attempt_id=int(payload["attempt_id"]),
        section=payload.get("section"),
        section_ends_at=payload.get("section_ends_at"),
        form=form,
        reading_raw=payload.get("reading_raw"),
        reading_scale=payload.get("reading_scale"),
        writing_raw=payload.get("writing_raw"),
        writing_scale=payload.get("writing_scale"),
        placement_score=payload.get("placement_score"),
        current_level=payload.get("current_level"),
        writing_feedback=payload.get("writing_feedback"),
        saved_answers=payload.get("saved_answers") or {},
        onboarding_complete=payload.get("onboarding_complete"),
    )


def _map_placement_exc(exc: Exception) -> HTTPException:
    if isinstance(exc, PermissionError):
        return HTTPException(status_code=400, detail=str(exc))
    if isinstance(exc, RuntimeError):
        return HTTPException(status_code=409, detail=str(exc))
    if isinstance(exc, ValueError):
        msg = str(exc)
        status = 503 if msg == INSUFFICIENT_BANK_MSG else 400
        return HTTPException(status_code=status, detail=msg)
    return HTTPException(status_code=500, detail="Internal error")


@router.get("/status", response_model=OnboardingStatusResponse)
async def onboarding_status(
    current_user: UserDB = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    data = await get_onboarding_status(db, int(current_user.id))
    return OnboardingStatusResponse(data=data)


@router.get("/survey/questions", response_model=SurveyQuestionsResponse)
async def survey_questions(
    current_user: UserDB = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    questions = await get_survey_questions_for_user(db, int(current_user.id))
    return SurveyQuestionsResponse(data=SurveyQuestionsData(questions=questions))


@router.post("/survey", response_model=SubmitSurveyResponse, status_code=200)
async def submit_survey_answers(
    payload: SubmitSurveyRequest,
    current_user: UserDB = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        result = await submit_survey(
            db,
            int(current_user.id),
            payload.answers,
            payload.level_resolution,
        )
    except LevelResolutionError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return SubmitSurveyResponse(
        data=SubmitSurveyData(next_step=result["next_step"])
    )


@router.post("/placement/sessions", response_model=PlacementSessionResponse)
async def placement_start_session(
    current_user: UserDB = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        payload = await start_or_resume_session(db, int(current_user.id))
    except (PermissionError, RuntimeError, ValueError) as exc:
        raise _map_placement_exc(exc) from exc
    return PlacementSessionResponse(data=_session_data(payload))


@router.get("/placement/sessions/current", response_model=PlacementSessionResponse)
async def placement_current_session(
    current_user: UserDB = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        payload = await get_current_session(db, int(current_user.id))
    except (PermissionError, RuntimeError, ValueError) as exc:
        raise _map_placement_exc(exc) from exc
    if payload is None:
        raise HTTPException(status_code=404, detail="Không có placement session đang chạy")
    return PlacementSessionResponse(data=_session_data(payload))


@router.post(
    "/placement/sessions/{attempt_id}/answers",
    status_code=410,
)
async def placement_session_answer_deprecated(
    attempt_id: int,
    current_user: UserDB = Depends(get_current_active_user),
):
    raise HTTPException(
        status_code=410,
        detail="Adaptive placement removed. Use reading-answers / writing-answers.",
    )


@router.post(
    "/placement/sessions/{attempt_id}/reading-answers",
    response_model=PlacementSessionResponse,
)
async def placement_reading_answers(
    attempt_id: int,
    payload: ReadingAnswersRequest,
    current_user: UserDB = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        result = await submit_reading_answers(
            db,
            int(current_user.id),
            attempt_id,
            [a.model_dump() for a in payload.answers],
        )
    except (PermissionError, RuntimeError, ValueError) as exc:
        raise _map_placement_exc(exc) from exc
    return PlacementSessionResponse(data=_session_data(result))


@router.post(
    "/placement/sessions/{attempt_id}/writing-answers",
    response_model=PlacementSessionResponse,
)
async def placement_writing_answers(
    attempt_id: int,
    payload: WritingAnswerRequest,
    current_user: UserDB = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        result = await submit_writing_answer(
            db,
            int(current_user.id),
            attempt_id,
            payload.item_id,
            payload.text,
        )
    except (PermissionError, RuntimeError, ValueError) as exc:
        raise _map_placement_exc(exc) from exc
    return PlacementSessionResponse(data=_session_data(result))


@router.post(
    "/placement/sessions/{attempt_id}/advance-section",
    response_model=PlacementSessionResponse,
)
async def placement_advance_section(
    attempt_id: int,
    current_user: UserDB = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        result = await advance_section(db, int(current_user.id), attempt_id)
    except (PermissionError, RuntimeError, ValueError) as exc:
        raise _map_placement_exc(exc) from exc
    return PlacementSessionResponse(data=_session_data(result))


@router.post(
    "/placement/sessions/{attempt_id}/complete",
    response_model=PlacementSessionResponse,
)
async def placement_complete(
    attempt_id: int,
    current_user: UserDB = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        result = await complete_session(db, int(current_user.id), attempt_id)
    except (PermissionError, RuntimeError, ValueError) as exc:
        raise _map_placement_exc(exc) from exc
    return PlacementSessionResponse(data=_session_data(result))


@router.get("/placement/access-status", response_model=PlacementAccessStatusResponse)
async def placement_access_status(
    current_user: UserDB = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        data = await get_placement_access_status(db, int(current_user.id))
    except (PermissionError, RuntimeError, ValueError) as exc:
        raise _map_placement_exc(exc) from exc
    return PlacementAccessStatusResponse(data=PlacementAccessStatusData(**data))
