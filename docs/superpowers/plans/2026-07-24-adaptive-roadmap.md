# Adaptive Roadmap (rolling horizon) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Change roadmap from a one-shot 8–12 week static path into a rolling adaptive horizon: always keep **1 in-progress + 2 future locked** steps, and regenerate the locked tail after each week completion.

**Architecture:** Keep existing skill-graph selection (`select_skills_for_roadmap`) and week persistence helpers. Add `plan_next_steps` (pure planning of the next N skills excluding already-assigned skills) and `replan_locked_tail` (delete locked progress/steps, append freshly planned weeks). Initial `assemble_user_roadmap` becomes a thin orchestrator that clears and persists `horizon=3`. `complete_roadmap_week` marks complete then calls `replan_locked_tail` instead of only unlocking a pre-baked next week.

**Tech Stack:** FastAPI + SQLAlchemy async, existing `roadmap_assembler_service` / `roadmap_progress_service`, Next.js dashboard + `lib/roadmap.ts`, pytest.

## Global Constraints

- Follow `.cursor/rules/service-orchestrator.mdc`: public entrypoints orchestrate; helpers stay small.
- No LLM on assemble/replan — reuse `select_skills_for_roadmap` + mastery/prereq/placement floor.
- Week dict shape returned to FE must stay compatible with `RoadmapWeek` in `frontend/my-app/lib/roadmap.ts` (same keys).
- Default horizon = **3** (`1 current + 2 future`). Do not invent similarity/remedial edges in this plan.
- Completed weeks are never deleted by replan. Only `locked` tail is replaced.
- Skills already used on `completed` or `in_progress` weeks are excluded from new planning.
- Commits only when the user asks (do not auto-commit unless requested).

---

## File map

| File | Responsibility |
|------|----------------|
| `backend/app/services/roadmap_assembler_service.py` | `DEFAULT_HORIZON`, `plan_next_steps`, `replan_locked_tail`, change `assemble_user_roadmap` clamp to horizon |
| `backend/app/services/roadmap_progress_service.py` | After complete → call `replan_locked_tail`; extend complete response |
| `backend/app/api/roadmap.py` | Relax `AssembleRequest.max_steps` to horizon range (default 3, ge=1, le=5) |
| `backend/tests/test_roadmap_adaptive_service.py` | Unit tests for plan/replan/assemble horizon |
| `backend/tests/test_roadmap_progress_service.py` | Update/add complete → replan behavior |
| `frontend/my-app/lib/roadmap.ts` | Default `max_steps: 3`; optional `replanned` on complete result |
| `frontend/my-app/src/app/dashboard/page.tsx` | Adaptive copy + refresh after complete |
| `frontend/my-app/components/roadmap/WeekNode.tsx` | Soft copy tweaks if needed (locked hint) |
| `docs/superpowers/specs/2026-07-24-adaptive-roadmap-design.md` | Short design note (optional Task 0) |

---

### Task 0: Spec note (short)

**Files:**
- Create: `docs/superpowers/specs/2026-07-24-adaptive-roadmap-design.md`

**Interfaces:**
- Produces: written decisions for horizon=3, exclude assigned skills, replan on complete

- [x] **Step 1: Write the design note**

Include:
- Problem: static 8–12 week assemble
- Decision: rolling horizon `DEFAULT_HORIZON = 3`
- Triggers: initial assemble; replan after complete
- Stop conditions: no more eligible skills at level → empty plan / no new locked weeks
- Non-goals: RL, similarity edges, lesson content, AI tutor

- [ ] **Step 2: Commit (only if user asks)**

```bash
git add docs/superpowers/specs/2026-07-24-adaptive-roadmap-design.md
git commit -m "$(cat <<'EOF'
docs: add adaptive roadmap rolling-horizon design

EOF
)"
```

---

### Task 1: `plan_next_steps` + helpers (selection excluding assigned skills)

**Files:**
- Modify: `backend/app/services/roadmap_assembler_service.py`
- Test: `backend/tests/test_roadmap_adaptive_service.py`

