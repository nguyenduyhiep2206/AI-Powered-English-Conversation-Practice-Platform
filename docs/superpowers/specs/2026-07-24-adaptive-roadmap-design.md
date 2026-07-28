# Design: Adaptive roadmap (rolling horizon)

**Date:** 2026-07-24  
**Status:** Spec (Task 0)  
**Depends on:** `2026-07-20-skill-graph-zpd-roadmap-design.md` (ZPD selection, week persistence)  
**Implementation plan:** `docs/superpowers/plans/2026-07-24-adaptive-roadmap.md`

---

## 1. Problem

Roadmap assembly today is a **one-shot static path**: `assemble_user_roadmap` plans **8–12 weeks** upfront (`max_steps` clamped to 8..12), persists them all, and `complete_roadmap_week` only unlocks the next pre-baked locked week.

That means:

- The full tail is chosen before the learner finishes early weeks — mastery and progress cannot reshape what comes next.
- Completing a week does not re-run skill selection; it merely advances status on weeks that were fixed at assemble time.
- Users who finish most skills at a CEFR level still carry a long pre-planned tail instead of stopping when nothing eligible remains.

---

## 2. Decision

Replace the static 8–12 week bake with a **rolling adaptive horizon**:

| Topic | Decision |
|-------|----------|
| Horizon | `DEFAULT_HORIZON = 3` — **1 in-progress + 2 future locked** weeks visible at all times |
| Selection | Reuse existing `select_skills_for_roadmap` (ZPD, prereq, placement floor, weak_point); no LLM on assemble/replan |
| Exclusion | Skills already on **completed** or **in_progress** weeks are excluded from new planning |
| Initial assemble | `assemble_user_roadmap` clears and persists up to `horizon` weeks (not 8–12) |
| After complete | `replan_locked_tail` deletes the **locked** tail only, then appends freshly planned weeks; completed weeks are never deleted |
| Week shape | Returned week dicts stay compatible with frontend `RoadmapWeek` (`frontend/my-app/lib/roadmap.ts`) |

Pure planning lives in `plan_next_steps`; replan orchestration in `replan_locked_tail`. Public entrypoints follow `.cursor/rules/service-orchestrator.mdc`.

---

## 3. Triggers

| Event | Behavior |
|-------|----------|
| **Initial assemble** | User calls `POST /roadmap/assemble` → clear existing roadmap → `plan_next_steps(horizon=3)` → persist weeks (first `in_progress`, rest `locked`) |
| **Week complete** | `complete_roadmap_week` marks the week completed → call `replan_locked_tail` → replace locked tail with up to 2 new locked weeks plus ensure one in-progress head |

Replan does **not** run on placement completion or mastery updates alone — only assemble (fresh start) and week completion (rolling tail refresh).

---

## 4. Stop conditions

Planning stops when `select_skills_for_roadmap` returns no eligible skills at the target CEFR level after excluding assigned skill ids:

- **`plan_next_steps` returns `[]`** — no candidates left (level effectively finished for this user).
- **Initial assemble with empty selection** — may still raise (no path to start); same as today when nothing is teachable.
- **Replan with empty selection** — do **not** raise; delete locked tail if any, commit, return current roadmap (possibly only completed weeks). No new locked weeks are appended.
- **Partial horizon** — if fewer than 3 skills remain, persist only what is available (`len(selected) <= horizon`).

---

## 5. Non-goals

This change does **not** include:

- **Reinforcement learning** or online policy optimization for step order
- **Similarity / remedial edges** on the skill graph (beyond existing prerequisite edges)
- **Lesson content** generation or changes to quiz/excerpt sourcing
- **AI tutor** or LLM calls during assemble or replan

Follow-up work (daily time, IRT, admin edge editing, etc.) remains out of scope unless captured in a separate spec.
