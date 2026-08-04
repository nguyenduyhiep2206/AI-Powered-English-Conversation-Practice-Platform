"""Windowed transcript memory helpers for AI Tutor."""

from __future__ import annotations

import math
from typing import Any


def estimate_tokens(text: str) -> int:
    return max(0, math.ceil(len(text or "") / 4))


def window_transcript(
    messages: list[dict[str, Any]],
    *,
    max_turns: int,
    keep_first_assistant: bool = True,
) -> list[dict[str, Any]]:
    """Keep opener (first assistant) + last N user/assistant pairs worth of messages."""
    if not messages:
        return []
    cleaned = [
        {"role": m.get("role"), "content": (m.get("content") or "").strip()}
        for m in messages
        if (m.get("content") or "").strip()
    ]
    if not cleaned:
        return []

    opener: list[dict[str, Any]] = []
    rest = cleaned
    if keep_first_assistant and cleaned[0].get("role") == "assistant":
        opener = [cleaned[0]]
        rest = cleaned[1:]

    # Approximate N turns as 2*N messages (user+assistant), keep at least max_turns messages.
    keep_n = max(1, int(max_turns)) * 2
    tail = rest[-keep_n:] if keep_n else rest
    return opener + tail
