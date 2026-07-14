"""Normalize book unit titles into canonical skill slugs (rule + alias MVP)."""

from __future__ import annotations

import re

# Common grammar/vocab title aliases → slug
SLUG_ALIASES: dict[str, str] = {
    "present perfect": "present_perfect",
    "present perfect continuous": "present_perfect_continuous",
    "present perfect simple": "present_perfect",
    "past simple": "past_simple",
    "past continuous": "past_continuous",
    "present simple": "present_simple",
    "present continuous": "present_continuous",
    "conditionals": "conditionals",
    "first conditional": "conditionals_type1",
    "second conditional": "conditionals_type2",
    "third conditional": "conditionals_type3",
    "passive": "passive_voice",
    "passive voice": "passive_voice",
    "modals": "modals",
    "articles": "articles",
}


_PAREN_RE = re.compile(r"\([^)]*\)")
_UNIT_PREFIX_RE = re.compile(
    r"^(unit|chapter|section|part|bài|chương|phần)\s*\d+\s*[:.\-]?\s*",
    re.I,
)
_TRAILING_NUM_RE = re.compile(r"\s+\d+\s*$")
_NON_ALNUM_RE = re.compile(r"[^a-z0-9]+")
_MULTI_UNDERSCORE_RE = re.compile(r"_+")


def clean_unit_title(title: str) -> str:
    text = (title or "").strip()
    text = _PAREN_RE.sub(" ", text)
    text = _UNIT_PREFIX_RE.sub("", text)
    text = _TRAILING_NUM_RE.sub("", text)
    text = re.sub(r"\s+", " ", text).strip(" -–—:")
    return text


def title_to_slug(cleaned_title: str) -> str:
    key = cleaned_title.lower().strip()
    if key in SLUG_ALIASES:
        return SLUG_ALIASES[key]
    # Prefix match longer aliases first
    for alias, slug in sorted(SLUG_ALIASES.items(), key=lambda x: -len(x[0])):
        if key.startswith(alias):
            return slug
    slug = _NON_ALNUM_RE.sub("_", key).strip("_")
    slug = _MULTI_UNDERSCORE_RE.sub("_", slug)
    return slug or "untitled_skill"


def normalize_unit_to_slug(title: str) -> tuple[str, str]:
    """Return (slug, display_title) for a unit heading."""
    cleaned = clean_unit_title(title)
    display = cleaned or (title or "").strip() or "Untitled skill"
    return title_to_slug(cleaned or display), display
