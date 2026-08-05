"""Blueprint for skill-aligned Practice quiz drills (non-TOEIC)."""

from __future__ import annotations

from typing import Any

# (item_kind, question_type)
_GRAMMAR_TEMPLATE: list[tuple[str, str]] = [
    ("form_choose", "mcq"),
    ("form_choose", "mcq"),
    ("cloze_form", "cloze"),
    ("fix_grammar", "fix_grammar"),
    ("contrast", "mcq"),
    ("paraphrase", "mcq"),
    ("form_choose", "mcq"),
    ("cloze_form", "cloze"),
    ("fix_grammar", "fix_grammar"),
    ("contrast", "mcq"),
]

_VOCAB_TEMPLATE: list[tuple[str, str]] = [
    ("form_choose", "mcq"),
    ("form_choose", "mcq"),
    ("cloze_form", "cloze"),
    ("cloze_form", "cloze"),
    ("paraphrase", "mcq"),
    ("reading_target", "mcq"),
]

_DEFAULT_TEMPLATE: list[tuple[str, str]] = [
    ("form_choose", "mcq"),
    ("cloze_form", "cloze"),
    ("fix_grammar", "fix_grammar"),
    ("contrast", "mcq"),
    ("paraphrase", "mcq"),
    ("reading_target", "mcq"),
]


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
        # Cap reading_target at 2 per batch
        if kind == "reading_target":
            already = sum(1 for b in out if b["item_kind"] == "reading_target")
            if already >= 2:
                i += 1
                continue
        out.append({"item_kind": kind, "question_type": qtype})
        i += 1
        if i > n * 4:
            break
    return out[:n]
