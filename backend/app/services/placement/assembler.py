"""Assemble a timed TOEIC R+W form snapshot from published quiz bank items."""

from __future__ import annotations

import re
from collections import Counter, defaultdict
from random import Random
from typing import Any

from app.services.passage_text import strip_embedded_mcq_choice_blocks
from app.services.placement.difficulty import (
    BANDS,
    Band,
    band_for_item,
    band_quota_for_part,
)
from app.services.placement.quotas import READING_QUOTA, WRITING_QUOTA

_BAND_TIE_ORDER = {"mid": 0, "easy": 1, "hard": 2}
_STRATA_TOLERANCE = 1
# Allow slight overshoot of part total so r6/r7 never split a passage set.
_GROUP_TOTAL_TOLERANCE = 3
_PASSAGE_BLANK_RE = re.compile(r"-{3,}\s*\((\d+)\)")
_STEM_BLANK_RE = re.compile(r"blank\s*\((\d+)\)", re.IGNORECASE)


class BankTooSmallError(Exception):
    """Published pool cannot satisfy TOEIC placement quotas."""


def assemble_form(
    items_by_part: dict[str, list[dict[str, Any]]],
    passages: dict[int, dict[str, Any]],
    *,
    rng: Random | None = None,
) -> dict[str, Any]:
    """
    Return form_snapshot with reading_items, writing_items, and passages used.

    Each item dict must include at least: id, toeic_part, stem, options, answer,
    skill_id, cefr_level (or difficulty), passage_id (optional), prompt_words,
    media_url, task_brief.
    Selection follows PART_BAND_QUOTA (CEFR → easy/mid/hard).
    R6/R7 selection keeps whole passage groups (may overshoot part quota slightly).
    """
    rng = rng or Random()
    reading_items: list[dict[str, Any]] = []
    writing_items: list[dict[str, Any]] = []
    used_passage_ids: set[int] = set()

    for part, need in READING_QUOTA.items():
        pool = list(items_by_part.get(part) or [])
        if part in {"r6", "r7"}:
            selected, pids = _pick_passage_groups_banded(
                pool, part, passages=passages, rng=rng
            )
            if len(selected) < need:
                raise BankTooSmallError(
                    f"Need {need} published {part} items, have {len(selected)}"
                )
            if len(selected) > need + _GROUP_TOTAL_TOLERANCE:
                raise BankTooSmallError(
                    f"Need ~{need} published {part} items (±{_GROUP_TOTAL_TOLERANCE} "
                    f"whole groups), have {len(selected)}"
                )
        else:
            selected, pids = _pick_flat_banded(pool, part, rng=rng)
            if len(selected) < need:
                raise BankTooSmallError(
                    f"Need {need} published {part} items, have {len(selected)}"
                )
        reading_items.extend(selected)
        used_passage_ids.update(pids)

    for part, need in WRITING_QUOTA.items():
        pool = list(items_by_part.get(part) or [])
        selected, pids = _pick_flat_banded(pool, part, rng=rng)
        if len(selected) < need:
            raise BankTooSmallError(
                f"Need {need} published {part} items, have {len(selected)}"
            )
        writing_items.extend(selected)
        used_passage_ids.update(pids)

    snapshot_passages = {}
    for pid in used_passage_ids:
        if pid not in passages:
            continue
        raw = passages[pid]
        body = strip_embedded_mcq_choice_blocks(
            raw.get("body") if isinstance(raw, dict) else None
        )
        if isinstance(raw, dict):
            snapshot_passages[str(pid)] = {**raw, "body": body}
        else:
            snapshot_passages[str(pid)] = raw
    reading_items = _dedupe_by_id(reading_items)
    writing_items = _dedupe_by_id(writing_items)
    return {
        "reading_items": [_public_item(i, include_answer=False) for i in reading_items],
        "writing_items": [_public_item(i, include_answer=False) for i in writing_items],
        "passages": snapshot_passages,
        "_answers": {str(i["id"]): i.get("answer") for i in reading_items},
        "_reading_ids": [i["id"] for i in reading_items],
        "_writing_ids": [i["id"] for i in writing_items],
        "_items": {str(i["id"]): i for i in reading_items + writing_items},
    }


