"""Unit tests for skill graph pure helpers (exclude / section / attach rules)."""

from app.services.skill_graph_service import (
    build_rule_attach_mappings,
    infer_section_title,
    should_exclude_unit,
)
from app.services.skill_normalize_service import normalize_unit_to_slug


def test_loai_answer_key_va_study_guide():
    assert should_exclude_unit("Key to Exercises") is True
    assert should_exclude_unit("Study guide") is True
    assert should_exclude_unit("Appendix 1 Regular and irregular verbs") is True
    assert should_exclude_unit("Present perfect 1 (I have done)") is False
    assert should_exclude_unit("Review Unit 1-3") is True


def test_suy_ra_section_title():
    units = [
        {"title": "Present perfect and past", "depth_or_source": "section", "unit_index": 0},
        {"title": "Present perfect 1 (I have done)", "depth_or_source": "toc", "unit_index": 1},
        {"title": "Present perfect 2 (I have done)", "depth_or_source": "toc", "unit_index": 2},
    ]
    assert infer_section_title(units[1], units) == "Present perfect and past"


def test_normalize_present_perfect_unit_title():
    slug, title = normalize_unit_to_slug("Present perfect 1 (I have done)")
    assert slug == "present_perfect"
    assert "present perfect" in title.lower()


def test_build_rule_attach_mappings_catalog_only():
    units = [
        {"title": "Present simple", "unit_index": 0},
        {"title": "Key to Exercises", "unit_index": 1},
        {"title": "Dragons Chapter", "unit_index": 2},
    ]
    mappings = build_rule_attach_mappings(
        units, catalog_slugs={"present_simple", "past_simple_regular"}
    )
    assert mappings[0]["slug"] == "present_simple"
    assert mappings[0]["exclude"] is False
    assert mappings[1]["exclude"] is True
    assert mappings[2]["slug"] is None
    assert mappings[2]["exclude"] is False
