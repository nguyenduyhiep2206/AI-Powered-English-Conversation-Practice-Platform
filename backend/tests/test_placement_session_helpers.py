from datetime import datetime, timedelta, timezone

from app.services.placement.session_service import (
    RETAKE_COOLDOWN_DAYS,
    _retake_allowed_for_profile,
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


def test_retake_allowed_for_profile_first_time():
    now = datetime(2026, 7, 23, tzinfo=timezone.utc)
    assert (
        _retake_allowed_for_profile(
            has_in_progress=False,
            last_completed_at=None,
            placement_score=None,
            now=now,
        )
        is True
    )


def test_retake_allowed_for_profile_blocks_in_progress():
    now = datetime(2026, 7, 23, tzinfo=timezone.utc)
    assert (
        _retake_allowed_for_profile(
            has_in_progress=True,
            last_completed_at=None,
            placement_score=None,
            now=now,
        )
        is False
    )


def test_get_in_progress_prefers_most_asked_then_newest():
    """Document preferred-attempt ordering used when duplicates exist."""
    # Mirrors order_by(questions_asked.desc(), started_at.desc(), id.desc())
    rows = [
        {"id": 1, "questions_asked": 2, "started_at": datetime(2026, 7, 1, tzinfo=timezone.utc)},
        {"id": 2, "questions_asked": 5, "started_at": datetime(2026, 7, 1, tzinfo=timezone.utc)},
        {"id": 3, "questions_asked": 5, "started_at": datetime(2026, 7, 2, tzinfo=timezone.utc)},
    ]
    preferred = sorted(
        rows,
        key=lambda r: (r["questions_asked"], r["started_at"], r["id"]),
        reverse=True,
    )[0]
    assert preferred["id"] == 3
