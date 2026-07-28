from datetime import datetime
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field

from app.models.enums import CEFRLevel, GoalEnum, WeakPointEnum


OnboardingStep = Literal["survey", "placement", "completed"]


class OnboardingStatusData(BaseModel):
    survey_done: bool
    placement_done: bool
    onboarding_complete: bool
    current_step: OnboardingStep
    occupation: Optional[str] = None
    goal: Optional[GoalEnum] = None
    weak_point: Optional[WeakPointEnum] = None
    daily_time_min: Optional[int] = None
    current_level: Optional[CEFRLevel] = None
    placement_score: Optional[int] = None


class OnboardingStatusResponse(BaseModel):
    success: bool = True
    data: OnboardingStatusData


class PlacementFormItemOut(BaseModel):
    id: int
    toeic_part: str | None = None
    stem: str | None = None
    options: list[str] | None = None
    skill_id: int | None = None
    cefr_level: str | None = None
    passage_id: int | None = None
    prompt_words: list[str] | None = None
    media_url: str | None = None
    task_brief: dict[str, Any] | None = None
    question_type: str | None = None


class PlacementFormOut(BaseModel):
    reading_items: list[PlacementFormItemOut] = Field(default_factory=list)
    writing_items: list[PlacementFormItemOut] = Field(default_factory=list)
    passages: dict[str, Any] = Field(default_factory=dict)


class PlacementSessionData(BaseModel):
    done: bool
    attempt_id: int
    section: str | None = None
    section_ends_at: datetime | None = None
    form: PlacementFormOut | None = None
    reading_raw: int | None = None
    reading_scale: int | None = None
    writing_raw: float | None = None
    writing_scale: int | None = None
    placement_score: int | None = None
    current_level: str | None = None
    writing_feedback: list[dict[str, Any]] | None = None
    onboarding_complete: bool | None = None
    # Legacy adaptive fields (unused)
    question: Any | None = None
    progress: Any | None = None
    questions_asked: int | None = None


class PlacementSessionResponse(BaseModel):
    success: bool = True
    data: PlacementSessionData


class ReadingAnswerItem(BaseModel):
    item_id: int
    given_answer: str


class ReadingAnswersRequest(BaseModel):
    answers: list[ReadingAnswerItem]


class WritingAnswerRequest(BaseModel):
    item_id: int
    text: str


class PlacementAnswerRequest(BaseModel):
    """Deprecated adaptive payload."""

    question_id: int
    answer: str


class PlacementRetakeStatusData(BaseModel):
    allowed: bool
    has_in_progress: bool
    retry_after_at: datetime | None = None


class PlacementRetakeStatusResponse(BaseModel):
    success: bool = True
    data: PlacementRetakeStatusData
