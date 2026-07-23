from app.models.enums import CEFRLevel
from app.services.placement_service import (
    PlacementCandidate,
    grade_placement_answer,
    placement_public_dict,
)


def test_grade_placement_answer_uses_case_insensitive_match():
    assert grade_placement_answer("Has gone", "has gone") is True
    assert grade_placement_answer("x", "y") is False


def test_placement_public_dict_omits_answer():
    c = PlacementCandidate(
        id=9,
        skill_id=1,
        cefr_level=CEFRLevel.B1,
        question_type="mcq",
        stem="Stem",
        options=["a", "b", "c", "d"],
        difficulty="easy",
        answer="SECRET",
        passage="Once upon a time…",
    )
    d = placement_public_dict(c)
    assert "answer" not in d
    assert d["id"] == 9
    assert d["cefr_level"] == "B1"
    assert d["passage"] == "Once upon a time…"
