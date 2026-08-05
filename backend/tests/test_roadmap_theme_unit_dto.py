from app.services.roadmap_assembler_service import attach_theme_unit_fields


def test_attach_theme_unit_fields():
    week = {"skill_id": 10, "skill_slug": "be_present"}
    out = attach_theme_unit_fields(
        week,
        {
            10: {
                "slug": "a1_be_basics",
                "title": "Basics with be",
                "can_do": "I can…",
                "position": 1,
            }
        },
    )
    assert out["theme_unit_slug"] == "a1_be_basics"
    assert out["theme_unit_title"] == "Basics with be"
    assert out["theme_unit_can_do"] == "I can…"
    assert out["theme_unit_position"] == 1


def test_attach_theme_unit_fields_missing():
    out = attach_theme_unit_fields({"skill_id": 99}, {})
    assert out["theme_unit_slug"] is None
    assert out["theme_unit_position"] is None
