"""Pure checks for curated CEFR ladder seed data (no DB required)."""

from app.models.enums import CEFRLevel
from app.seeds.cefr_ladder_a1_a2 import (
    A1_EDGES,
    A1_SKILLS,
    A2_EDGES,
    A2_SKILLS,
    catalog_slug_set,
)


def test_a1_a2_slugs_unique_within_level():
    assert len({s[0] for s in A1_SKILLS}) == len(A1_SKILLS)
    assert len({s[0] for s in A2_SKILLS}) == len(A2_SKILLS)


def test_catalog_sizes_match_plan():
    assert len(A1_SKILLS) == 22
    assert len(A2_SKILLS) == 22


def test_edges_only_reference_catalog_slugs():
    a1 = catalog_slug_set(CEFRLevel.A1)
    a2 = catalog_slug_set(CEFRLevel.A2)
    for frm, to in A1_EDGES:
        assert frm in a1 and to in a1
        assert frm != to
    for frm, to in A2_EDGES:
        assert frm in a2 and to in a2
        assert frm != to


def test_difficulty_in_1_to_10():
    for row in A1_SKILLS + A2_SKILLS:
        assert 1 <= row[2] <= 10
