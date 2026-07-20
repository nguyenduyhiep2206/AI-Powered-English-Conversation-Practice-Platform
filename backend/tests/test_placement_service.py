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


def test_avoids_duplicate_skill_within_level_without_preferring_mcq():
    cands = [
        PlacementCandidate(1, 10, CEFRLevel.A1, "mcq", "a1", ["a", "b", "c", "d"], "medium", "a"),
        PlacementCandidate(2, 11, CEFRLevel.A1, "cloze", "a2", None, "medium", "x"),
        PlacementCandidate(3, 12, CEFRLevel.A1, "fix_grammar", "a3", None, "medium", "y"),
        PlacementCandidate(4, 20, CEFRLevel.A2, "mcq", "s", ["a", "b", "c", "d"], "medium", "a"),
        PlacementCandidate(5, 21, CEFRLevel.A2, "cloze", "t", None, "medium", "b"),
        PlacementCandidate(6, 20, CEFRLevel.B1, "mcq", "s", ["a", "b", "c", "d"], "medium", "a"),
        PlacementCandidate(7, 21, CEFRLevel.B1, "fix_grammar", "t", None, "medium", "c"),
        PlacementCandidate(8, 20, CEFRLevel.B2, "cloze", "s", None, "medium", "d"),
        PlacementCandidate(9, 21, CEFRLevel.B2, "mcq", "t", ["a", "b", "c", "d"], "medium", "a"),
        PlacementCandidate(10, 20, CEFRLevel.C1, "fix_grammar", "s", None, "medium", "e"),
        PlacementCandidate(11, 21, CEFRLevel.C1, "cloze", "t", None, "medium", "f"),
    ]
    picked = select_from_candidates(cands, rng_seed=7)
    a1 = [p for p in picked if p.cefr_level == CEFRLevel.A1]
    assert len(a1) == 2
    assert len({p.skill_id for p in a1}) == 2
    # Must not force both A1 picks to be mcq anymore.
    assert not all(p.question_type == "mcq" for p in a1)


def test_spreads_question_types_when_bank_is_balanced():
    """With ample mix per level, overall type counts should be nearly even."""
    cands: list[PlacementCandidate] = []
    n = 0
    types = ("mcq", "cloze", "fix_grammar")
    for lvl in CEFRLevel:
        for t_i, qtype in enumerate(types):
            for dup in range(2):
                n += 1
                cands.append(
                    PlacementCandidate(
                        id=n,
                        skill_id=1000 + n,
                        cefr_level=lvl,
                        question_type=qtype,
                        stem=f"{lvl.value}-{qtype}-{dup}",
                        options=["a", "b", "c", "d"] if qtype == "mcq" else None,
                        difficulty="medium",
                        answer="a" if qtype == "mcq" else "x",
                    )
                )
    picked = select_from_candidates(cands, rng_seed=99)
    counts = Counter(p.question_type for p in picked)
    assert len(picked) == PLACEMENT_SIZE
    # 10 items / 3 types → counts differ by at most 1 (e.g. 4/3/3)
    assert max(counts.values()) - min(counts.values()) <= 1
    assert set(counts) == set(types)


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
