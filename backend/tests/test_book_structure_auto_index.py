from app.models.enums import BookStatusEnum
from app.services.book_structure_service import status_after_structure_decision


def test_gate_pass_sets_processing_and_implies_index():
    status = status_after_structure_decision(gate_ok=True, auto_index_enabled=True)
    assert status == BookStatusEnum.processing
    should_index = status == BookStatusEnum.processing
    assert should_index is True


def test_gate_fail_sets_needs_review_no_index():
    status = status_after_structure_decision(gate_ok=False, auto_index_enabled=True)
    assert status == BookStatusEnum.needs_review
    should_index = status == BookStatusEnum.processing
    assert should_index is False
