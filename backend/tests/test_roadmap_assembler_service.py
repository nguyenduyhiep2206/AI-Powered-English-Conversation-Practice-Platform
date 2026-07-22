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


def test_prereq_chain_unfolds_into_later_weeks():
    # diff-9 skill is far above placement, but reachable as a later week once its
    # prerequisite (skill 3) is placed earlier in the path (sequential semantics).
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
    # skill 1 is below the placement floor + already strong → assumed known, not taught.
    assert ids == [2, 3, 4]


def test_prereq_becomes_earlier_week_instead_of_dropped():
    # Both skills are at/above the floor; the unmet prereq (skill 1) is scheduled
    # as an earlier week rather than excluding its dependent (skill 2).
    skills = [_skill(1, "be", 3), _skill(2, "ps", 4)]
    selected = select_skills_for_roadmap(
        skills,
        mastery={1: 0.2, 2: 0.2},
        placement_score=3,
        prereq_from_by_to={2: [1]},
        max_steps=10,
    )
    assert [s["id"] for s in selected] == [1, 2]


def test_linear_chain_builds_sequential_path():
    # Regression: a strict linear prerequisite chain must not collapse to one
    # week. Path starts at the placement floor and unfolds up the chain.
    skills = [_skill(i, f"s{i}", i) for i in range(1, 7)]
    selected = select_skills_for_roadmap(
        skills,
        mastery={i: 0.2 for i in range(1, 7)},
        placement_score=3,
        prereq_from_by_to={2: [1], 3: [2], 4: [3], 5: [4], 6: [5]},
        max_steps=10,
    )
    # diff 1 & 2 are below the floor (assumed known); path is weeks 3..6 in order.
    assert [s["id"] for s in selected] == [3, 4, 5, 6]


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
