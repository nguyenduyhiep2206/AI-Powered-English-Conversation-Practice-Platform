"""Map TOEIC-style reading/writing scores to CEFR + placement sublevel."""

from __future__ import annotations

from app.services.placement.quotas import WRITING_RAW_MAX

# (cefr, min_reading_scale, min_writing_scale) high → low for lookup
_CEFR_THRESHOLDS: list[tuple[str, int, int]] = [
    ("C1", 400, 160),
    ("B2", 300, 120),
    ("B1", 200, 90),
    ("A2", 110, 50),
]


def reading_scale(correct: int, total: int = 100) -> int:
    if total <= 0:
        return 5
    ratio = max(0.0, min(1.0, correct / total))
    return int(round(5 + ratio * 490))


def writing_scale(raw: float, raw_max: float = WRITING_RAW_MAX) -> int:
    if raw_max <= 0:
        return 0
    ratio = max(0.0, min(1.0, float(raw) / raw_max))
    return int(round(ratio * 200))


def _cefr_from_pair(reading: int, writing: int) -> str:
    for cefr, r_min, w_min in _CEFR_THRESHOLDS:
        if reading >= r_min and writing >= w_min:
            return cefr
    return "A1"


def blend_to_cefr(reading_scale_val: int, writing_scale_val: int) -> str:
    """Min-of-two: CEFR is the weaker of reading-derived and writing-derived bands."""
    r_level = _cefr_from_pair(reading_scale_val, 200)  # writing maxed → reading alone
    w_level = _cefr_from_pair(495, writing_scale_val)  # reading maxed → writing alone
    order = ["A1", "A2", "B1", "B2", "C1"]
    return order[min(order.index(r_level), order.index(w_level))]


def placement_sublevel(
    reading_scale_val: int, writing_scale_val: int, cefr: str
) -> int:
    """Map residual strength inside the CEFR band to sublevel 1–10."""
    bands = {
        "A1": (5, 109, 0, 49),
        "A2": (110, 199, 50, 89),
        "B1": (200, 299, 90, 119),
        "B2": (300, 399, 120, 159),
        "C1": (400, 495, 160, 200),
    }
    r_lo, r_hi, w_lo, w_hi = bands.get(cefr, bands["A1"])
    r_span = max(1, r_hi - r_lo)
    w_span = max(1, w_hi - w_lo)
    r_pct = (max(r_lo, min(r_hi, reading_scale_val)) - r_lo) / r_span
    w_pct = (max(w_lo, min(w_hi, writing_scale_val)) - w_lo) / w_span
    blended = (r_pct + w_pct) / 2.0
    return max(1, min(10, int(blended * 9) + 1))
