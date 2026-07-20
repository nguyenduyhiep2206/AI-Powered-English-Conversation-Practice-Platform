"""Rule-based difficulty_in_level (1–10) helpers."""

from __future__ import annotations


def difficulty_from_unit_index(unit_index: int, n_units: int) -> int:
    """Map unit position in a book to difficulty 1 (start) … 10 (end)."""
    if n_units <= 1:
        return 1
    idx = max(0, min(int(unit_index), n_units - 1))
    raw = 1 + round(9 * idx / (n_units - 1))
    return max(1, min(10, int(raw)))


def median_difficulty(values: list[int]) -> int:
    """Median of clamped 1..10 values; even length uses lower middle (index (n-1)//2)."""
    if not values:
        return 5
    xs = sorted(max(1, min(10, int(v))) for v in values)
    return xs[(len(xs) - 1) // 2]
