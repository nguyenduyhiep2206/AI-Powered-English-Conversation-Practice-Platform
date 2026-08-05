from __future__ import annotations

import re
from dataclasses import dataclass

from app.services.unit_enrichment_excerpt import FOCUS_HEADING_RE

_LANGUAGE_FOCUS_MAX_CHARS = 200

_STOPWORDS = frozenset(
    {
        "a",
        "an",
        "and",
        "are",
        "as",
        "at",
        "be",
        "for",
        "from",
        "in",
        "is",
        "it",
        "of",
        "on",
        "or",
        "the",
        "to",
        "unit",
        "with",
    }
)

# Tokens too common to count alone toward a catalog cue.
_WEAK_MATCH_TOKENS = frozenset(
    {
        "because",
        "but",
        "conditional",
        "first",
        "have",
        "lot",
        "many",
        "much",
        "present",
        "second",
        "simple",
        "so",
        "will",
    }
)

_WORD_RE = re.compile(r"[a-z]+")

_DIRTY_FOCUS_RE = re.compile(
    r"(?i)("
    r"\bcorrect the\b"
    r"|\bspelling\b"
    r"|\bmarked words\b"
    r"|\bexercise\b"
    r"|\d+\s+\S+"  # "1 What's…"
    r")"
)


@dataclass(frozen=True)
class HeuristicResult:
    language_focus: str | None
    grammar_cues: list[str]
    vocab_cues: list[str]
    strong: bool


def _word_tokens(text: str) -> set[str]:
    return set(_WORD_RE.findall(text.lower()))


def _slug_tokens(slug: str) -> list[str]:
    return [t for t in slug.split("_") if len(t) >= 3]


def _title_tokens(title: str) -> list[str]:
    cleaned = re.sub(r"\([^)]*\)", "", title)
    return [
        t
        for t in _WORD_RE.findall(cleaned.lower())
        if len(t) >= 3 and t not in _STOPWORDS
    ]


def _skill_match_tokens(skill: dict) -> list[str]:
    slug = skill.get("slug") or ""
    title = skill.get("title") or ""
    seen: set[str] = set()
    tokens: list[str] = []
    for token in _slug_tokens(slug) + _title_tokens(title):
        if token not in seen:
            seen.add(token)
            tokens.append(token)
    return tokens


def _title_phrase(title: str) -> str | None:
    """Distinctive multi-word phrase from a skill title, if any."""
    cleaned = re.sub(r"\([^)]*\)", "", title)
    # Keep first slash-segment (e.g. "Should / must" → "should")
    cleaned = cleaned.split("/")[0]
    words = [
        t
        for t in _WORD_RE.findall(cleaned.lower())
        if t not in _STOPWORDS and len(t) >= 3
    ]
    if len(words) >= 2:
        return " ".join(words[:3])
    return None


def _skill_matches_text(skill: dict, text: str) -> bool:
    """Require phrase hit, or ≥2 non-weak tokens, or one distinctive token."""
    if not text:
        return False
    lower = text.lower()
    title = str(skill.get("title") or "")
    phrase = _title_phrase(title)
    if phrase and phrase in lower:
        return True

    tokens = _skill_match_tokens(skill)
    if not tokens:
        return False

    words = _word_tokens(text)
    hits = [t for t in tokens if t in words]
    strong_hits = [t for t in hits if t not in _WEAK_MATCH_TOKENS]

    if len(hits) >= 2:
        return True
    if len(strong_hits) == 1 and len(strong_hits[0]) >= 6:
        return True
    return False


def language_focus_looks_like_body(language_focus: str | None) -> bool:
    """True when extracted focus looks like exercise/body text, not a focus line."""
    if not language_focus:
        return False
    focus = language_focus.strip()
    if len(focus) > 120:
        return True
    if _DIRTY_FOCUS_RE.search(focus):
        return True
    if focus.count("?") >= 1 and len(focus.split()) > 12:
        return True
    return False


def _extract_language_focus(excerpt: str) -> str | None:
    match = FOCUS_HEADING_RE.search(excerpt)
    if not match:
        return None

    rest = excerpt[match.end() :].lstrip("\n")
    lines: list[str] = []
    for line in rest.splitlines():
        stripped = line.strip()
        if not stripped:
            break
        if FOCUS_HEADING_RE.match(line):
            break
        lines.append(stripped)

    focus = " ".join(lines).strip()
    if not focus:
        return None
    if len(focus) > _LANGUAGE_FOCUS_MAX_CHARS:
        focus = focus[:_LANGUAGE_FOCUS_MAX_CHARS].rstrip()
    return focus


def _extract_vocab_cues(unit_title: str) -> list[str]:
    cues: list[str] = []
    seen: set[str] = set()
    for token in _word_tokens(unit_title):
        if token in _STOPWORDS or token.isdigit() or len(token) < 3:
            continue
        if token not in seen:
            seen.add(token)
            cues.append(token)
    return cues


def _extract_grammar_cues(excerpt: str, catalog_skills: list[dict]) -> list[str]:
    cues: list[str] = []
    seen: set[str] = set()
    for skill in catalog_skills:
        slug = skill.get("slug") or ""
        if not slug or slug in seen:
            continue
        if _skill_matches_text(skill, excerpt):
            seen.add(slug)
            cues.append(slug)
    return cues


def _focus_matches_catalog(language_focus: str, catalog_skills: list[dict]) -> bool:
    for skill in catalog_skills:
        if _skill_matches_text(skill, language_focus):
            return True
    return False


def run_heuristic(
    excerpt: str,
    *,
    unit_title: str,
    catalog_skills: list[dict],
) -> HeuristicResult:
    catalog_slugs = {s.get("slug") for s in catalog_skills if s.get("slug")}
    language_focus = _extract_language_focus(excerpt)
    if language_focus_looks_like_body(language_focus):
        language_focus = None

    grammar_cues = _extract_grammar_cues(excerpt, catalog_skills)
    vocab_cues = _extract_vocab_cues(unit_title)
    strong = bool(set(grammar_cues) & catalog_slugs) or bool(
        language_focus and _focus_matches_catalog(language_focus, catalog_skills)
    )
    return HeuristicResult(
        language_focus=language_focus,
        grammar_cues=grammar_cues,
        vocab_cues=vocab_cues,
        strong=strong,
    )
