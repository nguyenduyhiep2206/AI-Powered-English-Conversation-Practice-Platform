from app.models.enums import BookStatusEnum
from app.services.book_structure_service import status_after_successful_detect


def test_successful_detect_always_needs_review_even_high_confidence():
    assert status_after_successful_detect(0.95) == BookStatusEnum.needs_review
    assert status_after_successful_detect(0.5) == BookStatusEnum.needs_review
