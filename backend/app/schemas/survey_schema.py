from typing import Any, Literal, Optional

from pydantic import BaseModel, Field, model_validator

from app.models.enums import CEFRLevel, GoalEnum, SurveyQuestionTypeEnum, WeakPointEnum


class LevelResolution(BaseModel):
    mode: Literal["beginner", "self_selected", "placement"]
    cefr_level: Optional[CEFRLevel] = None

    @model_validator(mode="after")
    def _require_cefr_when_self(self):
        if self.mode == "self_selected" and self.cefr_level is None:
            raise ValueError("cefr_level is required when mode is self_selected")
        return self


class SurveyOption(BaseModel):
    value: str
    label: str


class SurveyQuestionPublic(BaseModel):
    id: int
    prompt: str
    question_type: SurveyQuestionTypeEnum
    options: Optional[list[SurveyOption]] = None
    is_required: bool

    model_config = {"from_attributes": True}


class SurveyQuestionsData(BaseModel):
    questions: list[SurveyQuestionPublic]


class SurveyQuestionsResponse(BaseModel):
    success: bool = True
    data: SurveyQuestionsData


class SurveyAnswerItem(BaseModel):
    question_id: int
    answer: dict[str, Any] = Field(
        ...,
        description='e.g. {"value": "job_interview"} or {"text": "custom occupation"}',
    )


class SubmitSurveyRequest(BaseModel):
    answers: list[SurveyAnswerItem]
    level_resolution: LevelResolution


class SubmitSurveyData(BaseModel):
    survey_done: bool = True
    next_step: Literal["placement", "completed"]
    message: str = "Survey submitted successfully"


class SubmitSurveyResponse(BaseModel):
    success: bool = True
    data: SubmitSurveyData


ProfileFieldName = Literal["occupation", "goal", "weak_point", "daily_time_min"]


class SurveyQuestionAdmin(BaseModel):
    id: int
    prompt: str
    question_type: SurveyQuestionTypeEnum
    options: Optional[list[SurveyOption]] = None
    maps_to_profile_field: Optional[ProfileFieldName] = None
    priority: int
    is_required: bool
    is_active: bool

    model_config = {"from_attributes": True}


class SurveyQuestionCreate(BaseModel):
    prompt: str = Field(..., min_length=1, max_length=500)
    question_type: SurveyQuestionTypeEnum
    options: Optional[list[SurveyOption]] = None
    maps_to_profile_field: Optional[ProfileFieldName] = None
    priority: int = 0
    is_required: bool = True
    is_active: bool = True


class SurveyQuestionUpdate(BaseModel):
    prompt: Optional[str] = Field(None, min_length=1, max_length=500)
    question_type: Optional[SurveyQuestionTypeEnum] = None
    options: Optional[list[SurveyOption]] = None
    maps_to_profile_field: Optional[ProfileFieldName] = None
    priority: Optional[int] = None
    is_required: Optional[bool] = None
    is_active: Optional[bool] = None


class SurveyQuestionListResponse(BaseModel):
    success: bool = True
    data: list[SurveyQuestionAdmin]


class SurveyQuestionResponse(BaseModel):
    success: bool = True
    data: SurveyQuestionAdmin
