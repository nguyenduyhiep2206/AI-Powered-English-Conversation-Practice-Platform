from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_active_user
from app.core.database import get_db
from app.models.user import UserDB
from app.models.enums import CEFRLevel
from app.schemas.onboarding_schema import (
    LevelChallengeQuestionsData,
    LevelChallengeQuestionsResponse,
    LevelChallengeResultData,
    LevelChallengeSubmitRequest,
    LevelChallengeSubmitResponse,
    OnboardingStatusResponse,
    PlacementAnswerRequest,
    PlacementProgressOut,
    PlacementQuestionOut,
    PlacementRetakeStatusData,
    PlacementRetakeStatusResponse,
    PlacementSessionData,
    PlacementSessionResponse,
)
from app.schemas.survey_schema import (
    SubmitSurveyData,
    SubmitSurveyRequest,
    SubmitSurveyResponse,
    SurveyQuestionsData,
    SurveyQuestionsResponse,
)
from app.services.level_challenge_service import (
    INSUFFICIENT_CHALLENGE_BANK_MSG,
    get_level_challenge_questions,
    submit_level_challenge,
)
from app.services.onboarding_service import get_onboarding_status
from app.services.placement.session_service import (
    INSUFFICIENT_ADAPTIVE_BANK_MSG,
    get_current_session,
    get_retake_status,
    start_or_resume_session,
    submit_session_answer,
)
from app.services.survey_service import get_survey_questions_for_user, submit_survey

router = APIRouter()


def _session_data(payload: dict) -> PlacementSessionData:
    question = None
    if payload.get("question"):
        question = PlacementQuestionOut(**payload["question"])
    progress = None
    if payload.get("progress"):
        progress = PlacementProgressOut(**payload["progress"])
    return PlacementSessionData(
        done=bool(payload["done"]),
        attempt_id=int(payload["attempt_id"]),
        question=question,
        progress=progress,
        placement_score=payload.get("placement_score"),
        current_level=payload.get("current_level"),
        questions_asked=payload.get("questions_asked"),
        onboarding_complete=payload.get("onboarding_complete"),
    )


def _map_placement_exc(exc: Exception) -> HTTPException:
    if isinstance(exc, PermissionError):
        return HTTPException(status_code=400, detail=str(exc))
    if isinstance(exc, RuntimeError):
        return HTTPException(status_code=409, detail=str(exc))
    if isinstance(exc, ValueError):
        msg = str(exc)
        status = 503 if msg == INSUFFICIENT_ADAPTIVE_BANK_MSG else 400
        return HTTPException(status_code=status, detail=msg)
    return HTTPException(status_code=500, detail="Internal error")


@router.get("/status", response_model=OnboardingStatusResponse)
async def onboarding_status(
    current_user: UserDB = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Check whether the user has completed survey and placement test."""
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
    await submit_survey(db, int(current_user.id), payload.answers)
    return SubmitSurveyResponse(data=SubmitSurveyData())


@router.post("/placement/sessions", response_model=PlacementSessionResponse)
async def placement_start_session(
    current_user: UserDB = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Start or resume an adaptive placement session."""
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
    """Resume in-progress adaptive placement, or 404 if none."""
    try:
        payload = await get_current_session(db, int(current_user.id))
    except (PermissionError, RuntimeError, ValueError) as exc:
        raise _map_placement_exc(exc) from exc
    if payload is None:
        raise HTTPException(status_code=404, detail="Không có placement session đang chạy")
    return PlacementSessionResponse(data=_session_data(payload))


@router.post(
    "/placement/sessions/{attempt_id}/answers",
    response_model=PlacementSessionResponse,
)
async def placement_session_answer(
    attempt_id: int,
    payload: PlacementAnswerRequest,
    current_user: UserDB = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Grade one adaptive answer; return next question or final result."""
    try:
        result = await submit_session_answer(
            db,
            int(current_user.id),
            attempt_id,
            payload.question_id,
            payload.answer,
        )
    except (PermissionError, RuntimeError, ValueError) as exc:
        raise _map_placement_exc(exc) from exc
    return PlacementSessionResponse(data=_session_data(result))


@router.get("/placement/retake-status", response_model=PlacementRetakeStatusResponse)
async def placement_retake_status(
    current_user: UserDB = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        data = await get_retake_status(db, int(current_user.id))
    except (PermissionError, RuntimeError, ValueError) as exc:
        raise _map_placement_exc(exc) from exc
    return PlacementRetakeStatusResponse(data=PlacementRetakeStatusData(**data))


@router.get("/level-challenge", response_model=LevelChallengeQuestionsResponse)
async def level_challenge_questions(
    target_level: CEFRLevel | None = None,
    current_user: UserDB = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Return 6 published questions for the next CEFR level (no answers)."""
    try:
        data = await get_level_challenge_questions(
            db, int(current_user.id), target_level=target_level
        )
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ValueError as exc:
        status = 503 if str(exc) == INSUFFICIENT_CHALLENGE_BANK_MSG else 400
        raise HTTPException(status_code=status, detail=str(exc)) from exc

    questions = [PlacementQuestionOut(**q) for q in data["questions"]]
    return LevelChallengeQuestionsResponse(
        data=LevelChallengeQuestionsData(
            target_level=data["target_level"],
            question_count=data["question_count"],
            questions=questions,
        )
    )


@router.post("/level-challenge", response_model=LevelChallengeSubmitResponse)
async def level_challenge_submit(
    payload: LevelChallengeSubmitRequest,
    current_user: UserDB = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Grade +1 CEFR challenge; promote on pass. Does not auto-assemble roadmap."""
    try:
        result = await submit_level_challenge(
            db,
            int(current_user.id),
            payload.target_level,
            [a.model_dump() for a in payload.answers],
        )
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return LevelChallengeSubmitResponse(data=LevelChallengeResultData(**result))