def _dedupe_by_id(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[int] = set()
    out: list[dict[str, Any]] = []
    for item in items:
        iid = int(item["id"])
        if iid in seen:
            continue
        seen.add(iid)
        out.append(item)
    return out


def _band_counts(items: list[dict[str, Any]]) -> dict[Band, int]:
    counts: dict[Band, int] = {b: 0 for b in BANDS}
    for item in items:
        counts[band_for_item(item)] += 1
    return counts


def _require_pool_band(
    part: str, band: Band, need: int, have: int
) -> None:
    if have < need:
        raise BankTooSmallError(
            f"Need {need} published {part}/{band}, have {have}"
        )


def _pick_flat_banded(
    pool: list[dict[str, Any]], part: str, *, rng: Random
) -> tuple[list[dict[str, Any]], set[int]]:
    pool = _dedupe_by_id(pool)
    targets = band_quota_for_part(part)
    by_band: dict[Band, list[dict[str, Any]]] = defaultdict(list)
    for item in pool:
        by_band[band_for_item(item)].append(item)

    selected: list[dict[str, Any]] = []
    for band in BANDS:
        need = int(targets.get(band, 0))
        if need <= 0:
            continue
        bucket = by_band.get(band) or []
        _require_pool_band(part, band, need, len(bucket))
        selected.extend(rng.sample(bucket, need))

    pids = {
        int(i["passage_id"])
        for i in selected
        if i.get("passage_id") is not None
    }
    return selected, pids


def _majority_band(items: list[dict[str, Any]]) -> Band:
    counts = Counter(band_for_item(i) for i in items)
    return min(counts.keys(), key=lambda b: (-counts[b], _BAND_TIE_ORDER[b]))


def blank_index_from_stem(stem: str | None) -> int:
    """Parse 'blank (n)' from a Part 6 stem; unknown → large sort key."""
    if not stem:
        return 10_000
    match = _STEM_BLANK_RE.search(stem)
    return int(match.group(1)) if match else 10_000


def _passage_blank_numbers(body: str | None) -> set[int]:
    if not body:
        return set()
    return {int(n) for n in _PASSAGE_BLANK_RE.findall(body)}


def _sort_group_items(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(
        items,
        key=lambda i: (blank_index_from_stem(i.get("stem")), int(i["id"])),
    )


def _r6_group_is_complete(
    items: list[dict[str, Any]], passage_body: str | None
) -> bool:
    """True when published items cover every numbered blank in the passage."""
    blanks = _passage_blank_numbers(passage_body)
    if not blanks:
        # No markers to verify (legacy / non-standard body) — keep the set.
        return len(items) >= 1
    stem_blanks = {
        blank_index_from_stem(i.get("stem"))
        for i in items
        if blank_index_from_stem(i.get("stem")) < 10_000
    }
    return blanks <= stem_blanks and len(items) >= len(blanks)


def _pick_passage_groups_banded(
    pool: list[dict[str, Any]],
    part: str,
    *,
    passages: dict[int, dict[str, Any]] | None = None,
    rng: Random,
) -> tuple[list[dict[str, Any]], set[int]]:
    """
    Keep whole passage groups; fill PART_BAND_QUOTA with ±1 per band when possible.

    Never splits a passage set to hit an exact item count. Total may land in
    [need, need + _GROUP_TOTAL_TOLERANCE].
    Part 6 drops incomplete published sets (passage has more blanks than items).
    """
    pool = _dedupe_by_id(pool)
    passages = passages or {}
    targets = band_quota_for_part(part)
    need = sum(targets.values())
    max_total = need + _GROUP_TOTAL_TOLERANCE

    by_passage: dict[Any, list[dict[str, Any]]] = defaultdict(list)
    orphans: list[dict[str, Any]] = []
    for item in pool:
        pid = item.get("passage_id")
        if pid is None:
            orphans.append(item)
        else:
            by_passage[pid].append(item)

    groups: list[tuple[Band, list[dict[str, Any]], int | None]] = []
    for pid, items in by_passage.items():
        ordered = _sort_group_items(list(items))
        if part == "r6":
            body = (passages.get(int(pid)) or {}).get("body")
            if not _r6_group_is_complete(ordered, body):
                continue
        groups.append((_majority_band(ordered), ordered, int(pid)))
    # Orphan r6 items cannot form a complete multi-blank set.
    if part != "r6":
        for item in orphans:
            groups.append((band_for_item(item), [item], None))

    rng.shuffle(groups)
    by_band: dict[Band, list[tuple[Band, list[dict[str, Any]], int | None]]] = (
        defaultdict(list)
    )
    for g in groups:
        by_band[g[0]].append(g)
    for band in BANDS:
        rng.shuffle(by_band[band])

    selected_groups: list[tuple[Band, list[dict[str, Any]], int | None]] = []
    credited: dict[Band, int] = {b: 0 for b in BANDS}
    used: set[int] = set()

    def _total() -> int:
        return sum(len(g[1]) for g in selected_groups)

    def _add(group: tuple[Band, list[dict[str, Any]], int | None]) -> bool:
        band, items, _pid = group
        gid = id(group)
        if gid in used:
            return False
        if _total() + len(items) > max_total:
            return False
        used.add(gid)
        selected_groups.append(group)
        credited[band] += len(items)
        return True

    def _drop_at(index: int) -> None:
        group = selected_groups.pop(index)
        band, items, _pid = group
        used.discard(id(group))
        credited[band] = max(0, credited[band] - len(items))

    # Fill each band toward its target without large overshoot.
    for band in BANDS:
        target = int(targets.get(band, 0))
        if target <= 0:
            continue
        for group in by_band[band]:
            if credited[band] >= target:
                break
            _, items, _ = group
            room = target + _STRATA_TOLERANCE - credited[band]
            if len(items) > room and credited[band] > 0:
                continue
            _add(group)

    # Top up total while respecting per-band +tolerance when possible.
    leftovers = [g for g in groups if id(g) not in used]
    rng.shuffle(leftovers)
    progressed = True
    while _total() < need and progressed:
        progressed = False
        leftovers = [g for g in leftovers if id(g) not in used]
        leftovers.sort(
            key=lambda g: (
                0
                if credited[g[0]] < int(targets.get(g[0], 0)) + _STRATA_TOLERANCE
                else 1,
                len(g[1]),
            )
        )
        for group in leftovers:
            if _total() >= need:
                break
            band, items, _ = group
            if credited[band] + len(items) > int(targets.get(band, 0)) + _STRATA_TOLERANCE:
                continue
            if _add(group):
                progressed = True
                break

    # Last resort: any leftover whole group that keeps total within max_total.
    leftovers = [g for g in groups if id(g) not in used]
    rng.shuffle(leftovers)
    for group in leftovers:
        if _total() >= need:
            break
        _add(group)

    # Trim excess by dropping whole groups only (never mid-passage).
    trimmed = True
    while trimmed and _total() > need:
        trimmed = False
        for i in range(len(selected_groups) - 1, -1, -1):
            if _total() - len(selected_groups[i][1]) >= need:
                _drop_at(i)
                trimmed = True
                break

    selected = [item for _b, items, _p in selected_groups for item in items]
    pids = {
        int(pid)
        for _b, _items, pid in selected_groups
        if pid is not None
    }

    if len(selected) < need:
        raise BankTooSmallError(
            f"Need {need} published {part} items after banded group pick, "
            f"have {len(selected)}"
        )
    if len(selected) > max_total:
        raise BankTooSmallError(
            f"Need ~{need} published {part} items (±{_GROUP_TOTAL_TOLERANCE} "
            f"whole groups), have {len(selected)}"
        )

    final_counts = _band_counts(selected)
    # Whole groups can force a slightly wider band miss than flat ±1.
    band_tol = max(_STRATA_TOLERANCE, _GROUP_TOTAL_TOLERANCE)
    for band in BANDS:
        target = int(targets.get(band, 0))
        have = final_counts[band]
        if abs(have - target) > band_tol:
            raise BankTooSmallError(
                f"Need ~{target} (±{band_tol}) published {part}/{band}, "
                f"have {have}"
            )

    return _dedupe_by_id(selected), pids


def _public_item(item: dict[str, Any], *, include_answer: bool) -> dict[str, Any]:
    out = {
        "id": item["id"],
        "toeic_part": item.get("toeic_part"),
        "stem": item.get("stem"),
        "options": item.get("options"),
        "skill_id": item.get("skill_id"),
        "cefr_level": item.get("cefr_level"),
        "passage_id": item.get("passage_id"),
        "prompt_words": item.get("prompt_words"),
        "media_url": item.get("media_url"),
        "task_brief": item.get("task_brief"),
        "question_type": item.get("question_type"),
    }
    if include_answer:
        out["answer"] = item.get("answer")
    return out
