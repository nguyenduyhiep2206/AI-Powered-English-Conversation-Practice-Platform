from typing import Any, Literal, Optional

from pydantic import BaseModel, Field

from app.models.enums import GoalEnum, SurveyQuestionTypeEnum, WeakPointEnum


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


class SubmitSurveyData(BaseModel):
    survey_done: bool = True
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
