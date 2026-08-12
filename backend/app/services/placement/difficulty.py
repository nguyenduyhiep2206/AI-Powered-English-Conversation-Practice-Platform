"""CEFR → difficulty band and fixed per-part band quotas for placement assemble."""

from __future__ import annotations

from typing import Any, Literal, Mapping

Band = Literal["easy", "mid", "hard"]

BANDS: tuple[Band, ...] = ("easy", "mid", "hard")

# Heuristic blueprint (not official ETS counts): P5 easier skew, P7 harder skew.
PART_BAND_QUOTA: dict[str, dict[Band, int]] = {
    "r5": {"easy": 15, "mid": 10, "hard": 5},
    "r6": {"easy": 4, "mid": 8, "hard": 4},
    "r7": {"easy": 8, "mid": 19, "hard": 27},
    "w1": {"easy": 3, "mid": 2, "hard": 0},
    "w2": {"easy": 0, "mid": 2, "hard": 0},
    "w3": {"easy": 0, "mid": 0, "hard": 1},
}

_CEFR_TO_BAND: dict[str, Band] = {
    "A1": "easy",
    "A2": "easy",
    "B1": "mid",
    "B2": "hard",
    "C1": "hard",
}

_DIFFICULTY_TO_BAND: dict[str, Band] = {
    "easy": "easy",
    "medium": "mid",
    "mid": "mid",
    "hard": "hard",
}


def band_quota_for_part(part: str) -> dict[Band, int]:
    """Return a copy of the band quota for a toeic_part."""
    if part not in PART_BAND_QUOTA:
        raise KeyError(f"Unknown toeic_part for band quota: {part}")
    return dict(PART_BAND_QUOTA[part])


def band_for_item(item: Mapping[str, Any]) -> Band:
    """
    Map an item to easy|mid|hard from CEFR only.

    Fallback: difficulty string easy|medium|hard. Else mid.
    """
    cefr = item.get("cefr_level")
    if cefr is not None:
        key = cefr.value if hasattr(cefr, "value") else str(cefr)
        key = key.strip().upper()
        if key in _CEFR_TO_BAND:
            return _CEFR_TO_BAND[key]

    raw = item.get("difficulty")
    if raw is not None:
        dkey = str(raw).strip().lower()
        if dkey in _DIFFICULTY_TO_BAND:
            return _DIFFICULTY_TO_BAND[dkey]

    return "mid"
