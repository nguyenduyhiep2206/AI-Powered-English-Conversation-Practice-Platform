"""TOEIC quiz bank model smoke tests (unified quiz_passages / quiz_questions)."""

from app.models.enums import QuizQuestionTypeEnum, ToeicPartEnum
from app.models.quiz_passage import QuizPassageDB
from app.models.quiz_question import QuizQuestionDB


def test_toeic_parts_cover_rw():
    assert {p.value for p in ToeicPartEnum} == {"r5", "r6", "r7", "w1", "w2", "w3"}


def test_writing_question_type_exists():
    assert QuizQuestionTypeEnum.writing.value == "writing"


def test_quiz_passage_and_question_tables():
    assert QuizPassageDB.__tablename__ == "quiz_passages"
    assert QuizQuestionDB.__tablename__ == "quiz_questions"
    assert hasattr(QuizQuestionDB, "toeic_part")
    assert hasattr(QuizQuestionDB, "passage_id")
    assert hasattr(QuizQuestionDB, "prompt_words")
    assert hasattr(QuizQuestionDB, "media_url")
    assert hasattr(QuizQuestionDB, "task_brief")
