"""Normalize quiz passage bodies for learner display."""

from __future__ import annotations

import re

# LLM sometimes pastes paper-style choice lists under the document, e.g.
#   (1)\nwill have painted\npaints\nis painting\nwill paint
_EMBEDDED_MCQ_BLOCK_RE = re.compile(
    r"(?:\n|\A)\(\d+\)\s*\n(?:[^\n]+\n){3,4}",
    re.MULTILINE,
)
_EMBEDDED_LETTERED_BLOCK_RE = re.compile(
    r"(?:\n|\A)(?:\(\s*[A-D]\s*\)|[A-D][.)])\s*[^\n]+(?:\n(?:\(\s*[A-D]\s*\)|[A-D][.)])\s*[^\n]+){3,}",
    re.MULTILINE | re.IGNORECASE,
)
# Or appends stem prompts under the memo, e.g.
#   (1) Which answer choice best completes the blank?
_EMBEDDED_STEM_LINE_RE = re.compile(
    r"^\(\d+\)\s*(?:"
    r"Which\b|Choose\b|Select\b|What\b|Pick\b|"
    r".*\b(?:blank|answer choice|best completes|best answer)\b"
    r").*$",
    re.IGNORECASE | re.MULTILINE,
)


def strip_embedded_mcq_choice_blocks(body: str | None) -> str:
    """Remove choice/stem dumps that belong on quiz items, not passage prose."""
    if not body:
        return ""
    text = body.replace("\r\n", "\n")
    prev = None
    while prev != text:
        prev = text
        text = _EMBEDDED_MCQ_BLOCK_RE.sub("\n", text)
        text = _EMBEDDED_LETTERED_BLOCK_RE.sub("\n", text)
        text = _EMBEDDED_STEM_LINE_RE.sub("", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()
