"""Fail-closed validation for detected / AI-merged book structure units."""

from __future__ import annotations

import re
from difflib import SequenceMatcher

from app.services.book_structure.base import DetectedUnit

MIN_UNITS = 2
MAX_UNITS = 80
GROUNDING_PREFIX_CHARS = 500
FUZZY_RATIO_MIN = 0.6

JUNK_TITLE_RE = re.compile(
    r"(accessibility|file formats? available|organization of content|"
    r"^images$|^links$|font size|known issues|potential barriers|"
    r"structure bookmarks|alt text|screen reader)",
    re.IGNORECASE,
)

_NON_ALNUM = re.compile(r"[^a-z0-9]+")


def _normalize(text: str) -> str:
    return _NON_ALNUM.sub(" ", text.lower()).strip()


def _title_grounded(title: str, page_text: str) -> bool:
    if not title.strip() or not page_text:
        return False
    haystack = _normalize(page_text[:GROUNDING_PREFIX_CHARS])
    needle = _normalize(title)
    if not needle or not haystack:
        return False
    if needle in haystack:
        return True
    # Allow title like "1. THE OLD MAN..." vs page "1\nTHE OLD MAN..."
    parts = [p for p in needle.split() if len(p) > 1]
    if len(parts) >= 2 and all(p in haystack for p in parts[1:]):
        return True
    return SequenceMatcher(None, needle, haystack).ratio() >= FUZZY_RATIO_MIN


def validate_structure(
    units: list[DetectedUnit],
    *,
    total_pages: int,
    page_texts: list[str],
) -> tuple[bool, list[str]]:
    """Return (ok, reasons). Empty reasons when ok."""
    reasons: list[str] = []

    if not (MIN_UNITS <= len(units) <= MAX_UNITS):
        reasons.append(f"unit count {len(units)} outside [{MIN_UNITS}, {MAX_UNITS}]")
        return False, reasons

    if total_pages < 1:
        reasons.append("total_pages must be >= 1")
        return False, reasons

    if len(page_texts) < total_pages:
        reasons.append("page_texts shorter than total_pages")
        return False, reasons

    sorted_units = sorted(units, key=lambda u: (u.page_start, u.page_end, u.title))
    prev_end = 0
    junk_hits = 0

    for unit in sorted_units:
        if unit.page_start < 1 or unit.page_end > total_pages or unit.page_start > unit.page_end:
            reasons.append(
                f"invalid pages for {unit.title!r}: {unit.page_start}-{unit.page_end}"
            )
            continue

        if unit.page_start <= prev_end:
            reasons.append(
                f"overlap or non-increasing start for {unit.title!r} "
                f"(start={unit.page_start}, prev_end={prev_end})"
            )
        prev_end = max(prev_end, unit.page_end)

        if JUNK_TITLE_RE.search(unit.title.strip()):
            junk_hits += 1

        page_text = page_texts[unit.page_start - 1] or ""
        if not _title_grounded(unit.title, page_text):
            reasons.append(f"title not grounded on page {unit.page_start}: {unit.title!r}")

    if junk_hits >= max(2, (len(sorted_units) + 1) // 2):
        reasons.append(f"too many junk titles ({junk_hits}/{len(sorted_units)})")

    return (len(reasons) == 0), reasons
