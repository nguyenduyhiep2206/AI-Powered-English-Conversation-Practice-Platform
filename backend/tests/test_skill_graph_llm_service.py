from unittest.mock import patch

import pytest

from app.services.skill_graph_llm_service import refine_units_with_llm


def test_refine_units_with_llm_happy_path():
    fake = {
        "unit_mappings": [
            {
                "unit_index": 0,
                "slug": "be_present",
                "title": "Be",
                "skill_type": "grammar",
                "difficulty_in_level": 2,
                "exclude": False,
            }
        ],
        "prerequisites": [],
    }
    with patch("app.services.skill_graph_llm_service.chat_json", return_value=fake):
        mappings, edges = refine_units_with_llm(
            cefr_level="A1",
            book_title="Book",
            existing_skills=[],
            units=[{"unit_index": 0, "title": "Hello", "rule_slug": "hello"}],
        )
    assert mappings[0]["slug"] == "be_present"
    assert edges == []


def test_refine_units_with_llm_rejects_non_object():
    with patch("app.services.skill_graph_llm_service.chat_json", return_value=[]):
        with pytest.raises(ValueError, match="must be an object"):
            refine_units_with_llm(
                cefr_level="A1",
                book_title="Book",
                existing_skills=[],
                units=[{"unit_index": 0, "title": "Hello", "rule_slug": "hello"}],
            )


def test_refine_units_passes_prereqs_through_validate():
    fake = {
        "unit_mappings": [
            {
                "unit_index": 0,
                "slug": "be_present",
                "title": "Be",
                "skill_type": "grammar",
                "difficulty_in_level": 2,
                "exclude": False,
            },
            {
                "unit_index": 1,
                "slug": "present_simple",
                "title": "Present simple",
                "skill_type": "grammar",
                "difficulty_in_level": 5,
                "exclude": False,
            },
        ],
        "prerequisites": [{"from_slug": "be_present", "to_slug": "present_simple"}],
    }
    with patch("app.services.skill_graph_llm_service.chat_json", return_value=fake):
        _mappings, edges = refine_units_with_llm(
            cefr_level="A1",
            book_title="Book",
            existing_skills=[],
            units=[
                {"unit_index": 0, "title": "Be", "rule_slug": "be"},
                {"unit_index": 1, "title": "PS", "rule_slug": "ps"},
            ],
        )
    assert edges == [("be_present", "present_simple")]