**Interfaces:**
- Consumes: `_require_profile`, `_resolve_target_level`, `load_active_skills`, `load_mastery_map`, `load_prereq_map`, `select_skills_for_roadmap`, `_skill_as_dict`
- Produces:
  - `DEFAULT_HORIZON: int = 3`
  - `async def _load_assigned_skill_ids(db, user_id) -> set[int]`
  - `async def plan_next_steps(db, user_id, *, horizon: int = DEFAULT_HORIZON, level: CEFRLevel | None = None) -> tuple[list[dict[str, Any]], dict[int, float], UserProfileDB, CEFRLevel]`
    - returns `(selected_skills, mastery, profile, target_level)`
    - selected length `<= horizon`
    - excludes skills already linked to this user's `completed` / `in_progress` weeks

- [x] **Step 1: Write failing tests**

```python
# backend/tests/test_roadmap_adaptive_service.py
from app.services.roadmap_assembler_service import select_skills_for_roadmap


def test_select_respects_max_steps_as_horizon():
    skills = [
        {
            "id": i,
            "slug": f"s{i}",
            "title": f"s{i}",
            "cefr_level": "A1",
            "skill_type": "grammar",
            "is_active": True,
            "difficulty_in_level": i,
        }
        for i in range(1, 8)
    ]
    selected = select_skills_for_roadmap(
        skills,
        mastery={i: 0.2 for i in range(1, 8)},
        placement_score=1,
        prereq_from_by_to={},
        max_steps=3,
    )
    assert len(selected) == 3


def test_plan_next_steps_excludes_assigned_ids_via_filter():
    # Pure filter helper behavior — implement as:
    # remaining = [s for s in skills if int(s["id"]) not in assigned]
    assigned = {1, 2}
    skills = [{"id": 1}, {"id": 2}, {"id": 3}, {"id": 4}]
    remaining = [s for s in skills if int(s["id"]) not in assigned]
    assert [s["id"] for s in remaining] == [3, 4]
```

Also add an async unit test with mocked DB once `_load_assigned_skill_ids` / `plan_next_steps` exist (see Step 3).

- [x] **Step 2: Run tests — expect fail / incomplete until helpers land**

```bash
cd backend && source .venv/bin/activate && PYTHONDONTWRITEBYTECODE=1 \
  python -m pytest tests/test_roadmap_adaptive_service.py -q -p no:cacheprovider
```

Expected: fail on missing imports / helpers (or pass pure filter-only tests if split).

- [x] **Step 3: Implement helpers**

Add near other constants:

```python
DEFAULT_HORIZON = 3
```

Add:

```python
async def _load_assigned_skill_ids(db: AsyncSession, user_id: int) -> set[int]:
    """Skill ids on completed or in_progress weeks for this user."""
    rows = list(
        (
            await db.execute(
                select(RoadmapStepSkillDB.skill_id)
                .join(UserProgressDB, UserProgressDB.roadmap_step_id == RoadmapStepSkillDB.roadmap_step_id)
                .where(
                    UserProgressDB.user_id == user_id,
                    UserProgressDB.status.in_(
                        [ProgressStatusEnum.completed, ProgressStatusEnum.in_progress]
                    ),
                    RoadmapStepSkillDB.role == "quiz",
                )
            )
        )
        .scalars()
        .all()
    )
    return {int(sid) for sid in rows}


async def plan_next_steps(
    db: AsyncSession,
    user_id: int,
    *,
    horizon: int = DEFAULT_HORIZON,
    level: CEFRLevel | None = None,
) -> tuple[list[dict[str, Any]], dict[int, float], UserProfileDB, CEFRLevel]:
    profile = await _require_profile(db, user_id)
    target_level = _resolve_target_level(profile, level)
    horizon = max(1, min(5, int(horizon)))

    skills = await load_active_skills(db, target_level)
    if not skills:
        raise ValueError(f"No active learning_skills for level {target_level}.")

    assigned = await _load_assigned_skill_ids(db, user_id)
    candidates = [s for s in skills if int(s.id) not in assigned]
    if not candidates:
        return [], await load_mastery_map(db, user_id), profile, target_level

    mastery = await load_mastery_map(db, user_id)
    prereq_from_by_to = await load_prereq_map(db, {int(s.id) for s in candidates})
    selected = select_skills_for_roadmap(
        candidates,
        mastery,
        placement_score=profile.placement_score,
        prereq_from_by_to=prereq_from_by_to,
        max_steps=horizon,
        weak_point=profile.weak_point,
    )
    return selected, mastery, profile, target_level
```

