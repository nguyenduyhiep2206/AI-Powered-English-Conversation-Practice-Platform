from app.services.mastery_service import MASTERY_STRONG
from app.services.roadmap_progress_service import can_pass_week


def test_pass_khi_mastery_du():
    assert can_pass_week(0.7) is True
    assert can_pass_week(MASTERY_STRONG) is True
    assert can_pass_week(0.69) is False
    assert can_pass_week(0.0) is False
