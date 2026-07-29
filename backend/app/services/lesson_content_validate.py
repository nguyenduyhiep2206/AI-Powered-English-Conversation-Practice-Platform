"""Validate mini-unit lesson content JSON."""

from __future__ import annotations

from typing import Any


MIN_TARGETS = 4
MAX_TARGETS = 7
MIN_CHECKS = 1
MAX_CHECKS = 2


def _pick_gloss(item: dict[str, Any]) -> str:
    """Prefer EN gloss fields; accept legacy gloss_vi for old drafts."""
    for key in ("gloss", "gloss_en", "gloss_vi"):
        value = str(item.get(key) or "").strip()
        if value:
            return value
    return ""


def normalize_content(raw: Any) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise ValueError("content must be an object")

    passage = raw.get("passage")
    if not isinstance(passage, dict):
        raise ValueError("passage must be an object")
    text = str(passage.get("text") or "").strip()
    if not text:
        raise ValueError("passage.text is required")
    gloss = _pick_gloss(passage) or None

    targets_raw = raw.get("targets")
    if not isinstance(targets_raw, list):
        raise ValueError("targets must be a list")
    targets: list[dict[str, str]] = []
    for item in targets_raw:
        if not isinstance(item, dict):
            continue
        surface = str(item.get("surface") or "").strip()
        if not surface:
            continue
        targets.append(
            {
                "surface": surface,
                "gloss": _pick_gloss(item),
                "note": str(item.get("note") or "").strip(),
            }
        )
    if not (MIN_TARGETS <= len(targets) <= MAX_TARGETS):
        raise ValueError(f"targets must have {MIN_TARGETS}-{MAX_TARGETS} items")

    checks_raw = raw.get("checks")
    if not isinstance(checks_raw, list):
        raise ValueError("checks must be a list")
    checks: list[dict[str, Any]] = []
    for item in checks_raw:
        normalized = _normalize_check(item)
        if normalized is not None:
            checks.append(normalized)
    if not (MIN_CHECKS <= len(checks) <= MAX_CHECKS):
        raise ValueError(f"checks must have {MIN_CHECKS}-{MAX_CHECKS} items")

    writing_raw = raw.get("writing")
    if not isinstance(writing_raw, dict):
        raise ValueError("writing must be an object")
    prompt = str(writing_raw.get("prompt") or "").strip()
    if not prompt:
        raise ValueError("writing.prompt is required")
    min_words = writing_raw.get("min_words", 15)
    try:
        min_words_i = max(1, int(min_words))
    except (TypeError, ValueError):
        min_words_i = 15
    must_use_raw = writing_raw.get("must_use")
    must_use: list[str] = []
    if isinstance(must_use_raw, list):
        must_use = [str(x).strip() for x in must_use_raw if str(x).strip()]
    if not must_use:
        must_use = [t["surface"] for t in targets[:3]]

    return {
        "passage": {"text": text, "gloss": gloss},
        "targets": targets,
        "checks": checks,
        "writing": {
            "prompt": prompt,
            "min_words": min_words_i,
            "must_use": must_use,
        },
    }


def assert_publishable(content: dict[str, Any]) -> None:
    normalize_content(content)


def _normalize_check(item: Any) -> dict[str, Any] | None:
    if not isinstance(item, dict):
        return None
    check_type = str(item.get("type") or "mcq").strip().lower()
    if check_type not in {"mcq", "cloze"}:
        return None
    prompt = str(item.get("prompt") or "").strip()
    answer = str(item.get("answer") or "").strip()
    if not prompt or not answer:
        return None
    options_raw = item.get("options")
    options: list[str] = []
    if isinstance(options_raw, list):
        options = [str(o).strip() for o in options_raw if str(o).strip()]
    if check_type == "mcq":
        if len(options) < 2:
            return None
        if answer not in options:
            return None
    return {
        "type": check_type,
        "prompt": prompt,
        "options": options,
        "answer": answer,
    }
