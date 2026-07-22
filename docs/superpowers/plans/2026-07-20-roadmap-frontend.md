# Roadmap Frontend (Duolingo-style path) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Learner can open `/dashboard`, see a weekly ZPD path, complete a week when mastery ≥ 0.7, and optionally take a +1 CEFR level challenge — wired to existing backend APIs.

**Architecture:** Thin Next.js App Router clients call `authFetch` → FastAPI. UI is a **vertical weekly path** (completed / current / locked), not a React Flow skill graph. Backend remains source of truth for ZPD assemble + unlock. Add `GET /roadmap` so dashboard can reload without re-assembling.

**Tech Stack:** Next.js 16 App Router, React 19, TypeScript, Tailwind 4 + shadcn/ui, `authFetch` in `frontend/my-app/src/lib/api.ts`.

## Global Constraints

- Match existing onboarding/placement UX patterns (`frontend/my-app/src/app/onboarding/**`, `lib/placement.ts`-style clients).
- **No LLM on assemble** in FE copy or calls — only `POST /roadmap/assemble` + `GET /roadmap`.
- Product UI first (utility), then optional visual polish pass — see **Taste skill decision** below.
- Follow project Cursor rules: `service-orchestrator` (BE only); user frontend-design rules for learner surfaces (no purple-gradient AI slop; path = one composition).
- API clients live under `frontend/my-app/lib/` (same as `placement.ts`, not `src/lib`).
- Vietnamese or English UI copy: match existing onboarding language (currently English strings in placement).
- Do not invent quiz-taking FE in this plan unless a skill quiz route already exists; week complete can assume mastery updated elsewhere or stub a “practice” link.

## Taste skill decision (Exa research)

