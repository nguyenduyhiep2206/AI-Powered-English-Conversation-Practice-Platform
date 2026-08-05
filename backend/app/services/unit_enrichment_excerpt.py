from __future__ import annotations

import re

FOCUS_HEADING_RE = re.compile(
    # Heading-only lines — not mid-sentence "grammar and learn…"
    r"(?im)^(?:\s*)(?:"
    r"language\s+focus"
    r"|unit\s+goals"
    r"|grammar(?:\s+focus|\s+box)?"
    r"|vocabulary(?:\s+focus|\s+box)?"
    r")(?:\s*[:.\-–]?\s*\d*)?\s*$"
)


def join_chunk_texts(chunks: list[dict]) -> str:
    ordered = sorted(chunks, key=lambda c: int(c.get("chunk_index") or 0))
    parts = [(c.get("text") or "").strip() for c in ordered]
    return "\n\n".join(p for p in parts if p)


def window_prefer_language_focus(raw: str) -> str:
    if not raw:
        return ""
    m = FOCUS_HEADING_RE.search(raw)
    if not m:
        return raw
    return raw[m.start() :].lstrip()


def truncate_excerpt(text: str, max_chars: int) -> str:
    if max_chars < 1:
        return ""
    if len(text) <= max_chars:
        return text
    return text[:max_chars]
