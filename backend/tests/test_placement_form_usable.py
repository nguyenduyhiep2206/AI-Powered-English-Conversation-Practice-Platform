"""Tests for TOEIC form usability on placement sessions."""

from app.services.placement.session_service import _form_is_usable


def test_form_usable_requires_reading_items():
    assert _form_is_usable(None) is False
    assert _form_is_usable({}) is False
    assert _form_is_usable({"reading_items": []}) is False
    assert _form_is_usable({"reading_items": [{"id": 1}]}) is True
