import pytest

from app.services.lesson_generation_service import assert_pack_publishable
from app.services.lesson_service import compute_pack_completed
from app.services.quiz_generation_service import surfaces_from_lessons


def test_pack_completed_when_all_indices_done():
    assert (
        compute_pack_completed(
            published_indices=[0, 1, 2], completed_indices={0, 1, 2}
        )
        is True
    )


def test_pack_not_completed_partial():
    assert (
        compute_pack_completed(
            published_indices=[0, 1, 2], completed_indices={0, 1}
        )
        is False
    )


def test_legacy_single_lesson_pack_total_one():
    assert (
        compute_pack_completed(published_indices=[0], completed_indices={0}) is True
    )


def test_assert_pack_publishable_requires_three_indices():
    with pytest.raises(ValueError, match="pack"):
        assert_pack_publishable(indices_ready={0, 1}, required=3)


def test_assert_pack_publishable_ok():
    assert_pack_publishable(indices_ready={0, 1, 2}, required=3)


def test_union_surfaces_across_pack():
    lessons = [
        {"content": {"targets": [{"surface": "am"}]}},
        {"content": {"targets": [{"surface": "is"}, {"surface": "are"}]}},
    ]
    assert surfaces_from_lessons(lessons) == {"am", "is", "are"}
