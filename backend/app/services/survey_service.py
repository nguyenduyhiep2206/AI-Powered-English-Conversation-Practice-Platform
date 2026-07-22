from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import CEFRLevel, GoalEnum, SurveyQuestionTypeEnum, WeakPointEnum
from app.models.profile import UserProfileDB
from app.models.survey import SurveyQuestionDB
from app.schemas.survey_schema import (
    SurveyAnswerItem,
    SurveyQuestionCreate,
    SurveyQuestionPublic,
    SurveyQuestionUpdate,
)


PROFILE_FIELDS = frozenset({"occupation", "goal", "weak_point", "daily_time_min"})


def _options_to_public(options: Any) -> list[dict[str, str]] | None:
    if not options:
        return None
    return options


def _question_to_public(question: SurveyQuestionDB) -> SurveyQuestionPublic:
    return SurveyQuestionPublic(
        id=int(question.id),
        prompt=question.prompt,
        question_type=question.question_type,
        options=_options_to_public(question.options),
        is_required=question.is_required,
    )


async def _load_active_questions(db: AsyncSession) -> list[SurveyQuestionDB]:
    result = await db.execute(
        select(SurveyQuestionDB)
        .where(SurveyQuestionDB.is_active.is_(True))
        .order_by(SurveyQuestionDB.priority.desc(), SurveyQuestionDB.id.asc())
    )
    return list(result.scalars().all())


async def list_active_survey_questions(db: AsyncSession) -> list[SurveyQuestionPublic]:
    return [_question_to_public(q) for q in await _load_active_questions(db)]


async def _get_user_profile(db: AsyncSession, user_id: int) -> UserProfileDB | None:
    result = await db.execute(select(UserProfileDB).where(UserProfileDB.user_id == user_id))
    return result.scalar_one_or_none()


def _require_survey_not_done(profile: UserProfileDB | None) -> None:
    if profile and profile.survey_done:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Survey already completed",
        )


async def get_survey_questions_for_user(db: AsyncSession, user_id: int) -> list[SurveyQuestionPublic]:
    profile = await _get_user_profile(db, user_id)
    _require_survey_not_done(profile)
    return await list_active_survey_questions(db)


def _extract_answer_value(answer: dict[str, Any], question: SurveyQuestionDB) -> str:
    if question.question_type == SurveyQuestionTypeEnum.text:
        text = answer.get("text")
        if not isinstance(text, str) or not text.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Question {question.id} requires a text answer",
            )
        return text.strip()

    value = answer.get("value")
    if not isinstance(value, str) or not value.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Question {question.id} requires a selected option",
        )
    return value.strip()


def _validate_option_value(question: SurveyQuestionDB, value: str) -> None:
    if question.question_type != SurveyQuestionTypeEnum.single_choice:
        return
    options = question.options or []
    allowed = {opt["value"] for opt in options if isinstance(opt, dict) and "value" in opt}
    if value not in allowed:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid option for question {question.id}",
        )


def _apply_profile_field(profile: UserProfileDB, field: str, raw_value: str) -> None:
    if field == "occupation":
        profile.occupation = raw_value
        return
    if field == "goal":
        try:
            profile.goal = GoalEnum(raw_value)
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid goal") from exc
        return
    if field == "weak_point":
        try:
            profile.weak_point = WeakPointEnum(raw_value)
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid weak_point"
            ) from exc
        return
    if field == "daily_time_min":
        try:
            profile.daily_time_min = int(raw_value)
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid daily study time"
            ) from exc
        return
    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Unknown profile field: {field}")


async def _require_active_question_map(db: AsyncSession) -> dict[int, SurveyQuestionDB]:
    active_questions = {int(q.id): q for q in await _load_active_questions(db)}
    if not active_questions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No active survey questions configured",
        )
    return active_questions


def _require_required_answers(
    active_questions: dict[int, SurveyQuestionDB],
    answers_by_question: dict[int, SurveyAnswerItem],
) -> None:
    for question in active_questions.values():
        if question.is_required and question.id not in answers_by_question:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Missing required answer for question {question.id}",
            )


def _ensure_profile(
    db: AsyncSession, user_id: int, profile: UserProfileDB | None
) -> UserProfileDB:
    if profile is not None:
        return profile
    profile = UserProfileDB(
        user_id=user_id,
        goal=GoalEnum.daily_conversation,
        current_level=CEFRLevel.A1,
        daily_time_min=30,
        survey_done=False,
    )
    db.add(profile)
    return profile


def _apply_answers_to_profile(
    profile: UserProfileDB,
    active_questions: dict[int, SurveyQuestionDB],
    answers_by_question: dict[int, SurveyAnswerItem],
) -> None:
    for question_id, item in answers_by_question.items():
        question = active_questions.get(question_id)
        if question is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unknown or inactive question id {question_id}",
            )

        raw_value = _extract_answer_value(item.answer, question)
        _validate_option_value(question, raw_value)

        field = question.maps_to_profile_field
        if not field:
            continue
        if field not in PROFILE_FIELDS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Question {question.id} has invalid maps_to_profile_field",
            )
        _apply_profile_field(profile, field, raw_value)


async def submit_survey(
    db: AsyncSession,
    user_id: int,
    answers: list[SurveyAnswerItem],
) -> None:
    profile = await _get_user_profile(db, user_id)
    _require_survey_not_done(profile)

    active_questions = await _require_active_question_map(db)
    answers_by_question = {item.question_id: item for item in answers}
    _require_required_answers(active_questions, answers_by_question)

    profile = _ensure_profile(db, user_id, profile)
    _apply_answers_to_profile(profile, active_questions, answers_by_question)

    profile.survey_done = True
    await db.commit()


async def list_all_survey_questions(db: AsyncSession) -> list[SurveyQuestionDB]:
    result = await db.execute(
        select(SurveyQuestionDB).order_by(
            SurveyQuestionDB.priority.desc(), SurveyQuestionDB.id.asc()
        )
    )
    return list(result.scalars().all())


async def create_survey_question(db: AsyncSession, payload: SurveyQuestionCreate) -> SurveyQuestionDB:
    question = SurveyQuestionDB(
        prompt=payload.prompt,
        question_type=payload.question_type,
        options=[opt.model_dump() for opt in payload.options] if payload.options else None,
        maps_to_profile_field=payload.maps_to_profile_field,
        priority=payload.priority,
        is_required=payload.is_required,
        is_active=payload.is_active,
    )
    db.add(question)
    await db.commit()
    await db.refresh(question)
    return question


async def _get_question_or_404(db: AsyncSession, question_id: int) -> SurveyQuestionDB:
    result = await db.execute(
        select(SurveyQuestionDB).where(SurveyQuestionDB.id == question_id)
    )
    question = result.scalar_one_or_none()
    if question is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Survey question not found")
    return question


async def update_survey_question(
    db: AsyncSession,
    question_id: int,
    payload: SurveyQuestionUpdate,
) -> SurveyQuestionDB:
    question = await _get_question_or_404(db, question_id)

    updates = payload.model_dump(exclude_unset=True)
    if "options" in updates and updates["options"] is not None:
        updates["options"] = [opt.model_dump() for opt in payload.options or []]

    for key, value in updates.items():
        setattr(question, key, value)

    await db.commit()
    await db.refresh(question)
    return question


async def deactivate_survey_question(db: AsyncSession, question_id: int) -> SurveyQuestionDB:
    question = await _get_question_or_404(db, question_id)

    question.is_active = False
    await db.commit()
    await db.refresh(question)
    return question
