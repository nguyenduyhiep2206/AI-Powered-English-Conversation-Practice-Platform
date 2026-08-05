"""Pure helpers: skill-drill item alignment against lesson target surfaces."""

from __future__ import annotations

import re
from typing import Any

# Spec floor is len>=2; bare "a" is only matched on answer/options (see align_score).
_SHORT_SURFACE_OK = frozenset({"a", "i"})
_DETERMINERS = frozenset({"a", "an", "the"})


def expand_surfaces(surfaces: set[str]) -> set[str]:
    """Add bare determiners from NP targets for prompts / answer-side align.

    Lesson packs often store targets like "a student". Drill cloze blanks the
    article ("____ student"), so the full phrase never appears contiguously.
    """
    out: set[str] = {str(s or "").strip() for s in surfaces if str(s or "").strip()}
    for s in list(out):
        words = s.lower().split()
        if words and words[0] in _DETERMINERS:
            out.add(words[0])
    return out


def _haystack(item: dict[str, Any]) -> str:
    parts = [
        str(item.get("stem") or ""),
        str(item.get("passage") or ""),
        str(item.get("answer") or ""),
    ]
    opts = item.get("options") or []
    if isinstance(opts, list):
        parts.extend(str(o) for o in opts)
    return " ".join(parts).lower()


def _answer_haystack(item: dict[str, Any]) -> str:
    parts = [str(item.get("answer") or "")]
    opts = item.get("options") or []
    if isinstance(opts, list):
        parts.extend(str(o) for o in opts)
    return " ".join(parts).lower()


def _token_in(text: str, tok: str) -> bool:
    return bool(re.search(rf"(?<![a-z0-9]){re.escape(tok)}(?![a-z0-9])", text))


def align_score(item: dict[str, Any], surfaces: set[str]) -> bool:
    """True if any surface matches as a whole word/token.

    Multi-word NP targets (e.g. "a student") also align when their leading
    determiner appears in answer/options — needed for article cloze blanks.
    Bare "a" never matches on stem/passage alone (too common in English).
    """
    text = _haystack(item)
    answer_text = _answer_haystack(item)
    for s in expand_surfaces(surfaces):
        tok = str(s or "").strip().lower()
        if not tok:
            continue
        if tok == "a":
            if _token_in(answer_text, "a"):
                return True
            continue
        if len(tok) < 2 and tok not in _SHORT_SURFACE_OK:
            continue
        if _token_in(text, tok):
            return True
        words = tok.split()
        if len(words) >= 2 and words[0] in _DETERMINERS:
            if _token_in(answer_text, words[0]):
                return True
    return False


def batch_align_ratio(items: list[dict[str, Any]], surfaces: set[str]) -> float:
    if not items:
        return 0.0
    ok = sum(1 for it in items if align_score(it, surfaces))
    return ok / len(items)
