from app.models.enums import BookStatusEnum
from app.services.book_structure_service import (
    status_after_structure_decision,
    status_after_successful_detect,
)


def test_successful_detect_legacy_helper_still_needs_review():
    assert status_after_successful_detect(0.95) == BookStatusEnum.needs_review
    assert status_after_successful_detect(0.5) == BookStatusEnum.needs_review


def test_gate_pass_with_auto_index_sets_processing():
    assert (
        status_after_structure_decision(gate_ok=True, auto_index_enabled=True)
        == BookStatusEnum.processing
    )


def test_gate_fail_sets_needs_review():
    assert (
        status_after_structure_decision(gate_ok=False, auto_index_enabled=True)
        == BookStatusEnum.needs_review
    )


def test_auto_index_disabled_always_needs_review_even_if_gate_ok():
    assert (
        status_after_structure_decision(gate_ok=True, auto_index_enabled=False)
        == BookStatusEnum.needs_review
    )
