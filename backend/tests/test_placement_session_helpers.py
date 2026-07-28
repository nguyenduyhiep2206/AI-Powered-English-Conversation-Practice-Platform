from app.services.placement.session_service import can_start_new_placement


def test_can_start_first_placement():
    assert (
        can_start_new_placement(has_in_progress=False, placement_score=None) is True
    )


def test_cannot_start_when_in_progress():
    assert (
        can_start_new_placement(has_in_progress=True, placement_score=None) is False
    )


def test_cannot_start_after_completed():
    assert (
        can_start_new_placement(has_in_progress=False, placement_score=5) is False
    )
