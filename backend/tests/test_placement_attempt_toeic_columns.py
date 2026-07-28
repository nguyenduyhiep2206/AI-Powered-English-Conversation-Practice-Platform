"""Smoke tests for timed TOEIC placement attempt columns."""

from app.models.placement_attempt import PlacementAttemptAnswerDB, PlacementAttemptDB


def test_attempt_has_toeic_session_columns():
    assert hasattr(PlacementAttemptDB, "form_snapshot")
    assert hasattr(PlacementAttemptDB, "section")
    assert hasattr(PlacementAttemptDB, "section_ends_at")
    assert hasattr(PlacementAttemptDB, "reading_scale")
    assert hasattr(PlacementAttemptDB, "writing_scale")


def test_answer_has_writing_grade_columns():
    assert hasattr(PlacementAttemptAnswerDB, "score")
    assert hasattr(PlacementAttemptAnswerDB, "ai_scores")
    assert hasattr(PlacementAttemptAnswerDB, "ai_feedback")