**Question:** Should we use [Taste Skill](https://www.tasteskill.dev/) / `design-taste-frontend` to improve UI?

| Verdict | Detail |
|--------|--------|
| **Yes — but only as a polish pass** | Taste / Anthropic `frontend-design` raise the floor against generic “AI slop” (typography, spacing, motion). |
| **Not for Task 1–4 wiring** | Wiring `lib/roadmap.ts` + empty states does not need aesthetic skills; they add noise and can fight shadcn tokens. |
| **Prefer product-oriented variant** | Exa + tasteskill docs: default taste is strongest for **landing/portfolio**. For app path UI use **`minimalist-ui`** (Linear/Notion restraint) or soft-skill; avoid brutalist / high variance. |
| **Existing project** | If polishing onboarding + new dashboard together, [`redesign-existing-projects`](https://github.com/Leonxlnx/taste-skill) (audit-first) is safer than greenfield taste. |
| **Already have overlap** | Cursor user rules already ban purple-on-white, cream+terracotta, broadsheet — same anti-slop intent. Taste is optional amplifier, not required. |

**Recommended workflow in this plan:** Tasks 0–5 ship functional path with shadcn. **Task 6 (optional)** = one visual pass with `minimalist-ui` or Taste v2 dials `VARIANCE=low`, `MOTION=low–med`, `DENSITY=med`.

---

## File map

| File | Responsibility |
|------|----------------|
| `backend/app/api/roadmap.py` | Add `GET /` current roadmap |
| `backend/app/services/roadmap_assembler_service.py` (or new `roadmap_query_service.py`) | `get_user_roadmap(db, user_id) -> list[dict]` same shape as assemble weeks |
| `frontend/my-app/lib/roadmap.ts` | `assembleRoadmap`, `fetchRoadmap`, `completeRoadmapStep` |
| `frontend/my-app/lib/level-challenge.ts` | `fetchLevelChallenge`, `submitLevelChallenge` |
| `frontend/my-app/src/app/dashboard/page.tsx` | Path home |
| `frontend/my-app/components/roadmap/RoadmapPath.tsx` | Vertical week nodes |
| `frontend/my-app/components/roadmap/WeekNode.tsx` | Single week state UI |
| `frontend/my-app/src/app/dashboard/level-challenge/page.tsx` | +1 CEFR quiz (reuse placement patterns) |
| `frontend/my-app/src/app/onboarding/placement/page.tsx` | CTA → assemble → dashboard |

---

### Task 0: Backend `GET /api/v1/roadmap`

**Files:**
- Modify: `backend/app/api/roadmap.py`
- Modify: `backend/app/services/roadmap_assembler_service.py` (add `get_user_roadmap`) **or** Create: `backend/app/services/roadmap_query_service.py`
- Test: `backend/tests/test_roadmap_query_service.py`

**Interfaces:**
- Consumes: `UserProgressDB`, `RoadmapStepDB`, `RoadmapStepSkillDB`, mastery map
- Produces: same week dict shape as `assemble_user_roadmap` return items; empty list if none

- [ ] **Step 1: Failing test — empty roadmap**

```python
# backend/tests/test_roadmap_query_service.py
import pytest
from unittest.mock import AsyncMock, MagicMock

# Prefer testing a pure mapper if extracting one; otherwise integration-style with mocks.
from app.services.roadmap_assembler_service import weeks_from_progress_rows  # or get_user_roadmap helpers


def test_empty_progress_maps_to_empty_weeks():
    assert weeks_from_progress_rows([], skills_by_step={}, mastery={}, scenarios={}) == []
```

(If you keep logic inside `get_user_roadmap` only, use AsyncMock session returning no rows and assert `[]`.)

- [ ] **Step 2: Implement `get_user_roadmap`**

Return for each user progress row (ordered by `RoadmapStepDB.week_number`):

```python
{
  "week_number": int,
  "roadmap_step_id": int,
  "title": str,
  "skill_id": int,
  "skill_slug": str,
  "skill_title": str | None,
  "skill_type": str | None,
  "difficulty_in_level": int,
  "scenario_id": int,
  "scenario_title": str,
  "status": str,  # locked | in_progress | completed
  "mastery": float,
  "level": str,
}
```

- [ ] **Step 3: Route**

```python
@router.get("")
async def get_roadmap(...):
    data = await get_user_roadmap(db, int(current_user.id))
    return {"data": data}
```

- [ ] **Step 4: Run tests**

```bash
cd backend && .venv/bin/python -m pytest tests/test_roadmap_query_service.py tests/test_roadmap_assembler_service.py -v
```

- [ ] **Step 5: Commit** (when user asks)

```bash
git add backend/app/api/roadmap.py backend/app/services/roadmap_assembler_service.py backend/tests/test_roadmap_query_service.py
git commit -m "$(cat <<'EOF'
feat: GET current user roadmap for dashboard reload

EOF
)"
```

---

### Task 1: FE API clients

**Files:**
- Create: `frontend/my-app/lib/roadmap.ts`
- Create: `frontend/my-app/lib/level-challenge.ts`
- Reuse: `frontend/my-app/lib/api.ts` (`authFetch`)

**Interfaces:**
- Consumes: `POST /api/v1/roadmap/assemble`, `GET /api/v1/roadmap`, `POST /api/v1/roadmap/steps/{id}/complete`, onboarding level-challenge endpoints
- Produces: typed helpers below

- [x] **Step 1: Types + roadmap client**

```typescript
// frontend/my-app/lib/roadmap.ts
export type RoadmapWeekStatus = "locked" | "in_progress" | "completed";

export type RoadmapWeek = {
  week_number: number;
  roadmap_step_id: number;
  title: string;
  skill_id: number;
  skill_slug: string;
  skill_title: string | null;
  skill_type: string | null;
  difficulty_in_level: number;
  scenario_id: number;
  scenario_title: string;
  status: RoadmapWeekStatus;
  mastery: number;
  level: string;
};

export async function fetchRoadmap(): Promise<RoadmapWeek[]> { /* GET */ }
export async function assembleRoadmap(opts?: {
  level?: string;
  max_steps?: number;
}): Promise<RoadmapWeek[]> { /* POST body */ }
export async function completeRoadmapStep(
  roadmapStepId: number
): Promise<{
  step_id: number;
  status: string;
  skill_id: number;
  mastery: number;
  unlocked_step_id: number | null;
}> { /* POST */ }
```

- [x] **Step 2: Level challenge client** (mirror `lib/placement.ts` shapes)

```typescript
// frontend/my-app/lib/level-challenge.ts
export async function fetchLevelChallengeQuestions(targetLevel?: string): Promise<{
  target_level: string;
  question_count: number;
  questions: Array<{ /* same public fields as placement */ }>;
}> { /* GET /api/v1/onboarding/level-challenge */ }

export async function submitLevelChallenge(body: {
  target_level: string;
  answers: Array<{ question_id: number; answer: string }>;
}): Promise<{
  passed: boolean;
  correct_count: number;
  total: number;
  current_level: string;
  placement_score: number | null;
  target_level: string;
}> { /* POST */ }
```

- [x] **Step 3: Manual smoke** — clients mirror `placement.ts`; `tsc` shows no errors in new files. Live HTTP smoke deferred until Task 0 (`GET /roadmap`) + auth session.

- [ ] **Step 4: Commit** (when user asks)

---

### Task 2: Dashboard + vertical path UI

**Files:**
- Create: `frontend/my-app/src/app/dashboard/page.tsx`
- Create: `frontend/my-app/components/roadmap/RoadmapPath.tsx`
- Create: `frontend/my-app/components/roadmap/WeekNode.tsx`

**Interfaces:**
- Consumes: `fetchRoadmap`, `assembleRoadmap`, `completeRoadmapStep`
- Produces: learner home at `/dashboard`

- [ ] **Step 1: Empty / load states**

On mount: `fetchRoadmap()`. If `[]`, show primary CTA **“Create my path”** → `assembleRoadmap()` → set weeks.

Header: CEFR level + short line (from onboarding status or first week’s `level`).

- [ ] **Step 2: `WeekNode` states**

| `status` | Visual | Actions |
|----------|--------|---------|
| `completed` | check / muted | optional review (no-op OK) |
| `in_progress` | emphasized “current” | Show mastery bar; **Complete week** enabled iff `mastery >= 0.7` |
| `locked` | muted lock | Tap → toast/helper: finish previous week |

Layout: vertical stack with slight zigzag offset (Duolingo-path pattern). One clear current node.

- [ ] **Step 3: Complete week**

```typescript
async function onComplete(week: RoadmapWeek) {
  await completeRoadmapStep(week.roadmap_step_id);
  setWeeks(await fetchRoadmap());
}
```

Map API 400 → inline error under current node.

- [ ] **Step 4: Manual check**

Login as onboarded user → `/dashboard` → Create path → see 8–12 weeks → only week 1 `in_progress`.

- [ ] **Step 5: Commit** (when user asks)

---

### Task 3: Wire placement success → assemble

**Files:**
- Modify: `frontend/my-app/src/app/onboarding/placement/page.tsx`

- [ ] **Step 1:** On placement success screen, primary button:

```typescript
async function goToRoadmap() {
  setBusy(true);
  try {
    await assembleRoadmap({ max_steps: 10 });
    router.push("/dashboard");
  } catch (e) {
    setError(/* message */);
  } finally {
    setBusy(false);
  }
}
```

Secondary: “Go to dashboard” without assemble (empty CTA there).

- [ ] **Step 2: Manual** — finish placement → path appears on dashboard.

- [ ] **Step 3: Commit** (when user asks)

---

### Task 4: Level challenge page

**Files:**
- Create: `frontend/my-app/src/app/dashboard/level-challenge/page.tsx`
- Modify: `frontend/my-app/src/app/dashboard/page.tsx` — link “Level feels too easy?”

- [ ] **Step 1:** Clone placement quiz UX; call `fetchLevelChallengeQuestions` / `submitLevelChallenge`.

- [ ] **Step 2:** Result UI

- `passed` → show new level + “Build new path” → `assembleRoadmap()` → `/dashboard`
- `!passed` → stay on level; CTA back to dashboard

- [ ] **Step 3: Manual** — need ≥6 published Q at next CEFR; pass ≥4/6.

- [ ] **Step 4: Commit** (when user asks)

---

### Task 5: Practice / mastery bridge (minimal)

**Files:**
- Create: `frontend/my-app/lib/quiz.ts`
- Create: `frontend/my-app/src/app/dashboard/practice/[skillId]/page.tsx`
- Modify: `frontend/my-app/components/roadmap/WeekNode.tsx`

**Goal:** User can raise mastery via existing `GET/POST /api/v1/quiz/*` (no fake mastery).

- [x] **Step 1:** Mastery % + copy on in-progress week
- [x] **Step 2:** **Practice skill** → `/dashboard/practice/{skill_id}` (wraps BE quiz API); refresh path after return
- [ ] **Step 3: Commit** (when user asks)

---

### Task 6 (optional): Visual polish with Taste / minimalist skill — DONE

**When:** After Tasks 0–5 work end-to-end.

**How:**
1. Install if missing: Taste `design-taste-frontend` **or** `minimalist-ui` (recommended for product path).
2. Prompt agent: *“Polish `/dashboard` RoadmapPath only. Keep shadcn tokens. Dials: low variance, medium density, light motion on current node only. No new purple gradients. Preserve all API wiring.”*
3. Do **not** restyle admin books panel in the same pass.
4. Screenshot mobile + desktop; respect `prefers-reduced-motion`.

- [x] **Step 1:** Installed `minimalist-ui` skill at `.cursor/skills/minimalist-ui/SKILL.md` (CLI subpath scan failed → placed in-repo so it persists per-project).
- [x] **Step 2:** Scoped polish to `/dashboard` roadmap surface only (dashboard page, `RoadmapPath`, `WeekNode`). Admin/books untouched; all API wiring preserved.
  - Added quiet staggered scroll/mount entry (`.ef-fade-up`, `transform`+`opacity` only, `--ef-index` cascade) in `globals.css`, gated by `prefers-reduced-motion: reduce`.
  - Replaced the noisy pulsing current-node (`motion-safe:animate-pulse` + heavy shadow) with a still, subtle `ring-4 ring-primary/10`; added `active:scale-95` micro-interaction.
  - Flatter surfaces: 1px crisp borders, removed backdrop-blur, tighter editorial type hierarchy, more macro-whitespace; kept shadcn tokens + lucide for app consistency (no gradients added).
- [x] **Step 3:** Verified — `tsc --noEmit` clean for touched files; no new lint errors (only pre-existing Tailwind v4 at-rule warnings).
- [ ] **Step 4: Commit** (when user asks)

**Note:** Kept the existing dark theme + lucide icons rather than importing the skill's light warm-monochrome palette / Phosphor icons wholesale, to stay consistent with the rest of the app (low-variance dial the plan asked for). Applied the *spirit* of minimalist-ui (flat, whitespace, type contrast, quiet motion) within current tokens.

**Skip Task 6 if:** shipping deadline & shadcn path already clear — user rules already block worst AI-slop defaults.

---

## Self-review (plan vs needs)

| Need | Task |
|------|------|
| Reload path without re-assemble | Task 0 |
| Client API | Task 1 |
| `/dashboard` path UI | Task 2 |
| Post-placement funnel | Task 3 |
| +1 CEFR challenge FE | Task 4 |
| Mastery loop | Task 5 (bridge) / future quiz plan |
| Better visuals | Task 6 optional |

**Out of plan:** React Flow full skill graph, FE difficulty badges, auto re-assemble, admin redesign, learner quiz bank UI (unless already present).

**Placeholder scan:** none intentional.

---

## Execution handoff

Plan saved to `docs/superpowers/plans/2026-07-20-roadmap-frontend.md`.

**Two execution options:**

1. **Subagent-Driven (recommended)** — fresh subagent per task, review between tasks  
2. **Inline Execution** — execute tasks in this session with checkpoints  

Which approach?
