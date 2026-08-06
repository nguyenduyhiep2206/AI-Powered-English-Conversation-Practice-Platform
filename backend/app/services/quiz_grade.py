"""Grade quiz answers by question type with canonicalization helpers."""

from __future__ import annotations

import re

from app.services.mastery_service import grade_mcq

_WHITESPACE_RE = re.compile(r"\s+")
_TRAILING_END_PUNCT = re.compile(r"[.!?]+$")
# Soft joiners between clauses — learners often use , . ; interchangeably.
_CLAUSE_JOINER_PUNCT = re.compile(r"\s*[,;:.—–-]+\s*")


def normalize_space_lower(s: str) -> str:
    return _WHITESPACE_RE.sub(" ", s.strip()).lower()


def canonicalize_sentence_build(raw: str) -> str:
    return normalize_space_lower(raw)


def canonicalize_fix_grammar(raw: str) -> str:
    """Compare rewritten sentences with lenient punctuation.

    Focus on words (the grammar fix). Comma / semicolon / period between
    clauses should not fail an otherwise correct rewrite.
    """
    text = normalize_space_lower(raw)
    text = text.strip("\"'`")
    text = _TRAILING_END_PUNCT.sub("", text).strip()
    text = _CLAUSE_JOINER_PUNCT.sub(" ", text)
    return normalize_space_lower(text)


def canonicalize_multi_select(raw: str) -> set[str]:
    parts = re.split(r"[|;]", raw)
    return {part.strip().lower() for part in parts if part.strip()}


def _parse_matching_pairs(raw: str) -> list[tuple[str, str]]:
    pairs: list[tuple[str, str]] = []
    for segment in re.split(r"[;\n]", raw):
        segment = segment.strip()
        if not segment:
            continue
        if "=>" in segment:
            left, right = segment.split("=>", 1)
        elif "|" in segment:
            left, right = segment.split("|", 1)
        else:
            continue
        pairs.append((left.strip().lower(), right.strip().lower()))
    return pairs


def canonicalize_matching_answer(raw: str) -> str:
    pairs = sorted(_parse_matching_pairs(raw), key=lambda pair: pair[0])
    return ";".join(f"{left}=>{right}" for left, right in pairs)


def grade_answer(question_type: str, expected: str, given: str) -> bool:
    if question_type in ("mcq", "cloze"):
        return grade_mcq(expected, given)
    if question_type == "fix_grammar":
        return canonicalize_fix_grammar(expected) == canonicalize_fix_grammar(
            given
        )
    if question_type == "sentence_build":
        return canonicalize_sentence_build(expected) == canonicalize_sentence_build(given)
    if question_type == "matching":
        return canonicalize_matching_answer(expected) == canonicalize_matching_answer(given)
    if question_type == "multi_select":
        return canonicalize_multi_select(expected) == canonicalize_multi_select(given)
    return grade_mcq(expected, given)
