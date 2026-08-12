"""Tests for TOEIC placement assembler and score mapping."""

from collections import Counter, defaultdict
from random import Random

import pytest

from app.services.placement.assembler import (
    BankTooSmallError,
    _GROUP_TOTAL_TOLERANCE,
    assemble_form,
)
from app.services.placement.difficulty import PART_BAND_QUOTA, band_for_item
from app.services.placement.score_map import (
    blend_to_cefr,
    placement_sublevel,
    reading_scale,
    writing_scale,
)

_CEFR = {"easy": "A2", "mid": "B1", "hard": "B2"}


def _item(
    iid: int,
    part: str,
    *,
    cefr: str = "B1",
    passage_id: int | None = None,
    stem: str | None = None,
) -> dict:
    return {
        "id": iid,
        "toeic_part": part,
        "stem": stem or f"stem {iid}",
        "options": ["a", "b", "c", "d"] if part.startswith("r") else None,
        "answer": "a",
        "skill_id": 1,
        "cefr_level": cefr,
        "difficulty": "medium",
        "passage_id": passage_id,
        "prompt_words": None,
        "media_url": None,
        "task_brief": None,
        "question_type": "mcq" if part.startswith("r") else "writing",
    }


def _pool_for_part(
    part: str,
    *,
    start_id: int,
    passage_start: int = 1,
    extra_per_band: int = 0,
    group_size: int = 1,
) -> tuple[list[dict], int, int, dict[int, dict]]:
    """Build a pool that covers PART_BAND_QUOTA[part] (optionally with extras)."""
    items: list[dict] = []
    passages: dict[int, dict] = {}
    iid = start_id
    pid = passage_start
    use_passage = part in {"r6", "r7", "w2"}
    gsize = group_size if use_passage and part in {"r6", "r7"} else 1
    for band, n in PART_BAND_QUOTA[part].items():
        total = n + extra_per_band
        if gsize > 1 and total % gsize:
            total += gsize - (total % gsize)
        made = 0
        while made < total:
            chunk = min(gsize, total - made)
            blank_order = list(range(1, chunk + 1))
            if part == "r6" and chunk >= 3:
                blank_order = [2, 3, 1] + blank_order[3:]
                blanks = " ".join(f"------- ({j})" for j in range(1, chunk + 1))
                body = f"Doc {pid}. {blanks}"
            elif use_passage:
                body = f"Doc {pid}."
            else:
                body = None
            for blank_n in blank_order:
                stem = (
                    f"Choose the best answer for blank ({blank_n})."
                    if part == "r6" and chunk >= 3
                    else f"stem {iid}"
                )
                items.append(
                    _item(
                        iid,
                        part,
                        cefr=_CEFR[band],
                        passage_id=pid if use_passage else None,
                        stem=stem,
                    )
                )
                iid += 1
                made += 1
            if use_passage:
                passages[pid] = {"id": pid, "body": body}
                pid += 1
    return items, iid, pid, passages


def _banded_bank(*, r6_group_size: int = 1, r7_group_size: int = 1):
    items: dict[str, list[dict]] = {}
    passages: dict[int, dict] = {}
    iid = 1
    pid = 1
    for part in ("r5", "r6", "r7", "w1", "w2", "w3"):
        gsize = 1
        if part == "r6":
            gsize = r6_group_size
        elif part == "r7":
            gsize = r7_group_size
        part_items, iid, pid, part_passages = _pool_for_part(
            part,
            start_id=iid,
            passage_start=pid,
            extra_per_band=max(2, gsize),
            group_size=gsize,
        )
        items[part] = part_items
        passages.update(part_passages)
    # Flat parts may not create passages; keep ids for writing w2 etc.
    for p in range(1, pid + 1):
        passages.setdefault(p, {"id": p, "body": f"p{p}"})
    return items, passages


def test_assemble_raises_when_r5_short():
    with pytest.raises(BankTooSmallError, match="r5"):
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


def test_assemble_raises_when_r5_hard_missing():
    easy_mid = (
        [_item(i, "r5", cefr="A2") for i in range(15)]
        + [_item(100 + i, "r5", cefr="B1") for i in range(10)]
    )
    with pytest.raises(BankTooSmallError, match=r"r5/hard"):
        assemble_form(
            {
                "r5": easy_mid,
                "r6": [],
                "r7": [],
                "w1": [],
                "w2": [],
                "w3": [],
            },
            {},
            rng=Random(0),
        )


