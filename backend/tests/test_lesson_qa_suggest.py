from app.services.lesson_qa_suggest import build_suggested_prompts


def test_suggest_uses_targets_not_generic_only():
    prompts = build_suggested_prompts(
        skill_title="Making a reservation",
        objective="Book a table politely",
        targets=["reservation", "I'd like"],
    )
    assert 3 <= len(prompts) <= 5
    joined = " ".join(prompts).lower()
    assert "reservation" in joined
    assert "i'd like" in joined or "i'd like" in joined.replace("'", "'")


def test_suggest_falls_back_to_skill_title():
    prompts = build_suggested_prompts(
        skill_title="Past simple",
        objective=None,
        targets=[],
    )
    assert 3 <= len(prompts) <= 5
    assert any("past simple" in p.lower() for p in prompts)
