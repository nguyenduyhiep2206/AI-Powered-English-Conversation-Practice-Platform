import pytest
from app.models.enums import CEFRLevel
from app.services.survey_service import (
    resolve_level_for_survey,
    LevelResolutionError,
)


def test_beginner_sets_a1_and_score_1():
    level, score, next_step = resolve_level_for_survey(
        {"mode": "beginner"}
    )
    assert level == CEFRLevel.A1
    assert score == 1
    assert next_step == "completed"


def test_self_selected_requires_cefr_and_sets_score_1():
    """Self-declared level has no measured sub-level — start at band floor."""
    level, score, next_step = resolve_level_for_survey(
        {"mode": "self_selected", "cefr_level": "A2"}
    )
    assert level == CEFRLevel.A2
    assert score == 1
    assert next_step == "completed"


def test_self_selected_missing_cefr_raises():
    with pytest.raises(LevelResolutionError):
        resolve_level_for_survey({"mode": "self_selected"})


def test_placement_mode_leaves_score_unset():
    level, score, next_step = resolve_level_for_survey(
        {"mode": "placement"}
    )
    assert level is None
    assert score is None
    assert next_step == "placement"
