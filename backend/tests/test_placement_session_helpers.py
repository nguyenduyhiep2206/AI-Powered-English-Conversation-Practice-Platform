from datetime import datetime, timedelta, timezone

from app.services.placement_session_service import (
    RETAKE_COOLDOWN_DAYS,
    progress_dict,
    retake_allowed,
)


def test_progress_dict():
    assert progress_dict(3) == {
        "asked": 3,
        "min_questions": 6,
        "max_questions": 15,
    }


def test_retake_allowed_never_completed():
    assert retake_allowed(last_completed_at=None, now=datetime.now(timezone.utc)) is True


def test_retake_cooldown():
    now = datetime(2026, 7, 23, tzinfo=timezone.utc)
    assert retake_allowed(now - timedelta(days=6), now) is False
    assert retake_allowed(now - timedelta(days=7), now) is True
    assert RETAKE_COOLDOWN_DAYS == 7
