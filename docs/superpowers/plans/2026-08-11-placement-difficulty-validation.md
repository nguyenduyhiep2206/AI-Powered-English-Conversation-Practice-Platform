# Placement CEFR Proxy + Part-Curve Blueprint Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans`. Steps use checkbox (`- [ ]`) syntax.

**Goal:** Assemble full TOEIC R+W placement forms with a fixed per-part easy/mid/hard blueprint; label items from CEFR only (A1/A2=easy, B1=mid, B2/C1=hard). No empirical calibration or external-exam validation in this phase.

**Architecture:** Pure helper `band_for_item` + `PART_BAND_QUOTA` lookup; stratified sample inside existing `assemble_form`. Keep quotas/timers/scoring unchanged.

**Tech Stack:** FastAPI, pytest, existing placement services.

**Spec:** `docs/superpowers/specs/2026-08-11-placement-difficulty-validation-design.md`  
**Base:** `docs/superpowers/specs/2026-07-28-toeic-rw-placement-design.md`

## Global Constraints

- Quotas unchanged: R5=30, R6=16, R7=54, W1=5, W2=2, W3=1; timers 75/58.
- Band from **CEFR only** (fallback `difficulty` string → else `mid`). **No** part-based band shift.
- **No** `difficulty_p`, profile external exam, concordance, or score_map retune in this phase.
- No CAT; no ETS official-score claims.
- r6/r7 keep passage groups; band tolerance ±1 or fail.
- Orchestrator style.

### `PART_BAND_QUOTA` (must match spec)

```python
PART_BAND_QUOTA = {
    "r5": {"easy": 15, "mid": 10, "hard": 5},
    "r6": {"easy": 4, "mid": 8, "hard": 4},
    "r7": {"easy": 8, "mid": 19, "hard": 27},
    "w1": {"easy": 3, "mid": 2, "hard": 0},
    "w2": {"easy": 0, "mid": 2, "hard": 0},
    "w3": {"easy": 0, "mid": 0, "hard": 1},
}
```

---

## File map

| File | Role |
|------|------|
| `backend/app/services/placement/difficulty.py` | **New** — bands + `PART_BAND_QUOTA` |
| `backend/app/services/placement/assembler.py` | Stratified pick |
| `backend/app/services/placement/session_service.py` | `_question_to_item` includes `cefr_level`, `difficulty` |
| `backend/tests/test_placement_difficulty.py` | **New** |
| `backend/tests/test_placement_assembler.py` | Strata / missing band cases |

---

### Task 1: `difficulty.py` + tests

**Produces:**

```python
Band = Literal["easy", "mid", "hard"]
PART_BAND_QUOTA: dict[str, dict[Band, int]]

def band_for_item(item: Mapping[str, Any]) -> Band: ...
def band_quota_for_part(part: str) -> dict[Band, int]: ...
```

- [x] Tests: A2→easy, B1→mid, B2→hard; medium string→mid; missing→mid; each part quota sums to part total
- [x] Implement
- [ ] Commit: `feat(placement): CEFR difficulty bands and part-curve quotas`

---

### Task 2: Wire stratified `assemble_form`

**Files:** `assembler.py`, `session_service.py`, `test_placement_assembler.py`

- [x] For each part, pick per `PART_BAND_QUOTA[part]` from banded pools
- [x] r6/r7 passage-group aware pick with ±1 tolerance
- [x] `BankTooSmallError` includes part/band/need/have
- [x] Tests: rich pool → exact (or ±1 for r6/r7) counts; missing r5/hard → error
- [ ] Commit: `feat(placement): assemble forms with part-curve difficulty blueprint`

---

### Task 3: Docs status

- [x] Mark design spec status when implemented
- [x] Note admin: publish enough items per part×CEFR band to satisfy table
- [ ] Commit: `docs(placement): part-curve assemble status`

---

## Out of scope (do not implement in this plan)

- `difficulty_p` / `difficulty_n` migrations
- Calibration on complete
- External exam columns / concordance / FE self-report
- Changing `score_map` thresholds

---

## Definition of done

- [x] Form assembly uses CEFR→band + `PART_BAND_QUOTA`
- [x] Unit tests green
- [x] No new DB columns required for this phase
- [x] Spec/plan describe heuristic (not ETS official counts)

**Admin note:** Placement start fails unless the published bank has enough items for each `part/band` in `PART_BAND_QUOTA` (e.g. r5 needs 5× B2/C1 as hard). Generate/publish across CEFR levels, not only A1–A2.
