from unittest.mock import patch

import pytest

from app.services.skill_graph_llm_service import attach_units_with_llm


def test_attach_units_with_llm_happy_path():
    fake = {
        "unit_mappings": [
            {"unit_index": 0, "slug": "be_present", "exclude": False},
        ]
    }
    with patch("app.services.skill_graph_llm_service.chat_json", return_value=fake):
        mappings = attach_units_with_llm(
            cefr_level="A1",
            book_title="Book",
            catalog_skills=[{"slug": "be_present", "title": "Be", "difficulty_in_level": 2}],
            units=[{"unit_index": 0, "title": "Hello", "rule_slug": "hello"}],
        )
    assert mappings[0]["slug"] == "be_present"


def test_attach_units_with_llm_rejects_non_object():
    with patch("app.services.skill_graph_llm_service.chat_json", return_value=[]):
        with pytest.raises(ValueError, match="must be an object"):
            attach_units_with_llm(
                cefr_level="A1",
                book_title="Book",
                catalog_skills=[{"slug": "be_present", "title": "Be"}],
                units=[{"unit_index": 0, "title": "Hello", "rule_slug": "hello"}],
            )


def test_attach_passes_null_slug():
    fake = {
        "unit_mappings": [
            {"unit_index": 0, "slug": None, "exclude": False},
            {"unit_index": 1, "slug": "present_simple", "exclude": False},
        ]
    }
    catalog = [
        {"slug": "present_simple", "title": "Present simple", "difficulty_in_level": 5},
    ]
    with patch("app.services.skill_graph_llm_service.chat_json", return_value=fake):
        mappings = attach_units_with_llm(
            cefr_level="A1",
            book_title="Book",
            catalog_skills=catalog,
            units=[
                {"unit_index": 0, "title": "Odd", "rule_slug": "odd"},
                {"unit_index": 1, "title": "PS", "rule_slug": "ps"},
            ],
        )
    assert mappings[0]["slug"] is None
    assert mappings[1]["slug"] == "present_simple"
