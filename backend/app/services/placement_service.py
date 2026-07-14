"""Placement test helpers: sample published quiz bank and map score to CEFR.

Roadmap assemble is intentionally out of scope here.
"""

from __future__ import annotations

import random
from collections import defaultdict
from dataclasses import dataclass
from typing import Sequence

from app.models.enums import CEFRLevel

PLACEMENT_SIZE = 10
PER_LEVEL = 2
CEFR_ORDER: tuple[CEFRLevel, ...] = (
    CEFRLevel.A1,
    CEFRLevel.A2,
    CEFRLevel.B1,
    CEFRLevel.B2,
    CEFRLevel.C1,
)
INSUFFICIENT_BANK_MSG = (
    "Chưa đủ câu hỏi published cho placement (cần 10 câu trải A1–C1)."
)


@dataclass(frozen=True)
class PlacementCandidate:
    id: int
    skill_id: int
    cefr_level: CEFRLevel
    question_type: str
    stem: str
    options: list[str] | None
    difficulty: str
    answer: str


def score_to_level(score: int) -> CEFRLevel:
    if score <= 3:
        return CEFRLevel.A1
    if score <= 5:
        return CEFRLevel.A2
    if score <= 7:
        return CEFRLevel.B1
    if score <= 9:
        return CEFRLevel.B2
    return CEFRLevel.C1


def _type_rank(question_type: str) -> int:
    """Lower rank is preferred (mcq first)."""
    if question_type == "mcq":
        return 0
    if question_type == "cloze":
        return 1
    return 2


def select_from_candidates(
    candidates: Sequence[PlacementCandidate],
    *,
    rng_seed: int | None = None,
) -> list[PlacementCandidate]:
    rng = random.Random(rng_seed)
    by_level: dict[CEFRLevel, list[PlacementCandidate]] = defaultdict(list)
    for c in candidates:
        by_level[c.cefr_level].append(c)

    picked: list[PlacementCandidate] = []
    for level in CEFR_ORDER:
        pool = list(by_level.get(level, []))
        if len(pool) < PER_LEVEL:
            raise ValueError(INSUFFICIENT_BANK_MSG)

        # Shuffle for variety, then stable-sort so mcq stays preferred.
        rng.shuffle(pool)
        pool.sort(key=lambda c: _type_rank(c.question_type))

        chosen: list[PlacementCandidate] = []
        used_skills: set[int] = set()
        for c in pool:
            if len(chosen) >= PER_LEVEL:
                break
            if c.skill_id in used_skills:
                continue
            chosen.append(c)
            used_skills.add(c.skill_id)

        if len(chosen) < PER_LEVEL:
            for c in pool:
                if len(chosen) >= PER_LEVEL:
                    break
                if c in chosen:
                    continue
                chosen.append(c)

        if len(chosen) < PER_LEVEL:
            raise ValueError(INSUFFICIENT_BANK_MSG)
        picked.extend(chosen[:PER_LEVEL])

    if len(picked) != PLACEMENT_SIZE:
        raise ValueError(INSUFFICIENT_BANK_MSG)

    rng.shuffle(picked)
    return picked
