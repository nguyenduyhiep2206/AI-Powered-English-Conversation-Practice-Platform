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


def _require_unit_mappings(payload: dict[str, Any]) -> list[Any]:
    if not isinstance(payload, dict):
        raise ValueError("LLM skill graph payload must be an object")
    raw_mappings = payload.get("unit_mappings")
    if not isinstance(raw_mappings, list) or not raw_mappings:
        raise ValueError("unit_mappings must be a non-empty list")
    return raw_mappings


def _normalize_mapping_item(item: Any, *, allowed: set[str]) -> dict[str, Any] | None:
    """Normalize one mapping entry, or None if it should be soft-dropped."""
    if not isinstance(item, dict):
        return None
    try:
        unit_index = int(item["unit_index"])
    except (KeyError, TypeError, ValueError):
        return None

    slug = str(item.get("slug") or "").strip().lower()
    if not _SLUG_RE.match(slug):
        return None

    skill_type = str(item.get("skill_type") or "").strip().lower()
    if skill_type not in allowed:
        return None

    try:
        difficulty = int(item.get("difficulty_in_level", 5))
    except (TypeError, ValueError):
        difficulty = 5

    return {
        "unit_index": unit_index,
        "slug": slug,
        "title": str(item.get("title") or slug).strip() or slug,
        "skill_type": skill_type,
        "difficulty_in_level": max(1, min(10, difficulty)),
        "exclude": bool(item.get("exclude", False)),
    }


def _normalize_mappings(
    raw_mappings: list[Any], *, allowed: set[str]
) -> tuple[list[dict[str, Any]], set[int], set[str]]:
    """Return (mappings, seen_indexes, mapping_slugs); first entry per index wins."""
    mappings: list[dict[str, Any]] = []
    seen_indexes: set[int] = set()
    mapping_slugs: set[str] = set()
    for item in raw_mappings:
        normalized = _normalize_mapping_item(item, allowed=allowed)
        if normalized is None or normalized["unit_index"] in seen_indexes:
            continue
        mappings.append(normalized)
        seen_indexes.add(normalized["unit_index"])
        mapping_slugs.add(normalized["slug"])
    return mappings, seen_indexes, mapping_slugs


def _require_full_coverage(seen_indexes: set[int], expected: set[int]) -> None:
    if seen_indexes != expected:
        missing = sorted(expected - seen_indexes)
        extra = sorted(seen_indexes - expected)
        raise ValueError(
            f"unit_mappings must cover each unit_index exactly once "
            f"(missing={missing}, extra={extra})"
        )


def _normalize_prereq_edges(
    raw_prereqs: Any, *, known_slugs: set[str]
) -> list[tuple[str, str]]:
    """Keep unique from→to edges within known slugs; drop self-edges and cycles."""
    edges: list[tuple[str, str]] = []
    if not isinstance(raw_prereqs, list):
        return edges
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
    return edges


def _normalize_attach_item(item: Any, *, catalog_slugs: set[str]) -> dict[str, Any] | None:
    """Normalize one attach mapping, or None if soft-dropped."""
    if not isinstance(item, dict):
        return None
    try:
        unit_index = int(item["unit_index"])
    except (KeyError, TypeError, ValueError):
        return None

    exclude = bool(item.get("exclude", False))
    raw_slug = item.get("slug")
    if raw_slug is None or (isinstance(raw_slug, str) and not raw_slug.strip()):
        return {"unit_index": unit_index, "slug": None, "exclude": exclude}

    slug = str(raw_slug).strip().lower()
    if slug not in catalog_slugs:
        raise ValueError(f"slug {slug!r} is not in the catalog for this level")
    return {"unit_index": unit_index, "slug": slug, "exclude": exclude}


def validate_llm_attach_payload(
    payload: dict[str, Any],
    *,
    unit_indexes: set[int],
    catalog_slugs: set[str],
) -> list[dict[str, Any]]:
    """Return attach mappings; slug must be catalog member or null.

    Raises if a non-null slug is outside the catalog, or unit coverage is incomplete.
    """
    raw_mappings = _require_unit_mappings(payload)
    expected = {int(i) for i in unit_indexes}
    catalog = {str(s).strip().lower() for s in catalog_slugs}

    mappings: list[dict[str, Any]] = []
    seen_indexes: set[int] = set()
    for item in raw_mappings:
        normalized = _normalize_attach_item(item, catalog_slugs=catalog)
        if normalized is None or normalized["unit_index"] in seen_indexes:
            continue
        mappings.append(normalized)
        seen_indexes.add(normalized["unit_index"])

    _require_full_coverage(seen_indexes, expected)
    return mappings


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
    raw_mappings = _require_unit_mappings(payload)
    allowed = {str(t).strip().lower() for t in allowed_skill_types}
    expected = {int(i) for i in unit_indexes}

    mappings, seen_indexes, mapping_slugs = _normalize_mappings(raw_mappings, allowed=allowed)
    _require_full_coverage(seen_indexes, expected)

    known_slugs = mapping_slugs | {str(s).strip().lower() for s in existing_slugs}
    edges = _normalize_prereq_edges(payload.get("prerequisites"), known_slugs=known_slugs)
    return mappings, edges
