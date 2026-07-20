# backend/tests/test_skill_graph_validate.py
import pytest

from app.services.skill_graph_validate import validate_llm_graph_payload

ALLOWED = {"grammar", "vocabulary", "reading", "functional"}


def test_validate_maps_and_keeps_valid_edge():
    payload = {
        "unit_mappings": [
            {
                "unit_index": 0,
                "slug": "be_present",
                "title": "Be present",
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
        "prerequisites": [
            {"from_slug": "be_present", "to_slug": "present_simple"},
            {"from_slug": "present_simple", "to_slug": "present_simple"},  # self — drop
        ],
    }
    mappings, edges = validate_llm_graph_payload(
        payload,
        unit_indexes={0, 1},
        existing_slugs=set(),
        allowed_skill_types=ALLOWED,
    )
    assert len(mappings) == 2
    assert edges == [("be_present", "present_simple")]


def test_validate_drops_cycle_edge():
    payload = {
        "unit_mappings": [
            {
                "unit_index": 0,
                "slug": "skill_a",
                "title": "A",
                "skill_type": "grammar",
                "difficulty_in_level": 1,
                "exclude": False,
            },
            {
                "unit_index": 1,
                "slug": "skill_b",
                "title": "B",
                "skill_type": "grammar",
                "difficulty_in_level": 2,
                "exclude": False,
            },
        ],
        "prerequisites": [
            {"from_slug": "skill_a", "to_slug": "skill_b"},
            {"from_slug": "skill_b", "to_slug": "skill_a"},
        ],
    }
    _mappings, edges = validate_llm_graph_payload(
        payload,
        unit_indexes={0, 1},
        existing_slugs=set(),
        allowed_skill_types=ALLOWED,
    )
    assert edges == [("skill_a", "skill_b")]


def test_validate_rejects_missing_unit_coverage():
    payload = {"unit_mappings": [], "prerequisites": []}
    with pytest.raises(ValueError):
        validate_llm_graph_payload(
            payload,
            unit_indexes={0},
            existing_slugs=set(),
            allowed_skill_types={"grammar"},
        )


def test_validate_reuses_existing_slug_in_prereq():
    payload = {
        "unit_mappings": [
            {
                "unit_index": 0,
                "slug": "present_simple",
                "title": "Present simple",
                "skill_type": "grammar",
                "difficulty_in_level": 5,
                "exclude": False,
            }
        ],
        "prerequisites": [{"from_slug": "be_present", "to_slug": "present_simple"}],
    }
    _mappings, edges = validate_llm_graph_payload(
        payload,
        unit_indexes={0},
        existing_slugs={"be_present"},
        allowed_skill_types=ALLOWED,
    )
    assert edges == [("be_present", "present_simple")]
