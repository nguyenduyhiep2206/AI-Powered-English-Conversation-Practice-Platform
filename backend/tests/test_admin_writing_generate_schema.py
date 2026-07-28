"""Smoke tests for admin writing generate request schema."""

from app.schemas.quiz_schema import GenerateWritingRequest, QuizQuestionOut
from app.models.enums import QuizQuestionTypeEnum, QuizQuestionStatusEnum


def test_generate_writing_request_defaults():
    body = GenerateWritingRequest()
    assert body.count == 2


def test_quiz_question_out_accepts_toeic_fields():
    out = QuizQuestionOut(
        id=1,
        skill_id=1,
        book_id=1,
        unit_id=1,
        question_type=QuizQuestionTypeEnum.writing,
        stem="Respond to the email",
        toeic_part="w2",
        answer="",
        difficulty="medium",
        status=QuizQuestionStatusEnum.draft,
    )
    assert out.toeic_part.value == "w2"
