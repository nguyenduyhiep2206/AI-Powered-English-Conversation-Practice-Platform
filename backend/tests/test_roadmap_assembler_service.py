from app.services.roadmap_assembler_service import select_skills_for_roadmap


def _skill(id, slug, diff, stype="grammar"):
    return {
        "id": id,
        "slug": slug,
        "title": slug,
        "cefr_level": "A1",
        "skill_type": stype,
        "is_active": True,
        "difficulty_in_level": diff,
    }


def test_zpd_score_3_khong_lay_diff_9():
    skills = [
        _skill(1, "be", 2),
        _skill(2, "poss", 3),
        _skill(3, "ps", 5),
        _skill(4, "past", 9),
    ]
    selected = select_skills_for_roadmap(
        skills,
        mastery={1: 0.75, 2: 0.2, 3: 0.2, 4: 0.2},
        placement_score=3,
        prereq_from_by_to={2: [1], 3: [1], 4: [3]},
        max_steps=10,
    )
    ids = [s["id"] for s in selected]
    assert 4 not in ids
    assert 2 in ids


def test_prereq_chua_dat_thi_bo():
    skills = [_skill(1, "be", 2), _skill(2, "ps", 4)]
    selected = select_skills_for_roadmap(
        skills,
        mastery={1: 0.2, 2: 0.2},
        placement_score=3,
        prereq_from_by_to={2: [1]},
        max_steps=10,
    )
    assert 2 not in [s["id"] for s in selected]


def test_max_steps_van_ton_trong():
    skills = [_skill(i, f"s{i}", 4) for i in range(1, 40)]
    selected = select_skills_for_roadmap(
        skills,
        mastery={i: 0.1 for i in range(1, 40)},
        placement_score=3,
        prereq_from_by_to={},
        max_steps=12,
    )
    assert len(selected) == 12


def test_bo_qua_skill_da_manh():
    skills = [_skill(1, "a", 4), _skill(2, "b", 4)]
    selected = select_skills_for_roadmap(
        skills,
        mastery={1: 0.9, 2: 0.2},
        placement_score=3,
        prereq_from_by_to={},
        max_steps=10,
    )
    assert [s["id"] for s in selected] == [2]
