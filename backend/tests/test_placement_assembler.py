"""Tests for TOEIC placement assembler and score mapping."""

from random import Random

import pytest

from app.services.placement.assembler import BankTooSmallError, assemble_form
from app.services.placement.score_map import (
    blend_to_cefr,
    placement_sublevel,
    reading_scale,
    writing_scale,
)


def _item(iid: int, part: str, passage_id: int | None = None) -> dict:
    return {
        "id": iid,
        "toeic_part": part,
        "stem": f"stem {iid}",
        "options": ["a", "b", "c", "d"] if part.startswith("r") else None,
        "answer": "a",
        "skill_id": 1,
        "cefr_level": "B1",
        "passage_id": passage_id,
        "prompt_words": None,
        "media_url": None,
        "task_brief": None,
        "question_type": "mcq" if part.startswith("r") else "writing",
    }


def test_assemble_raises_when_r5_short():
    with pytest.raises(BankTooSmallError):
        assemble_form(
            {
                "r5": [_item(i, "r5") for i in range(10)],
                "r6": [],
                "r7": [],
                "w1": [],
                "w2": [],
                "w3": [],
            },
            {},
            rng=Random(0),
        )


def test_assemble_full_quotas():
    items = {
        "r5": [_item(i, "r5") for i in range(30)],
        "r6": [_item(100 + i, "r6", passage_id=1 + (i // 4)) for i in range(16)],
        "r7": [_item(200 + i, "r7", passage_id=10 + (i // 3)) for i in range(54)],
        "w1": [_item(300 + i, "w1") for i in range(5)],
        "w2": [_item(310 + i, "w2", passage_id=50) for i in range(2)],
        "w3": [_item(320, "w3")],
    }
    passages = {pid: {"id": pid, "body": f"p{pid}"} for pid in range(1, 60)}
    form = assemble_form(items, passages, rng=Random(1))
    assert len(form["reading_items"]) == 100
    assert len(form["writing_items"]) == 8
    assert len(form["_reading_ids"]) == 100


def test_reading_scale_full():
    assert reading_scale(100) == 495
    assert reading_scale(0) == 5


def test_writing_scale_full():
    assert writing_scale(28) == 200
    assert writing_scale(0) == 0


def test_blend_min_wins():
    assert blend_to_cefr(450, 40) == "A1"
    assert blend_to_cefr(450, 170) == "C1"


def test_placement_sublevel_in_range():
    level = blend_to_cefr(250, 100)
    sub = placement_sublevel(250, 100, level)
    assert 1 <= sub <= 10
