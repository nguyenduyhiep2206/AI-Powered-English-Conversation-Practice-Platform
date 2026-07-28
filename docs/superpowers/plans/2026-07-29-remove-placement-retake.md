# Remove Placement Retake (7-day Cooldown) Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Remove the ability to retake the placement test after a 7-day cooldown; users may complete placement once (and resume an in-progress attempt), then never start a new placement.

**Architecture:** Keep first-time placement and resume-in-progress. Change gate from `now - last_completed >= 7 days` to `placement_score is None` (never completed). Drop dashboard retake / cooldown UI; keep optional `has_in_progress` resume link. Do **not** commit unless the user asks.

**Tech Stack:** FastAPI + SQLAlchemy async, Next.js App Router, pytest

## Global Constraints

- Do not commit (user request).
- First-time placement and resume of `in_progress` must keep working.
- Do not remove the whole placement product — only retake-after-complete / 7-day cooldown.
- Prefer small diffs; update tests that assert the 7-day window.

## File map

| File | Change |
|------|--------|
| `backend/app/services/placement/session_service.py` | Drop cooldown; block new session if already completed |
| `backend/tests/test_placement_session_helpers.py` | Assert never-retake semantics |
| `frontend/my-app/src/app/dashboard/page.tsx` | Remove Retake / Retake after UI |
| `frontend/my-app/src/app/onboarding/placement/page.tsx` | Enter only if not done or has in-progress |
| `frontend/my-app/lib/placement.ts` | Keep `fetchRetakeStatus` for `has_in_progress` (optional `retry_after_at` unused) |
| `docs/superpowers/specs/2026-07-23-adaptive-placement-design.md` | Note: retake cooldown removed (optional short note) |

---

### Task 1: Backend — no retake after complete

**Files:**
- Modify: `backend/app/services/placement/session_service.py`
- Modify: `backend/tests/test_placement_session_helpers.py`

**Interfaces:**
- Consumes: `UserProfileDB.placement_score`, in-progress attempt helpers
- Produces: `retake_allowed` / `_retake_allowed_for_profile` / `get_retake_status` with `allowed=True` only when never completed and no in-progress; `retry_after_at` always `None`

- [ ] **Step 1: Rewrite failing tests**

```python
from datetime import datetime, timezone

from app.services.placement.session_service import (
    _retake_allowed_for_profile,
    retake_allowed,
)


def test_retake_allowed_never_completed():
    assert retake_allowed(last_completed_at=None, now=datetime.now(timezone.utc)) is True


def test_retake_never_after_completed():
    now = datetime(2026, 7, 23, tzinfo=timezone.utc)
    assert retake_allowed(now, now) is False


def test_retake_allowed_for_profile_first_time():
    now = datetime(2026, 7, 23, tzinfo=timezone.utc)
    assert (
        _retake_allowed_for_profile(
            has_in_progress=False,
            last_completed_at=None,
            placement_score=None,
            now=now,
        )
        is True
    )


def test_retake_allowed_for_profile_blocks_completed():
    now = datetime(2026, 7, 23, tzinfo=timezone.utc)
    assert (
        _retake_allowed_for_profile(
            has_in_progress=False,
            last_completed_at=now,
            placement_score=5,
            now=now,
        )
        is False
    )


def test_retake_allowed_for_profile_blocks_in_progress():
    now = datetime(2026, 7, 23, tzinfo=timezone.utc)
    assert (
        _retake_allowed_for_profile(
            has_in_progress=True,
            last_completed_at=None,
            placement_score=None,
            now=now,
        )
        is False
    )
```

- [ ] **Step 2: Run tests — expect fail on old cooldown**

Run: `cd backend && python -m pytest tests/test_placement_session_helpers.py -v`

- [ ] **Step 3: Implement**

In `session_service.py`:

1. Remove `RETAKE_COOLDOWN_DAYS`, `_retry_after_at`, and `timedelta` usage for cooldown.
2. Replace `retake_allowed` with:

```python
def retake_allowed(
    last_completed_at: datetime | None,
    now: datetime | None = None,
) -> bool:
    """True only when the user has never completed a placement attempt."""
    del now  # kept for call-site compatibility
    return last_completed_at is None
```

Prefer gating on `placement_score` in `_retake_allowed_for_profile`:

```python
def _retake_allowed_for_profile(
    *,
    has_in_progress: bool,
    last_completed_at: datetime | None,
    placement_score: int | None,
    now: datetime,
) -> bool:
    del now, last_completed_at
    if has_in_progress:
        return False
    return placement_score is None
```

3. `get_retake_status`: always set `"retry_after_at": None`.
4. `start_or_resume_session`: if `profile.placement_score is not None`, raise `RuntimeError("Bạn đã hoàn thành placement")` (no cooldown check).
5. On `complete_session`, remove `was_retake` / `clear_user_roadmap` retake branch (retakes are impossible).

- [ ] **Step 4: Re-run helpers tests — expect PASS**

Run: `cd backend && python -m pytest tests/test_placement_session_helpers.py -v`

- [ ] **Step 5: Do not commit**

---

### Task 2: Frontend — remove retake entry points

**Files:**
- Modify: `frontend/my-app/src/app/dashboard/page.tsx`
- Modify: `frontend/my-app/src/app/onboarding/placement/page.tsx`

**Interfaces:**
- Consumes: `fetchRetakeStatus()` → only `has_in_progress` for resume
- Produces: no “Retake placement” / “Retake after …” UI

- [ ] **Step 1: Dashboard**

- Keep fetching retake status only for `has_in_progress`.
- Header links: only **Resume placement** when `retake?.has_in_progress`; remove `allowed` and `retry_after_at` branches.

- [ ] **Step 2: Placement page gate**

```tsx
const retake = await fetchRetakeStatus().catch(() => null);
const canEnter =
  !status.placement_done || Boolean(retake?.has_in_progress);
if (!canEnter) {
  router.replace("/dashboard");
  return;
}
```

- [ ] **Step 3: Manual check**

- User with completed placement: `/onboarding/placement` → dashboard; dashboard has no Retake link.
- User with in-progress: Resume still works.
- Fresh user: placement still starts.

- [ ] **Step 4: Do not commit**

---

### Task 3: Spec note (optional, light)

**Files:**
- Modify: `docs/superpowers/specs/2026-07-23-adaptive-placement-design.md` (add one-line supersession near retake section)

- [ ] **Step 1:** Add note that 7-day adaptive retake was removed; placement is one-shot (resume in-progress only).
- [ ] **Step 2: Do not commit**

---

## Cleanup follow-up (done in same change set)

Renamed leftover retake surface:

- API: `GET /placement/access-status` → `{ can_start, has_in_progress }` (removed `retry_after_at` / `allowed`)
- Service: `get_placement_access_status`, `can_start_new_placement`
- FE: `fetchPlacementAccessStatus` / `PlacementAccessStatus`
- Dropped `_last_completed_at` / cooldown helpers