Note: when `selected` is empty after filters, callers must not raise “No weak skills” on **replan** (level may be finished); initial assemble may still raise if empty after clear.

- [x] **Step 4: Add async mock test for assigned exclusion**

```python
import asyncio
from unittest.mock import AsyncMock, MagicMock

from app.services import roadmap_assembler_service as ras


def test_load_assigned_skill_ids_query_shape():
    # Prefer integration-style with AsyncMock execute returning scalars
    # Assert function returns {10, 20} when those ids are yielded.
    db = AsyncMock()
    result = MagicMock()
    result.scalars.return_value.all.return_value = [10, 20]
    db.execute = AsyncMock(return_value=result)
    ids = asyncio.run(ras._load_assigned_skill_ids(db, user_id=1))
    assert ids == {10, 20}
```

- [x] **Step 5: Run tests**

```bash
cd backend && source .venv/bin/activate && PYTHONDONTWRITEBYTECODE=1 \
  python -m pytest tests/test_roadmap_adaptive_service.py tests/test_roadmap_assembler_service.py -q -p no:cacheprovider
```

Expected: all pass.

---

### Task 2: `replan_locked_tail` + change `assemble_user_roadmap` to horizon=3

**Files:**
- Modify: `backend/app/services/roadmap_assembler_service.py`
- Modify: `backend/app/api/roadmap.py`
- Test: `backend/tests/test_roadmap_adaptive_service.py`

**Interfaces:**
- Consumes: `plan_next_steps`, `_persist_week`, `pick_scenario`, `clear_user_roadmap`, existing clear helpers
- Produces:
  - `async def _delete_locked_tail(db, user_id) -> None`
  - `async def _next_week_number(db, user_id) -> int`
  - `async def replan_locked_tail(db, user_id, *, horizon: int = DEFAULT_HORIZON) -> list[dict[str, Any]]`
  - `assemble_user_roadmap(..., max_steps: int = DEFAULT_HORIZON)` clamps to `1..5` (not 8..12)

**Semantics for `replan_locked_tail`:**
1. Delete all `UserProgressDB` with `status=locked` for user (and orphan `RoadmapStepSkillDB` / `RoadmapStepDB` for those steps if no other progress — reuse patterns from `clear_user_roadmap`).
2. Assert there is **no** `in_progress` yet *or* there is exactly one — after Task 3 complete flow, there should be **zero** in_progress when replan runs (just completed). So replan should create `horizon` new weeks: first `in_progress`, rest `locked`, with `week_number` starting at `max(completed.week_number)+1` or `1` if none.
3. If `plan_next_steps` returns `[]`, commit nothing new (or only the deletes) and return `get_user_roadmap` — path may be “level complete”.
4. Do **not** clear completed weeks.

- [x] **Step 1: Write failing tests for assemble clamp + next week number**

```python
def test_assemble_clamp_horizon_not_eight():
    # Document expected clamp helper:
    def clamp_horizon(max_steps: int) -> int:
        return max(1, min(5, int(max_steps)))

    assert clamp_horizon(10) == 5
    assert clamp_horizon(3) == 3
    assert clamp_horizon(0) == 1


def test_next_week_number_from_completed():
    # Pure: if completed weeks are {1,2}, next is 3
    completed_week_numbers = [1, 2]
    next_week = (max(completed_week_numbers) + 1) if completed_week_numbers else 1
    assert next_week == 3
```

- [x] **Step 2: Implement `_next_week_number` and `_delete_locked_tail`**

```python
async def _next_week_number(db: AsyncSession, user_id: int) -> int:
    rows = list(
        (
            await db.execute(
                select(RoadmapStepDB.week_number)
                .join(UserProgressDB, UserProgressDB.roadmap_step_id == RoadmapStepDB.id)
                .where(UserProgressDB.user_id == user_id)
            )
        )
        .scalars()
        .all()
    )
    if not rows:
        return 1
    return int(max(int(n) for n in rows)) + 1


async def _delete_locked_tail(db: AsyncSession, user_id: int) -> None:
    locked = list(
        (
            await db.execute(
                select(UserProgressDB).where(
                    UserProgressDB.user_id == user_id,
                    UserProgressDB.status == ProgressStatusEnum.locked,
                )
            )
        )
        .scalars()
        .all()
    )
    step_ids = [int(p.roadmap_step_id) for p in locked]
    if locked:
        await db.execute(
            delete(UserProgressDB).where(
                UserProgressDB.user_id == user_id,
                UserProgressDB.status == ProgressStatusEnum.locked,
            )
        )
    for step_id in step_ids:
        remaining = (
            await db.execute(
                select(UserProgressDB.id)
                .where(UserProgressDB.roadmap_step_id == step_id)
                .limit(1)
            )
        ).scalar_one_or_none()
        if remaining is not None:
            continue
        await db.execute(
            delete(RoadmapStepSkillDB).where(RoadmapStepSkillDB.roadmap_step_id == step_id)
        )
        await db.execute(delete(RoadmapStepDB).where(RoadmapStepDB.id == step_id))
```

