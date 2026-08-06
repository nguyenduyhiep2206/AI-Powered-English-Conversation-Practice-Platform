"""Blueprint for skill-aligned Practice quiz drills (non-TOEIC)."""

from __future__ import annotations

from typing import Any

# (item_kind, question_type)
_GRAMMAR_TEMPLATE: list[tuple[str, str]] = [
    ("form_choose", "mcq"),
    ("cloze_form", "cloze"),
    ("fix_grammar", "fix_grammar"),
    ("spot_error", "mcq"),
    ("sentence_build", "sentence_build"),
    ("contrast", "mcq"),
]

_VOCAB_TEMPLATE: list[tuple[str, str]] = [
    ("form_choose", "mcq"),
    ("form_choose", "mcq"),
    ("cloze_form", "cloze"),
    ("matching", "matching"),
    ("sentence_build", "sentence_build"),
    ("reading_target", "mcq"),
]

_DEFAULT_TEMPLATE: list[tuple[str, str]] = [
    ("dialogue_complete", "mcq"),
    ("form_choose", "mcq"),
    ("cloze_form", "cloze"),
    ("multi_select", "multi_select"),
    ("paraphrase", "mcq"),
    ("reading_target", "mcq"),
]

_KIND_CAPS: dict[str, int] = {
    "reading_target": 2,
    "matching": 1,
    "sentence_build": 2,
}


def _kind_at_cap(out: list[dict[str, Any]], kind: str) -> bool:
    cap = _KIND_CAPS.get(kind)
    if cap is None:
        return False
    already = sum(1 for b in out if b["item_kind"] == kind)
    return already >= cap


def blueprint_for_skill_drill(skill_type: str, count: int) -> list[dict[str, Any]]:
    n = max(1, int(count))
    st = (skill_type or "").strip().lower()
    if st == "grammar":
        template = _GRAMMAR_TEMPLATE
    elif st == "vocabulary":
        template = _VOCAB_TEMPLATE
    else:
        template = _DEFAULT_TEMPLATE

    out: list[dict[str, Any]] = []
    i = 0
    while len(out) < n:
        kind, qtype = template[i % len(template)]
        if _kind_at_cap(out, kind):
            i += 1
            continue
        out.append({"item_kind": kind, "question_type": qtype})
        i += 1
        if i > n * 4:
            break
    return out[:n]
