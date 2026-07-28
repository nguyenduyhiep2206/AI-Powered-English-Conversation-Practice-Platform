"""Tests for TOEIC writing task validation."""

from app.services.writing_generation_service import validate_writing_tasks, writing_publishable
from app.models.enums import ToeicPartEnum, QuizQuestionTypeEnum
from app.models.quiz_question import QuizQuestionDB


def test_validate_w2_requires_passage():
    assert validate_writing_tasks([{"toeic_part": "w2", "stem": "Reply", "passage": ""}]) == []
    ok = validate_writing_tasks(
        [
            {
                "toeic_part": "w2",
                "stem": "Reply as Mary",
                "passage": "Dear Mary, please meet next week.",
                "task_brief": {"must_ask": 2, "must_provide": 1},
            }
        ]
    )
    assert len(ok) == 1


def test_validate_w3_sets_min_words():
    ok = validate_writing_tasks(
        [{"toeic_part": "w3", "stem": "Discuss remote work.", "task_brief": {}}]
    )
    assert ok[0]["task_brief"]["min_words"] == 300


def test_w1_not_publishable_without_media():
    row = QuizQuestionDB(
        skill_id=1,
        book_id=1,
        unit_id=1,
        question_type=QuizQuestionTypeEnum.writing,
        toeic_part=ToeicPartEnum.w1,
        stem="Write a sentence",
        prompt_words=["to", "whiteboard"],
        answer="",
    )
    assert writing_publishable(row) is False
    row.media_url = "https://example.com/pic.png"
    assert writing_publishable(row) is True
