"""Pure adaptive placement engine (no DB / IRT)."""

from __future__ import annotations

import math
import random
from typing import Sequence

from app.models.enums import CEFRLevel
from app.services.placement.bank import CEFR_ORDER, PlacementCandidate

MIN_QUESTIONS = 6
MAX_QUESTIONS = 15
CONFIDENCE_STOP = 0.85
ABILITY_STEP = 0.45

_CEFR_INDEX = {lvl: i for i, lvl in enumerate(CEFR_ORDER)}


def cefr_index(level: CEFRLevel) -> int:
    return _CEFR_INDEX[level]


def update_ability(
    ability_index: float,
    confidence: float,
    *,
    item_level: float,
    correct: bool,
) -> tuple[float, float]:
    before = float(ability_index)
    conf = float(confidence)
    if correct:
        delta = ABILITY_STEP * (1.0 + 0.25 * max(0.0, item_level - before))
        ability = before + delta
    else:
        delta = ABILITY_STEP * (1.0 + 0.25 * max(0.0, before - item_level))
        ability = before - delta
    ability = max(0.0, min(4.0, ability))

    surprise = abs(item_level - before)
    expected_ok = correct and item_level >= before - 0.5
    expected_miss = (not correct) and item_level <= before + 0.5
    if expected_ok or expected_miss:
        conf += 0.12 + 0.03 * surprise
    else:
        conf -= 0.08
    conf = max(0.0, min(1.0, conf))
    return ability, conf


def should_stop(asked: int, confidence: float) -> bool:
    if asked >= MAX_QUESTIONS:
        return True
    if asked >= MIN_QUESTIONS and float(confidence) >= CONFIDENCE_STOP:
        return True
    return False


def map_ability_to_profile(ability_index: float) -> tuple[CEFRLevel, int]:
    a = max(0.0, min(4.0, float(ability_index)))
    idx = int(round(a))
    idx = max(0, min(4, idx))
    level = CEFR_ORDER[idx]
    low = idx - 0.5
    high = idx + 0.5
    frac = (a - low) / (high - low) if high > low else 0.5
    frac = max(0.0, min(1.0, frac))
    sub = max(1, min(10, int(math.floor(frac * 9)) + 1))
    return level, sub


def pick_next_candidate(
    candidates: Sequence[PlacementCandidate],
    *,
    ability_index: float,
    seen_ids: set[int],
    used_skill_ids: set[int],
    rng_seed: int | None = None,
) -> PlacementCandidate:
    """Pick next item near ability CEFR; prefer unused skills; no weak_point bias."""
    rng = random.Random(rng_seed)
    target_idx = max(0, min(4, int(round(float(ability_index)))))
    pool = [c for c in candidates if int(c.id) not in seen_ids]
    if not pool:
        raise ValueError("Không còn câu hỏi published phù hợp cho placement adaptive.")

    def at_levels(indexes: set[int]) -> list[PlacementCandidate]:
        return [c for c in pool if cefr_index(c.cefr_level) in indexes]

    window = at_levels({target_idx})
    if not window:
        window = at_levels({target_idx - 1, target_idx, target_idx + 1} & {0, 1, 2, 3, 4})
    if not window:
        raise ValueError("Không còn câu hỏi published phù hợp cho placement adaptive.")

    def sort_key(c: PlacementCandidate) -> tuple:
        unused = 0 if int(c.skill_id) not in used_skill_ids else 1
        return (unused, rng.random())

    return sorted(window, key=sort_key)[0]
