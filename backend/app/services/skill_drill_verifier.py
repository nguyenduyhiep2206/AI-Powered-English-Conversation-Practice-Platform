"""LLM quality gate for skill-drill items (after structural validation)."""

from __future__ import annotations

import logging
from typing import Any

from app.core.config import settings
from app.services.llm_client import chat_json

logger = logging.getLogger(__name__)

VERIFY_KINDS = frozenset({"spot_error", "fix_grammar"})

VERIFY_SYSTEM_PROMPT = """You are a strict ESL exam editor.
You verify practice quiz items AFTER format checks. Return JSON only:
{"results":[{"index":0,"pass":true|false,"reason":"short English"}]}

For item_kind=spot_error:
- stem must contain exactly ONE real English error
- answer must be the incorrect underlined option
- the other options must be correct in context
- reject if the sentence is fully grammatical (e.g. Present Simple habit + Present Continuous temporary with but/today/usually/now)
- reject if explanation says the sentence is correct, or Error and Correct are the same string

For item_kind=fix_grammar:
- stem must be ungrammatical
- answer must be a correct natural repair of the stem

Be conservative: if unsure whether an error is real, pass=false.
Every input index MUST appear exactly once in results.
"""


def kinds_needing_verify(item: dict[str, Any]) -> bool:
    kind = str(item.get("item_kind") or "").strip()
    return kind in VERIFY_KINDS


def _build_verify_user_prompt(
    items: list[dict[str, Any]],
    *,
    skill_title: str,
    cefr: str,
) -> str:
    lines = [
        f"Skill: {skill_title}",
        f"CEFR: {cefr}",
        f"Verify {len(items)} item(s). Return results for every index 0..{len(items) - 1}.",
        "",
    ]
    for index, item in enumerate(items):
        lines.append(f"--- item index={index} ---")
        lines.append(f"item_kind: {item.get('item_kind')}")
        lines.append(f"type: {item.get('type')}")
        lines.append(f"stem: {item.get('stem')}")
        lines.append(f"options: {item.get('options')}")
        lines.append(f"answer: {item.get('answer')}")
        lines.append(f"explanation: {item.get('explanation')}")
        lines.append("")
    return "\n".join(lines)


def _parse_pass_map(payload: Any, expected: int) -> dict[int, bool]:
    """Map index -> pass. Missing / malformed indexes default to False."""
    out = {i: False for i in range(expected)}
    if not isinstance(payload, dict):
        return out
    results = payload.get("results")
    if not isinstance(results, list):
        return out
    for row in results:
        if not isinstance(row, dict):
            continue
        try:
            index = int(row.get("index"))
        except (TypeError, ValueError):
            continue
        if index not in out:
            continue
        out[index] = bool(row.get("pass"))
    return out


def verify_skill_drill_items(
    items: list[dict[str, Any]],
    *,
    skill_title: str,
    cefr: str,
) -> list[dict[str, Any]]:
    """Return items that pass verification. Non-verify kinds always kept.

    When SKILL_DRILL_LLM_VERIFY is false, returns items unchanged.
    Verify-eligible kinds fail-closed if the model omits them or errors.
    """
    if not items:
        return []
    if not getattr(settings, "SKILL_DRILL_LLM_VERIFY", True):
        return list(items)

    keep_as_is, to_verify = _partition_verify_items(items)
    if not to_verify:
        return list(items)

    pass_map = _run_verify_pass_map(
        [item for _, item in to_verify],
        skill_title=skill_title,
        cefr=cefr,
    )
    verified = _apply_pass_map(to_verify, pass_map)
    return _merge_by_original_index(keep_as_is, verified)


def _partition_verify_items(
    items: list[dict[str, Any]],
) -> tuple[list[tuple[int, dict[str, Any]]], list[tuple[int, dict[str, Any]]]]:
    keep_as_is: list[tuple[int, dict[str, Any]]] = []
    to_verify: list[tuple[int, dict[str, Any]]] = []
    for index, item in enumerate(items):
        if kinds_needing_verify(item):
            to_verify.append((index, item))
        else:
            keep_as_is.append((index, item))
    return keep_as_is, to_verify


def _run_verify_pass_map(
    verify_payload: list[dict[str, Any]],
    *,
    skill_title: str,
    cefr: str,
) -> dict[int, bool]:
    user_prompt = _build_verify_user_prompt(
        verify_payload, skill_title=skill_title, cefr=cefr
    )
    pass_map = {i: False for i in range(len(verify_payload))}
    try:
        raw = chat_json(VERIFY_SYSTEM_PROMPT, user_prompt)
        pass_map = _parse_pass_map(raw, len(verify_payload))
        # One retry if every verify item failed (likely parse / empty results).
        if verify_payload and not any(pass_map.values()):
            raw = chat_json(
                VERIFY_SYSTEM_PROMPT,
                user_prompt
                + "\nRETRY: previous response had no pass:true. "
                "Return results for EVERY index with pass true|false.\n",
            )
            pass_map = _parse_pass_map(raw, len(verify_payload))
    except Exception:
        logger.exception("skill_drill verifier call failed; failing closed")
        pass_map = {i: False for i in range(len(verify_payload))}
    return pass_map


def _mark_verified(item: dict[str, Any]) -> dict[str, Any]:
    brief = item.get("task_brief")
    if isinstance(brief, dict):
        return {**item, "task_brief": {**brief, "verified": True}}
    return {
        **item,
        "task_brief": {
            "mode": "skill_drill",
            "item_kind": item.get("item_kind"),
            "verified": True,
        },
    }


def _apply_pass_map(
    to_verify: list[tuple[int, dict[str, Any]]],
    pass_map: dict[int, bool],
) -> list[tuple[int, dict[str, Any]]]:
    verified: list[tuple[int, dict[str, Any]]] = []
    for verify_index, (orig_index, item) in enumerate(to_verify):
        if not pass_map.get(verify_index, False):
            logger.info(
                "skill_drill verifier rejected index=%s kind=%s stem=%r",
                orig_index,
                item.get("item_kind"),
                (item.get("stem") or "")[:120],
            )
            continue
        verified.append((orig_index, _mark_verified(item)))
    return verified


def _merge_by_original_index(
    keep_as_is: list[tuple[int, dict[str, Any]]],
    verified: list[tuple[int, dict[str, Any]]],
) -> list[dict[str, Any]]:
    merged = keep_as_is + verified
    merged.sort(key=lambda row: row[0])
    return [item for _, item in merged]
