from app.services.roadmap_assembler_service import select_skills_for_roadmap


def test_chi_lay_skill_dung_level_va_cap():
    skills = [
        {"id": 1, "slug": "a", "cefr_level": "B1", "skill_type": "grammar", "is_active": True},
        {"id": 2, "slug": "b", "cefr_level": "B1", "skill_type": "grammar", "is_active": True},
        {"id": 3, "slug": "c", "cefr_level": "B2", "skill_type": "grammar", "is_active": True},
    ]
    selected = select_skills_for_roadmap(
        [s for s in skills if s["cefr_level"] == "B1"],
        mastery={1: 0.9, 2: 0.2},
        max_steps=10,
    )
    assert [s["id"] for s in selected] == [2]


def test_khong_vuot_12_trong_level():
    skills = [
        {"id": i, "slug": f"s{i}", "cefr_level": "B1", "skill_type": "grammar", "is_active": True}
        for i in range(1, 40)
    ]
    mastery = {i: 0.1 for i in range(1, 40)}
    assert len(select_skills_for_roadmap(skills, mastery, max_steps=12)) == 12
