from app.services.weak_skill_review import pick_weak


def test_pick_weak_skills_orders_by_mastery_asc():
    rows = [{"skill_id": 1, "mastery": 0.9}, {"skill_id": 2, "mastery": 0.2}]
    assert [r["skill_id"] for r in pick_weak(rows, threshold=0.7, limit=5)] == [2]


def test_pick_weak_respects_limit():
    rows = [
        {"skill_id": 1, "mastery": 0.1},
        {"skill_id": 2, "mastery": 0.2},
        {"skill_id": 3, "mastery": 0.3},
    ]
    out = pick_weak(rows, threshold=0.7, limit=2)
    assert [r["skill_id"] for r in out] == [1, 2]


def test_pick_weak_excludes_at_or_above_threshold():
    rows = [{"skill_id": 1, "mastery": 0.7}, {"skill_id": 2, "mastery": 0.69}]
    assert [r["skill_id"] for r in pick_weak(rows, threshold=0.7, limit=5)] == [2]
