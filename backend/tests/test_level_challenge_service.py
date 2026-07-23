import pytest

from app.models.enums import CEFRLevel
from app.services.level_challenge_service import (
    _parse_challenge_answer_ids,
    challenge_score_to_placement,
    next_cefr_level,
    sample_challenge_candidates,
)
from app.services.placement.bank import PlacementCandidate


def test_next_cefr():
    assert next_cefr_level(CEFRLevel.A1) == CEFRLevel.A2
    assert next_cefr_level(CEFRLevel.B2) == CEFRLevel.C1
    assert next_cefr_level(CEFRLevel.C1) is None


def test_challenge_score_to_placement():
    assert challenge_score_to_placement(4, 6) >= 1
    assert challenge_score_to_placement(6, 6) == 10
    assert challenge_score_to_placement(0, 6) == 1


def _cand(qid: int, skill_id: int) -> PlacementCandidate:
    return PlacementCandidate(
        id=qid,
        skill_id=skill_id,
        cefr_level=CEFRLevel.A2,
        question_type="mcq",
        stem=f"Q{qid}",
        options=["a", "b"],
        difficulty="medium",
        answer="a",
        passage=None,
    )


def test_sample_challenge_prefers_unique_skills():
    pool = [_cand(i, skill_id=i) for i in range(1, 10)]
    picked = sample_challenge_candidates(pool, size=6, rng_seed=1)
    assert len(picked) == 6
    assert len({c.skill_id for c in picked}) == 6


def test_parse_challenge_answer_ids_ok():
    answers = [{"question_id": i, "answer": "a"} for i in range(1, 7)]
    assert _parse_challenge_answer_ids(answers) == [1, 2, 3, 4, 5, 6]


def test_parse_challenge_answer_ids_rejects_dupes():
    answers = [{"question_id": 1, "answer": "a"} for _ in range(6)]
    with pytest.raises(ValueError, match="trùng"):
        _parse_challenge_answer_ids(answers)
