"""Assemble a timed TOEIC R+W form snapshot from published quiz bank items."""

from __future__ import annotations

from collections import defaultdict
from random import Random
from typing import Any

from app.services.placement.quotas import READING_QUOTA, WRITING_QUOTA


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
    skill_id, cefr_level, passage_id (optional), prompt_words, media_url, task_brief.
    R6/R7 selection prefers whole passage groups until quota is met.
    """
    rng = rng or Random()
    reading_items: list[dict[str, Any]] = []
    writing_items: list[dict[str, Any]] = []
    used_passage_ids: set[int] = set()

    for part, need in READING_QUOTA.items():
        pool = list(items_by_part.get(part) or [])
        if part in {"r6", "r7"}:
            selected, pids = _pick_passage_groups(pool, need, rng=rng)
        else:
            selected, pids = _pick_flat(pool, need, rng=rng)
        if len(selected) < need:
            raise BankTooSmallError(
                f"Need {need} published {part} items, have {len(selected)}"
            )
        reading_items.extend(selected)
        used_passage_ids.update(pids)

    for part, need in WRITING_QUOTA.items():
        pool = list(items_by_part.get(part) or [])
        selected, pids = _pick_flat(pool, need, rng=rng)
        if len(selected) < need:
            raise BankTooSmallError(
                f"Need {need} published {part} items, have {len(selected)}"
            )
        writing_items.extend(selected)
        used_passage_ids.update(pids)

    snapshot_passages = {
        str(pid): passages[pid]
        for pid in used_passage_ids
        if pid in passages
    }
    return {
        "reading_items": [_public_item(i, include_answer=False) for i in reading_items],
        "writing_items": [_public_item(i, include_answer=False) for i in writing_items],
        "passages": snapshot_passages,
        # Private grading keys kept under _key for server-only use in session
        "_answers": {str(i["id"]): i.get("answer") for i in reading_items},
        "_reading_ids": [i["id"] for i in reading_items],
        "_writing_ids": [i["id"] for i in writing_items],
        "_items": {str(i["id"]): i for i in reading_items + writing_items},
    }


def _pick_flat(
    pool: list[dict[str, Any]], need: int, *, rng: Random
) -> tuple[list[dict[str, Any]], set[int]]:
    if len(pool) < need:
        return pool, {int(i["passage_id"]) for i in pool if i.get("passage_id") is not None}
    chosen = rng.sample(pool, need)
    pids = {int(i["passage_id"]) for i in chosen if i.get("passage_id") is not None}
    return chosen, pids


def _pick_passage_groups(
    pool: list[dict[str, Any]], need: int, *, rng: Random
) -> tuple[list[dict[str, Any]], set[int]]:
    by_passage: dict[Any, list[dict[str, Any]]] = defaultdict(list)
    orphans: list[dict[str, Any]] = []
    for item in pool:
        pid = item.get("passage_id")
        if pid is None:
            orphans.append(item)
        else:
            by_passage[pid].append(item)

    groups = list(by_passage.values())
    rng.shuffle(groups)
    rng.shuffle(orphans)

    selected: list[dict[str, Any]] = []
    pids: set[int] = set()
    for group in groups:
        if len(selected) >= need:
            break
        selected.extend(group)
        pid = group[0].get("passage_id")
        if pid is not None:
            pids.add(int(pid))
    for item in orphans:
        if len(selected) >= need:
            break
        selected.append(item)

    if len(selected) > need:
        # Prefer keeping full groups; trim from the end only if oversized
        selected = selected[:need]
    return selected, pids


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