def test_assemble_full_quotas_matches_part_curve():
    items, passages = _banded_bank()
    form = assemble_form(items, passages, rng=Random(1))
    assert len(form["reading_items"]) == 100
    assert len(form["writing_items"]) == 8
    assert len(form["_reading_ids"]) == 100

    by_part: dict[str, list[dict]] = {}
    for row in form["reading_items"] + form["writing_items"]:
        by_part.setdefault(row["toeic_part"], []).append(row)

    for part, quota in PART_BAND_QUOTA.items():
        part_items = by_part[part]
        assert len(part_items) == sum(quota.values())
        counts = Counter(band_for_item(i) for i in part_items)
        for band, need in quota.items():
            # Flat parts exact; group parts allow ±1 per assembler rule
            if part in {"r6", "r7"}:
                assert abs(counts[band] - need) <= 1
            else:
                assert counts[band] == need


def test_r6_keeps_whole_passage_groups():
    """Multi-blank Part 6 sets must stay intact (no mid-passage slice)."""
    items, passages = _banded_bank(r6_group_size=4, r7_group_size=3)
    form = assemble_form(items, passages, rng=Random(7))

    r6 = [i for i in form["reading_items"] if i["toeic_part"] == "r6"]
    r7 = [i for i in form["reading_items"] if i["toeic_part"] == "r7"]
    assert sum(PART_BAND_QUOTA["r6"].values()) <= len(r6) <= 16 + _GROUP_TOTAL_TOLERANCE
    assert sum(PART_BAND_QUOTA["r7"].values()) <= len(r7) <= 54 + _GROUP_TOTAL_TOLERANCE

    pool_r6_by_pid: dict[int, list[dict]] = defaultdict(list)
    for it in items["r6"]:
        pool_r6_by_pid[int(it["passage_id"])].append(it)

    by_pid: dict[int, list[dict]] = defaultdict(list)
    for it in r6:
        by_pid[int(it["passage_id"])].append(it)

    for pid, chosen in by_pid.items():
        assert len(chosen) == len(pool_r6_by_pid[pid])
        assert len(chosen) == 4
        from app.services.placement.assembler import blank_index_from_stem

        blanks = [blank_index_from_stem(it.get("stem")) for it in chosen]
        assert blanks == list(range(1, 5))

    pool_r7_by_pid: dict[int, list[dict]] = defaultdict(list)
    for it in items["r7"]:
        pool_r7_by_pid[int(it["passage_id"])].append(it)
    by_pid_r7: dict[int, list[dict]] = defaultdict(list)
    for it in r7:
        by_pid_r7[int(it["passage_id"])].append(it)
    for pid, chosen in by_pid_r7.items():
        assert len(chosen) == len(pool_r7_by_pid[pid])
        assert len(chosen) == 3


def test_r6_skips_incomplete_blank_sets():
    """Passage with 3 blanks but only 1 published item must not be selected."""
    from app.services.placement.assembler import blank_index_from_stem

    items, passages = _banded_bank(r6_group_size=4, r7_group_size=1)
    bad_pid = 9001
    passages[bad_pid] = {
        "id": bad_pid,
        "body": "Memo ------- (1). More ------- (2). End ------- (3).",
    }
    items["r6"].append(
        _item(
            90001,
            "r6",
            cefr="B1",
            passage_id=bad_pid,
            stem="Choose the best answer for blank (1).",
        )
    )
    form = assemble_form(items, passages, rng=Random(3))
    r6_pids = {
        int(i["passage_id"])
        for i in form["reading_items"]
        if i["toeic_part"] == "r6" and i.get("passage_id") is not None
    }
    assert bad_pid not in r6_pids
    for it in form["reading_items"]:
        if it["toeic_part"] != "r6":
            continue
        # Within each contiguous group, blanks ascend when present
    by_pid: dict[int, list[dict]] = defaultdict(list)
    for it in form["reading_items"]:
        if it["toeic_part"] == "r6" and it.get("passage_id") is not None:
            by_pid[int(it["passage_id"])].append(it)
    for group in by_pid.values():
        idxs = [blank_index_from_stem(i.get("stem")) for i in group]
        assert idxs == sorted(idxs)


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
