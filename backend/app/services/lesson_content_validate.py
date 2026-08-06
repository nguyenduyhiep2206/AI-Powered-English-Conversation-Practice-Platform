"""Validate mini-unit lesson content JSON."""

from __future__ import annotations

import re
import unicodedata
from typing import Any

from app.core.config import settings

MIN_CHECKS = 1
MAX_CHECKS = 2
MIN_FORM_ROWS = 2
MAX_FORM_ROWS = 8

# Past/future continuous (or will + V) answers need a time cue in the check prompt.
_ANSWER_NEEDS_TIME_CONTEXT = re.compile(
    r"\b(was|were)\s+[a-z']+ing\b"
    r"|\bwill\s+(be\s+)?[a-z']+(\s+[a-z']+ing)?\b",
    re.IGNORECASE,
)
_TIME_CONTEXT_IN_PROMPT = re.compile(
    r"\b("
    r"yesterday|tomorrow|tonight|ago|"
    r"last\s+\w+|next\s+\w+|"
    r"right\s+now|at\s+the\s+moment|"
    r"this\s+(morning|afternoon|evening|week|weekend)|"
    r"when\s+[a-z']+|while\s+[a-z']+|"
    r"at\s+\d{1,2}(:\d{2})?\s*(am|pm)?"
    r")\b",
    re.IGNORECASE,
)


def target_bounds() -> tuple[int, int]:
    """Inclusive (min, max) target counts from settings."""
    lo = max(1, int(settings.LEARN_LESSON_MIN_TARGETS))
    hi = max(lo, int(settings.LEARN_LESSON_MAX_TARGETS))
    return lo, hi


# Snapshots for import compatibility; validation uses target_bounds() (live settings).
MIN_TARGETS, MAX_TARGETS = target_bounds()


def fold_text(value: str) -> str:
    """Casefold + normalize quotes so LLM curly apostrophes match passage text."""
    text = unicodedata.normalize("NFKC", str(value or ""))
    return (
        text.replace("\u2019", "'")
        .replace("\u2018", "'")
        .replace("\u201c", '"')
        .replace("\u201d", '"')
        .casefold()
    )


def check_prompt_has_needed_time_context(prompt: str, answer: str) -> bool:
    """False when the answer implies past/future aspect but the prompt has no time cue."""
    if not _ANSWER_NEEDS_TIME_CONTEXT.search(answer or ""):
        return True
    return bool(_TIME_CONTEXT_IN_PROMPT.search(prompt or ""))


def _pick_gloss(item: dict[str, Any]) -> str:
    """Prefer EN gloss fields; accept legacy gloss_vi for old drafts."""
    for key in ("gloss", "gloss_en", "gloss_vi"):
        value = str(item.get(key) or "").strip()
        if value:
            return value
    return ""


def _normalize_form(raw: Any) -> dict[str, Any] | None:
    if not isinstance(raw, dict):
        return None
    title = str(raw.get("title") or "").strip()
    rows_raw = raw.get("rows")
    if not isinstance(rows_raw, list):
        return None
    rows: list[dict[str, str]] = []
    for item in rows_raw:
        if not isinstance(item, dict):
            continue
        pattern = str(item.get("pattern") or "").strip()
        if not pattern:
            continue
        rows.append(
            {
                "label": str(item.get("label") or "").strip(),
                "pattern": pattern,
                "example": str(item.get("example") or "").strip(),
            }
        )
    if not rows:
        return None
    if len(rows) > MAX_FORM_ROWS:
        rows = rows[:MAX_FORM_ROWS]
    return {"title": title or "Form", "rows": rows}


def _normalize_passage(raw: dict[str, Any]) -> tuple[str, str | None]:
    passage = raw.get("passage")
    if not isinstance(passage, dict):
        raise ValueError("passage must be an object")
    text = str(passage.get("text") or "").strip()
    if not text:
        raise ValueError("passage.text is required")
    return text, _pick_gloss(passage) or None


def _normalize_targets(raw: dict[str, Any], *, passage_text: str) -> list[dict[str, str]]:
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
    min_t, max_t = target_bounds()
    text_folded = fold_text(passage_text)
    # LLM often invents one orphan surface; keep targets that actually appear.
    matched: list[dict[str, str]] = []
    dropped: list[str] = []
    for t in targets:
        if fold_text(t["surface"]) in text_folded:
            matched.append(t)
        else:
            dropped.append(t["surface"])
    targets = matched
    if len(targets) > max_t:
        targets = targets[:max_t]
    if len(targets) < min_t:
        detail = f" (dropped not in passage: {dropped})" if dropped else ""
        raise ValueError(
            f"targets must have {min_t}-{max_t} items after passage match; "
            f"got {len(targets)}{detail}"
        )
    return targets


def _normalize_checks_list(raw: dict[str, Any]) -> list[dict[str, Any]]:
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
    return checks


def _normalize_writing(
    raw: dict[str, Any], *, targets: list[dict[str, str]]
) -> dict[str, Any]:
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
    surface_set = {fold_text(t["surface"]) for t in targets}
    must_use = [m for m in must_use if fold_text(m) in surface_set]
    if not must_use:
        must_use = [t["surface"] for t in targets[:3]]
    return {
        "prompt": prompt,
        "min_words": min_words_i,
        "must_use": must_use,
    }


def normalize_content(raw: Any) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise ValueError("content must be an object")

    text, gloss = _normalize_passage(raw)
    targets = _normalize_targets(raw, passage_text=text)
    checks = _normalize_checks_list(raw)
    writing = _normalize_writing(raw, targets=targets)
    form = _normalize_form(raw.get("form"))
    exit_check = _normalize_check(raw.get("exit_check"))
    hook = str(raw.get("hook") or "").strip() or None

    out: dict[str, Any] = {
        "passage": {"text": text, "gloss": gloss},
        "targets": targets,
        "checks": checks,
        "writing": writing,
    }
    if hook:
        out["hook"] = hook
    if form is not None:
        out["form"] = form
    if exit_check is not None:
        out["exit_check"] = exit_check
    return out


def assert_publishable(
    content: dict[str, Any],
    *,
    skill_type: str | None = None,
    require_grammar_form: bool = True,
) -> None:
    normalized = normalize_content(content)
    st = (skill_type or "").strip().lower()
    # Pack L1/L3 may omit form; L2 (or single-lesson publish) still requires it.
    if st == "grammar" and require_grammar_form:
        form = normalized.get("form")
        rows = form.get("rows") if isinstance(form, dict) else None
        if not isinstance(rows, list) or len(rows) < MIN_FORM_ROWS:
            raise ValueError(
                "grammar lessons require form with at least 2 rows"
            )


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
    if not check_prompt_has_needed_time_context(prompt, answer):
        return None
    return {
        "type": check_type,
        "prompt": prompt,
        "options": options,
        "answer": answer,
    }
