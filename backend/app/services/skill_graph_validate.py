"""Validate and normalize LLM skill-graph sync payloads."""

from __future__ import annotations

import re
from typing import Any

_SLUG_RE = re.compile(r"^[a-z0-9_]{2,120}$")


def _would_create_cycle(edges: list[tuple[str, str]], frm: str, to: str) -> bool:
    """True if adding frm→to creates a directed cycle (to can reach frm)."""
    adj: dict[str, list[str]] = {}
    for a, b in edges:
        adj.setdefault(a, []).append(b)
    adj.setdefault(frm, []).append(to)

    stack = [to]
    seen: set[str] = set()
    while stack:
        node = stack.pop()
        if node == frm:
            return True
        if node in seen:
            continue
        seen.add(node)
        stack.extend(adj.get(node, []))
    return False


def validate_llm_graph_payload(
    payload: dict[str, Any],
    *,
    unit_indexes: set[int],
    existing_slugs: set[str],
    allowed_skill_types: set[str],
) -> tuple[list[dict[str, Any]], list[tuple[str, str]]]:
    """Return normalized (unit_mappings, prereq pairs); raise if coverage unusable.

    Soft-drops self-edges, unknown-slug edges, and edges that would form a cycle.
    """
    if not isinstance(payload, dict):
        raise ValueError("LLM skill graph payload must be an object")

    raw_mappings = payload.get("unit_mappings")
    if not isinstance(raw_mappings, list) or not raw_mappings:
        raise ValueError("unit_mappings must be a non-empty list")

    existing_norm = {str(s).strip().lower() for s in existing_slugs}
    allowed = {str(t).strip().lower() for t in allowed_skill_types}
    expected = {int(i) for i in unit_indexes}

    mappings: list[dict[str, Any]] = []
    seen_indexes: set[int] = set()
    mapping_slugs: set[str] = set()

    for item in raw_mappings:
        if not isinstance(item, dict):
            continue
        try:
            unit_index = int(item["unit_index"])
        except (KeyError, TypeError, ValueError):
            continue
        if unit_index in seen_indexes:
            continue

        slug = str(item.get("slug") or "").strip().lower()
        if not _SLUG_RE.match(slug):
            continue

        skill_type = str(item.get("skill_type") or "").strip().lower()
        if skill_type not in allowed:
            continue

        try:
            difficulty = int(item.get("difficulty_in_level", 5))
        except (TypeError, ValueError):
            difficulty = 5
        difficulty = max(1, min(10, difficulty))

        title = str(item.get("title") or slug).strip() or slug
        exclude = bool(item.get("exclude", False))

        mappings.append(
            {
                "unit_index": unit_index,
                "slug": slug,
                "title": title,
                "skill_type": skill_type,
                "difficulty_in_level": difficulty,
                "exclude": exclude,
            }
        )
        seen_indexes.add(unit_index)
        mapping_slugs.add(slug)

    if seen_indexes != expected:
        missing = sorted(expected - seen_indexes)
        extra = sorted(seen_indexes - expected)
        raise ValueError(
            f"unit_mappings must cover each unit_index exactly once "
            f"(missing={missing}, extra={extra})"
        )

    known_slugs = mapping_slugs | existing_norm
    edges: list[tuple[str, str]] = []
    raw_prereqs = payload.get("prerequisites") or []
    if not isinstance(raw_prereqs, list):
        raw_prereqs = []

    for edge in raw_prereqs:
        if not isinstance(edge, dict):
            continue
        frm = str(edge.get("from_slug") or "").strip().lower()
        to = str(edge.get("to_slug") or "").strip().lower()
        if not frm or not to or frm == to:
            continue
        if frm not in known_slugs or to not in known_slugs:
            continue
        if (frm, to) in edges:
            continue
        if _would_create_cycle(edges, frm, to):
            continue
        edges.append((frm, to))

    return mappings, edges
