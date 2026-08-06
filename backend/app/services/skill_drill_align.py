"""Pure helpers: skill-drill item alignment against lesson target surfaces."""

from __future__ import annotations

import re
from typing import Any

# Spec floor is len>=2; bare "a" is only matched on answer/options (see align_score).
_SHORT_SURFACE_OK = frozenset({"a", "i"})
_DETERMINERS = frozenset({"a", "an", "the"})
_BE = frozenset({"am", "is", "are"})
_TRAILING_PUNCT = re.compile(r"[.!?;,:]+$")


def _normalize_surface(raw: str) -> str:
    """Lowercase + strip trailing sentence punctuation (lesson examples often end with '.')."""
    return _TRAILING_PUNCT.sub("", str(raw or "").strip().lower()).strip()


def expand_surfaces(surfaces: set[str]) -> set[str]:
    """Add bare determiners from NP targets for prompts / answer-side align.

    Lesson packs often store targets like "a student". Drill cloze blanks the
    article ("____ student"), so the full phrase never appears contiguously.

    Also expands slash alternatives in form labels (e.g. "am/is/are" → each form)
    so a cloze answer like "am working" aligns to Present Continuous patterns.
    """
    out: set[str] = {str(s or "").strip() for s in surfaces if str(s or "").strip()}
    for s in list(out):
        words = s.lower().split()
        if words and words[0] in _DETERMINERS:
            out.add(words[0])
        cleaned = _normalize_surface(s)
        if cleaned and cleaned != s.strip().lower():
            out.add(cleaned)
        # "am/is/are", "don't/doesn't", etc. from pattern labels
        for group in re.findall(r"\b[a-z']+(?:/[a-z']+)+\b", cleaned or s.lower()):
            for part in group.split("/"):
                part = part.strip()
                if not part:
                    continue
                if len(part) >= 2 or part in _SHORT_SURFACE_OK:
                    out.add(part)
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


def _surface_words(tok: str) -> list[str]:
    return re.findall(r"[a-z0-9']+", tok.lower())


def align_score(item: dict[str, Any], surfaces: set[str]) -> bool:
    """True if any surface matches as a whole word/token.

    Multi-word NP targets (e.g. "a student") also align when their leading
    determiner appears in answer/options — needed for article cloze blanks.
    Bare "a" never matches on stem/passage alone (too common in English).

    Example-sentence surfaces from lessons (e.g. "He is playing now.") also align
    when a contiguous 2+ word window appears (e.g. answer "is playing"), or when
    a be + V-ing pair contributes its -ing form (e.g. surface "are wearing" ↔
    answer "is wearing").
    """
    text = _haystack(item)
    answer_text = _answer_haystack(item)
    for s in expand_surfaces(surfaces):
        tok = _normalize_surface(s)
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

        words = _surface_words(tok)
        if len(words) >= 2:
            # Contiguous windows (≥2 words) cover conjugations shared with examples.
            for i in range(len(words)):
                for j in range(i + 2, len(words) + 1):
                    phrase = " ".join(words[i:j])
                    if _token_in(text, phrase):
                        return True
            # be + V-ing → V-ing alone (am/is/are variation across persons).
            for i, w in enumerate(words[:-1]):
                nxt = words[i + 1]
                if w in _BE and nxt.endswith("ing") and len(nxt) >= 5:
                    if _token_in(text, nxt):
                        return True

        if len(words) >= 2 and words[0] in _DETERMINERS:
            if _token_in(answer_text, words[0]):
                return True
    return False


def batch_align_ratio(items: list[dict[str, Any]], surfaces: set[str]) -> float:
    if not items:
        return 0.0
    ok = sum(1 for it in items if align_score(it, surfaces))
    return ok / len(items)
