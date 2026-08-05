from app.seeds.cefr_ladder_a1_a2 import A1_SKILLS, A2_SKILLS
from app.seeds.theme_units_a1_a2 import A1_UNITS, A2_UNITS, all_unit_skill_slugs


def test_a1_units_cover_all_catalog_slugs():
    catalog = {s[0] for s in A1_SKILLS}
    assert all_unit_skill_slugs(A1_UNITS) == catalog


def test_a2_units_cover_all_catalog_slugs():
    catalog = {s[0] for s in A2_SKILLS}
    assert all_unit_skill_slugs(A2_UNITS) == catalog


def test_no_duplicate_skill_across_a1_units():
    flat = [s for _, _, _, skills in A1_UNITS for s in skills]
    assert len(flat) == len(set(flat))


def test_no_duplicate_skill_across_a2_units():
    flat = [s for _, _, _, skills in A2_UNITS for s in skills]
    assert len(flat) == len(set(flat))
