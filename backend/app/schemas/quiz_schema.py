from typing import Any, Literal, Optional

from pydantic import BaseModel, Field

from app.models.enums import QuizQuestionStatusEnum, QuizQuestionTypeEnum, ToeicPartEnum


class GenerateQuizRequest(BaseModel):
    count: int = Field(default=10, ge=1, le=15)
    mode: Literal["skill_drill", "toeic"] = "skill_drill"


class GenerateWritingRequest(BaseModel):
    count: int = Field(default=2, ge=1, le=6)


class QuizQuestionOut(BaseModel):
    id: int
    skill_id: int
    book_id: int
    unit_id: int
    question_type: QuizQuestionTypeEnum
    stem: str
    passage: Optional[str] = None
    passage_id: Optional[int] = None
    toeic_part: Optional[ToeicPartEnum] = None
    prompt_words: Optional[list[str]] = None
    media_url: Optional[str] = None
    task_brief: Optional[dict[str, Any]] = None
    options: Optional[list[str]] = None
    answer: str
    explanation: Optional[str] = None
    difficulty: str
    status: QuizQuestionStatusEnum
    generation_batch_id: Optional[str] = None

    model_config = {"from_attributes": True}


class QuizQuestionListResponse(BaseModel):
    data: list[QuizQuestionOut]


class GenerateQuizResponse(BaseModel):
    data: list[QuizQuestionOut]
    message: str = "Đã tạo câu hỏi nháp"


class PublishQuizRequest(BaseModel):
    question_ids: list[int]
