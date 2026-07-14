from collections import Counter

from app.models.enums import CEFRLevel
from app.services.placement_service import (
    PLACEMENT_SIZE,
    PlacementCandidate,
    grade_placement_answer,
    placement_public_dict,
    score_to_level,
    select_from_candidates,
)


def test_score_to_level_matches_spec_table():
    assert score_to_level(0) == CEFRLevel.A1
    assert score_to_level(3) == CEFRLevel.A1
    assert score_to_level(4) == CEFRLevel.A2
    assert score_to_level(5) == CEFRLevel.A2
    assert score_to_level(6) == CEFRLevel.B1
    assert score_to_level(7) == CEFRLevel.B1
    assert score_to_level(8) == CEFRLevel.B2
    assert score_to_level(9) == CEFRLevel.B2
    assert score_to_level(10) == CEFRLevel.C1


def test_select_from_candidates_two_questions_per_level():
    cands: list[PlacementCandidate] = []
    n = 0
    for lvl in CEFRLevel:
        for i in range(3):
            n += 1
            cands.append(
                PlacementCandidate(
                    id=n,
                    skill_id=1000 + n,
                    cefr_level=lvl,
                    question_type="mcq",
                    stem=f"{lvl.value}-{i}",
                    options=["a", "b", "c", "d"],
                    difficulty="medium",
                    answer="a",
                )
            )
    picked = select_from_candidates(cands, rng_seed=42)
    assert len(picked) == PLACEMENT_SIZE
    counts = Counter(p.cefr_level for p in picked)
    assert all(counts[lvl] == 2 for lvl in CEFRLevel)


def test_select_raises_when_a_level_is_missing():
    cands = [
        PlacementCandidate(
            id=i,
            skill_id=1,
            cefr_level=CEFRLevel.B1,
            question_type="mcq",
            stem="x",
            options=["a", "b", "c", "d"],
            difficulty="medium",
            answer="a",
        )
        for i in range(10)
    ]
    try:
        select_from_candidates(cands, rng_seed=1)
        assert False, "expected ValueError"
    except ValueError as exc:
        assert "placement" in str(exc).lower() or "published" in str(exc).lower()


def test_prefers_mcq_and_avoids_duplicate_skill_within_level():
    cands = [
        PlacementCandidate(1, 10, CEFRLevel.A1, "mcq", "a1", ["a", "b", "c", "d"], "medium", "a"),
        PlacementCandidate(2, 11, CEFRLevel.A1, "mcq", "a2", ["a", "b", "c", "d"], "medium", "a"),
        PlacementCandidate(3, 12, CEFRLevel.A1, "cloze", "a3", None, "medium", "x"),
        PlacementCandidate(4, 20, CEFRLevel.A2, "mcq", "s", ["a", "b", "c", "d"], "medium", "a"),
        PlacementCandidate(5, 21, CEFRLevel.A2, "mcq", "t", ["a", "b", "c", "d"], "medium", "a"),
        PlacementCandidate(6, 20, CEFRLevel.B1, "mcq", "s", ["a", "b", "c", "d"], "medium", "a"),
        PlacementCandidate(7, 21, CEFRLevel.B1, "mcq", "t", ["a", "b", "c", "d"], "medium", "a"),
        PlacementCandidate(8, 20, CEFRLevel.B2, "mcq", "s", ["a", "b", "c", "d"], "medium", "a"),
        PlacementCandidate(9, 21, CEFRLevel.B2, "mcq", "t", ["a", "b", "c", "d"], "medium", "a"),
        PlacementCandidate(10, 20, CEFRLevel.C1, "mcq", "s", ["a", "b", "c", "d"], "medium", "a"),
        PlacementCandidate(11, 21, CEFRLevel.C1, "mcq", "t", ["a", "b", "c", "d"], "medium", "a"),
    ]
    picked = select_from_candidates(cands, rng_seed=7)
    a1 = [p for p in picked if p.cefr_level == CEFRLevel.A1]
    assert len(a1) == 2
    assert all(p.question_type == "mcq" for p in a1)
    assert len({p.skill_id for p in a1}) == 2


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
    )
    d = placement_public_dict(c)
    assert "answer" not in d
    assert d["id"] == 9
    assert d["cefr_level"] == "B1"
