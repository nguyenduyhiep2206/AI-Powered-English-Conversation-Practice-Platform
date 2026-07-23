from app.models.enums import CEFRLevel, WeakPointEnum
from app.services.placement.adaptive_engine import (
    MAX_QUESTIONS,
    MIN_QUESTIONS,
    map_ability_to_profile,
    pick_next_candidate,
    preferred_skill_types,
    should_stop,
    update_ability,
)
from app.services.placement.bank import PlacementCandidate


def test_preferred_skill_types_mapping():
    assert "grammar" in preferred_skill_types(WeakPointEnum.grammar)
    assert "vocabulary" in preferred_skill_types(WeakPointEnum.vocabulary)
    assert "functional" in preferred_skill_types(WeakPointEnum.writing)
    assert preferred_skill_types(WeakPointEnum.confidence) == frozenset()
    assert preferred_skill_types(None) == frozenset()


def test_update_ability_correct_increases():
    a, c = update_ability(1.0, 0.0, item_level=1.0, correct=True)
    assert a > 1.0
    assert 0.0 <= c <= 1.0


def test_update_ability_wrong_decreases():
    a, _c = update_ability(1.0, 0.5, item_level=1.0, correct=False)
    assert a < 1.0


def test_should_stop_rules():
    assert should_stop(5, 1.0) is False
    assert should_stop(6, 0.84) is False
    assert should_stop(6, 0.85) is True
    assert should_stop(MAX_QUESTIONS, 0.0) is True
    assert MIN_QUESTIONS == 6


def test_map_ability_to_profile_bounds():
    level, sub = map_ability_to_profile(0.0)
    assert level == CEFRLevel.A1
    assert 1 <= sub <= 10
    level, sub = map_ability_to_profile(4.0)
    assert level == CEFRLevel.C1
    assert 1 <= sub <= 10
    level, _ = map_ability_to_profile(2.2)
    assert level == CEFRLevel.B1


def _cand(id_: int, skill_id: int, level: CEFRLevel) -> PlacementCandidate:
    return PlacementCandidate(
        id=id_,
        skill_id=skill_id,
        cefr_level=level,
        question_type="mcq",
        stem="s",
        options=["a", "b"],
        difficulty="medium",
        answer="a",
    )


def test_pick_next_prefers_target_cefr_and_weak_point():
    cands = [
        _cand(1, 10, CEFRLevel.A1),
        _cand(2, 11, CEFRLevel.A2),
        _cand(3, 12, CEFRLevel.A2),
        _cand(4, 13, CEFRLevel.B1),
    ]
    skill_types = {10: "grammar", 11: "vocabulary", 12: "grammar", 13: "grammar"}
    picked = pick_next_candidate(
        cands,
        ability_index=1.0,
        seen_ids=set(),
        used_skill_ids=set(),
        weak_point=WeakPointEnum.grammar,
        skill_types_by_skill_id=skill_types,
        rng_seed=1,
    )
    assert picked.cefr_level == CEFRLevel.A2
    assert skill_types[picked.skill_id] == "grammar"
