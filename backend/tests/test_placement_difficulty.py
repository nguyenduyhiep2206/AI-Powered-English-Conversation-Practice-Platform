"""Unit tests for placement difficulty bands and part-curve quotas."""

import pytest

from app.services.placement.difficulty import (
    PART_BAND_QUOTA,
    band_for_item,
    band_quota_for_part,
)
from app.services.placement.quotas import READING_QUOTA, WRITING_QUOTA


@pytest.mark.parametrize(
    ("cefr", "expected"),
    [
        ("A1", "easy"),
        ("A2", "easy"),
        ("B1", "mid"),
        ("B2", "hard"),
        ("C1", "hard"),
        ("a2", "easy"),
    ],
)
def test_band_from_cefr(cefr: str, expected: str):
    assert band_for_item({"cefr_level": cefr}) == expected


def test_band_fallback_difficulty_string():
    assert band_for_item({"difficulty": "easy"}) == "easy"
    assert band_for_item({"difficulty": "medium"}) == "mid"
    assert band_for_item({"difficulty": "hard"}) == "hard"


def test_band_default_mid_when_missing():
    assert band_for_item({}) == "mid"


def test_cefr_wins_over_difficulty_string():
    assert band_for_item({"cefr_level": "A1", "difficulty": "hard"}) == "easy"


def test_part_band_quota_sums_match_part_totals():
    for part, total in {**READING_QUOTA, **WRITING_QUOTA}.items():
        q = band_quota_for_part(part)
        assert sum(q.values()) == total
        assert q == PART_BAND_QUOTA[part]


def test_unknown_part_raises():
    with pytest.raises(KeyError):
        band_quota_for_part("r1")