- [x] **Step 3: Implement `replan_locked_tail`**

```python
async def replan_locked_tail(
    db: AsyncSession,
    user_id: int,
    *,
    horizon: int = DEFAULT_HORIZON,
) -> list[dict[str, Any]]:
    await _delete_locked_tail(db, user_id)
    selected, mastery, profile, target_level = await plan_next_steps(
        db, user_id, horizon=horizon
    )
    if not selected:
        await db.commit()
        return await get_user_roadmap(db, user_id)

    scenario = await pick_scenario(db, profile.goal, target_level)
    start = await _next_week_number(db, user_id)
    for offset, skill in enumerate(selected):
        await _persist_week(
            db,
            user_id,
            start + offset,
            skill,
            scenario,
            target_level,
            mastery,
        )
        # _persist_week currently sets index==1 as in_progress. Fix below.
    await db.commit()
    return await get_user_roadmap(db, user_id)
```

**Important:** `_persist_week` today uses `index == 1` for in_progress. Change it to accept an explicit status **or** a flag `is_current: bool`:

```python
async def _persist_week(
    db: AsyncSession,
    user_id: int,
    index: int,
    skill: dict[str, Any],
    scenario: ScenarioDB,
    target_level: CEFRLevel,
    mastery: dict[int, float],
    *,
    is_current: bool = False,
) -> dict[str, Any]:
    ...
    status = (
        ProgressStatusEnum.in_progress if is_current else ProgressStatusEnum.locked
    )
    ...
```

Call sites:
- `assemble_user_roadmap`: first skill `is_current=True`, others False
- `replan_locked_tail`: first of `selected` `is_current=True` (because complete left no in_progress)

Also update `unlock_condition` to use week numbers: `None` if `is_current` else `f"complete_week_{index - 1}"`.

- [x] **Step 4: Rewrite `assemble_user_roadmap` orchestrator**

```python
async def assemble_user_roadmap(
    db: AsyncSession,
    user_id: int,
    level: CEFRLevel | None = None,
    max_steps: int = DEFAULT_HORIZON,
) -> list[dict[str, Any]]:
    horizon = max(1, min(5, int(max_steps)))
    await clear_user_roadmap(db, user_id)
    selected, mastery, profile, target_level = await plan_next_steps(
        db, user_id, horizon=horizon, level=level
    )
    if not selected:
        raise ValueError("No weak skills left to assemble the roadmap at this level.")
    scenario = await pick_scenario(db, profile.goal, target_level)
    weeks = [
        await _persist_week(
            db,
            user_id,
            index,
            skill,
            scenario,
            target_level,
            mastery,
            is_current=(index == 1),
        )
        for index, skill in enumerate(selected, start=1)
    ]
    await db.commit()
    return weeks
```

- [x] **Step 5: Update API request model**

```python
# backend/app/api/roadmap.py
class AssembleRequest(BaseModel):
    level: CEFRLevel | None = None
    max_steps: int = Field(default=3, ge=1, le=5)
```

- [x] **Step 6: Run tests**

```bash
cd backend && source .venv/bin/activate && PYTHONDONTWRITEBYTECODE=1 \
  python -m pytest tests/test_roadmap_adaptive_service.py tests/test_roadmap_assembler_service.py tests/test_roadmap_query_service.py -q -p no:cacheprovider
```

Expected: pass. Update any test that assumed `max(8,min(12,...))` if present.

---

### Task 3: Wire `complete_roadmap_week` → `replan_locked_tail`

