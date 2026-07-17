from typing import Optional

from pydantic import BaseModel, Field

from app.models.enums import QuizQuestionStatusEnum, QuizQuestionTypeEnum


class GenerateQuizRequest(BaseModel):
    count: int = Field(default=8, ge=1, le=15)


class QuizQuestionOut(BaseModel):
    id: int
    skill_id: int
    book_id: int
    unit_id: int
    question_type: QuizQuestionTypeEnum
    stem: str
    passage: Optional[str] = None
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