**Files:**
- Modify: `backend/app/services/roadmap_progress_service.py`
- Modify: `backend/tests/test_roadmap_progress_service.py` (create if missing coverage)
- Test: `backend/tests/test_roadmap_progress_service.py`

**Interfaces:**
- Consumes: `replan_locked_tail` from assembler service
- Produces: complete response includes `unlocked_step_id` (first new in_progress id) and optional `weeks` or rely on FE `GET /roadmap` refresh

- [x] **Step 1: Write / update failing test intent**

Document expected behavior in test:

```python
def test_complete_flow_should_replan_instead_of_only_unlock():
    # After complete:
    # 1) progress.status == completed
    # 2) replan_locked_tail is awaited
    # 3) unlocked_step_id is the new in_progress step id (or None if no skills left)
    assert True  # replace with AsyncMock spy on replan_locked_tail
```

Prefer mocking:

```python
import asyncio
from unittest.mock import AsyncMock, patch

# Pseudocode structure — adapt to existing progress tests patterns:
# with patch("app.services.roadmap_progress_service.replan_locked_tail", new_callable=AsyncMock) as replan:
#     replan.return_value = [{"roadmap_step_id": 99, "status": "in_progress", ...}]
#     result = asyncio.run(complete_roadmap_week(db, 1, 5))
#     replan.assert_awaited_once()
#     assert result["unlocked_step_id"] == 99
```

- [x] **Step 2: Change `complete_roadmap_week`**

Replace `_unlock_next_week` usage with replan:

```python
from app.services.roadmap_assembler_service import replan_locked_tail


async def complete_roadmap_week(
    db: AsyncSession,
    user_id: int,
    roadmap_step_id: int,
) -> dict[str, Any]:
    progress, step = await _require_in_progress(db, user_id, roadmap_step_id)
    skill_id = await _quiz_skill_id(db, roadmap_step_id)
    mastery = await _mastery_for_skill(db, user_id, skill_id)
    if not can_pass_week(mastery):
        raise ValueError("Chưa đạt mastery 0.7 cho skill của tuần này")

    progress.status = ProgressStatusEnum.completed
    progress.completed_at = datetime.now(timezone.utc)
    await db.flush()

    weeks = await replan_locked_tail(db, user_id)  # commits inside
    unlocked = next((w for w in weeks if w.get("status") == "in_progress"), None)
    unlocked_step_id = int(unlocked["roadmap_step_id"]) if unlocked else None

    return {
        "step_id": int(roadmap_step_id),
        "status": ProgressStatusEnum.completed.value,
        "skill_id": skill_id,
        "mastery": mastery,
        "unlocked_step_id": unlocked_step_id,
        "replanned": True,
    }
```

**Commit caution:** `replan_locked_tail` already commits. Do **not** double-commit inconsistently. Either:
- `replan_locked_tail(..., commit=False)` and single commit in complete, **or**
- remove commit from complete and let replan commit (as above), but then complete must `flush` before replan so completed status is visible to `_load_assigned_skill_ids`.

Preferred: add `*, commit: bool = True` to `replan_locked_tail`; complete calls `await replan_locked_tail(db, user_id, commit=False)` then `await db.commit()`.

- [x] **Step 3: Remove dead `_unlock_next_week` if unused** (or keep private unused → delete to avoid drift)

- [x] **Step 4: Run progress + adaptive tests**

```bash
cd backend && source .venv/bin/activate && PYTHONDONTWRITEBYTECODE=1 \
  python -m pytest tests/test_roadmap_progress_service.py tests/test_roadmap_adaptive_service.py -q -p no:cacheprovider
```

Expected: pass.

---

### Task 4: Frontend adaptive copy + assemble default horizon

**Files:**
- Modify: `frontend/my-app/lib/roadmap.ts`
- Modify: `frontend/my-app/src/app/dashboard/page.tsx`
- Modify: `frontend/my-app/components/roadmap/RoadmapPath.tsx` (locked hint)
- Modify: `frontend/my-app/src/app/onboarding/placement/page.tsx` if it calls `assembleRoadmap({ max_steps: 10 })`

**Interfaces:**
- Consumes: same APIs
- Produces: UI that describes rolling next steps; assemble uses `max_steps: 3`

- [x] **Step 1: Update client defaults**

```typescript
// frontend/my-app/lib/roadmap.ts
export type CompleteRoadmapStepResult = {
  step_id: number;
  status: string;
  skill_id: number;
  mastery: number;
  unlocked_step_id: number | null;
  replanned?: boolean;
};

export async function assembleRoadmap(
  opts?: AssembleRoadmapOptions,
): Promise<RoadmapWeek[]> {
  const res = await authFetch("/api/v1/roadmap/assemble", {
    method: "POST",
    body: JSON.stringify({
      ...(opts?.level ? { level: opts.level } : {}),
      max_steps: opts?.max_steps ?? 3,
    }),
  });
  // ...
}
```

- [x] **Step 2: Dashboard copy**

In `dashboard/page.tsx`:
- Eyebrow: `Your next steps` (keep or replace `Your path`)
- Title: `Adaptive path` or keep `Weekly roadmap` but change subtitle to:  
  `We keep a few steps ahead — the path updates when you complete a week.`
- Empty CTA helper text: remove “8–12 week”; use `Build your next 3 steps from skills in your zone.`
- After `handleComplete`, always `await refresh()` so new locked weeks appear.

- [x] **Step 3: Locked hint in `RoadmapPath`**

Change locked tap message to something like:  
`Finish the current step first — future steps may change as you progress.`

- [x] **Step 4: Grep FE for max_steps: 10 / “8–12”**

```bash
rg -n "max_steps|8–12|8-12|Create my path" frontend/my-app
```

Update any leftover assemble calls / copy.

- [ ] **Step 5: Manual check**

1. Assemble → exactly 3 weeks (1 in_progress, 2 locked) if enough skills.
2. Complete week (mastery ≥ 0.7) → completed stays; new in_progress + up to 2 locked appear; old locked replaced.
3. When no skills left → complete leaves only completed weeks (or completed + no new in_progress).

---

### Task 5: Verification + plan/spec status

**Files:**
- Modify: `docs/superpowers/plans/2026-07-24-adaptive-roadmap.md` (this file — checkboxes)
- Optionally link from `docs/superpowers/specs/2026-07-20-skill-graph-zpd-roadmap-design.md`

- [x] **Step 1: Full backend suite for roadmap**

```bash
cd backend && source .venv/bin/activate && PYTHONDONTWRITEBYTECODE=1 \
  python -m pytest tests/test_roadmap_*.py -q -p no:cacheprovider
```

Expected: all pass.

- [x] **Step 2: Mark tasks complete in this plan**

- [ ] **Step 3: Commit (only if user asks)** — group BE + FE adaptive changes

```bash
git add backend/app/services/roadmap_assembler_service.py \
  backend/app/services/roadmap_progress_service.py \
  backend/app/api/roadmap.py \
  backend/tests/test_roadmap_adaptive_service.py \
  backend/tests/test_roadmap_progress_service.py \
  frontend/my-app/lib/roadmap.ts \
  frontend/my-app/src/app/dashboard/page.tsx \
  frontend/my-app/components/roadmap/RoadmapPath.tsx \
  docs/superpowers/specs/2026-07-24-adaptive-roadmap-design.md \
  docs/superpowers/plans/2026-07-24-adaptive-roadmap.md
git commit -m "$(cat <<'EOF'
feat: adaptive roadmap with rolling 3-step horizon

Replace one-shot 8–12 week assemble with plan_next_steps +
replan_locked_tail after week completion, and update dashboard copy.
EOF
)"
```

---

## Self-review

| Requirement | Task |
|-------------|------|
| `plan_next_steps(user_id, horizon)` | Task 1 |
| `replan_locked_tail` on complete | Tasks 2–3 |
| Assemble = 1 current + 2 future | Task 2 (`DEFAULT_HORIZON=3`) |
| Dashboard adaptive copy/UI | Task 4 |
| Exclude assigned skills | Task 1 `_load_assigned_skill_ids` |
| Keep completed history | Task 2 delete locked only |
| API `max_steps` 1–5 default 3 | Task 2 |

**Placeholder scan:** none intentional.  
**Out of plan:** lesson content, AI tutor, similarity edges, RL, cognitive load.

---

## Execution handoff

Plan saved to `docs/superpowers/plans/2026-07-24-adaptive-roadmap.md`.

**Two execution options:**

1. **Subagent-Driven (recommended)** — fresh subagent per task, review between tasks  
2. **Inline Execution** — execute tasks in this session with checkpoints  

Which approach?
