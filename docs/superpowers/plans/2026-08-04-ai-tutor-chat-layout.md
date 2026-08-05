# AI Tutor Chat Layout Restyle Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** Restyle `/ai-tutor/[sessionId]` to a 3-column roleplay chat (scenario | messages | feedback), wire real session/messages/meta, and remove Debug RAG from this UI.

**Architecture:** Keep one Next.js session page and existing tutor SSE API. Enrich `GET/POST /sessions` DTO with nested `scenario` so the left rail has title/roles/vocab without a second fetch. Extract feedback items from assistant `meta` via a pure helper. Persist stays on `tutor_sessions` / `tutor_messages`.

**Tech Stack:** Next.js App Router, existing `lib/tutor.ts`, FastAPI tutor schemas, lucide-react (already used on page), Tailwind + shadcn Button/Input/Badge.

> **Note (commits):** Tasks 1–4 shipped in `a5b5a2b` (session scenario DTO, `tutor-feedback`, strip debug, 3-column rails + page). Task 5 docs commit records acceptance on this branch.

## Global Constraints

- Do not create `/chat` or TanStack routes.
- Catalog + roadmap continue to open `/ai-tutor/{id}`.
- No Debug RAG checkbox/panel; do not pass `debug: true` from this page.
- Feedback only from real `meta.correction` / `meta.hint` (no mock-data).
- End session keeps summary modal; no `/report` page.
- Prefer existing visual language of the app (AppHeader, borders, muted cards) while matching mock structure.
- Commit only when the user explicitly asks (skip automatic git commits during implementation).

---

## File map

| Path | Responsibility |
|------|----------------|
| `backend/app/schemas/tutor_schema.py` | Add optional `scenario` on `TutorSessionDTO` |
| `backend/app/api/tutor.py` | Load scenario into `_session_to_dto` |
| `backend/tests/test_tutor_api_sse.py` or existing tutor API tests | Assert session payload includes scenario |
| `frontend/my-app/lib/tutor.ts` | Types for nested scenario; stream default `debug: false` |
| `frontend/my-app/lib/tutor-feedback.ts` | Pure `collectFeedbackItems` |
| `frontend/my-app/lib/tutor-feedback.test.ts` | Unit tests for feedback helper (if vitest/jest present; else colocate and document manual) |
| `frontend/my-app/components/tutor/TutorSessionChrome.tsx` | Top bar + scenario rail + feedback rail presentational pieces |
| `frontend/my-app/src/app/ai-tutor/[sessionId]/page.tsx` | Wire layout, SSE, end session; remove debug UI |

---

### Task 1: Session DTO includes scenario

**Files:**
- Modify: `backend/app/schemas/tutor_schema.py`
- Modify: `backend/app/api/tutor.py`
- Test: extend existing tutor API test under `backend/tests/`

**Interfaces:**
- Produces: `TutorSessionDTO.scenario: TutorScenarioDTO | None` (always set for valid sessions)
- Consumes: `ScenarioDB` via select by `session.scenario_id`

- [x] **Step 1: Add failing API assertion**

In the suite that starts a tutor session (e.g. `backend/tests/test_tutor_api_sse.py` or `backend/tests/tutor/`), add:

```python
async def test_get_session_includes_scenario(client, auth_headers, tutor_session):
    res = await client.get(
        f"/api/v1/tutor/sessions/{tutor_session.id}",
        headers=auth_headers,
    )
    assert res.status_code == 200
    data = res.json()["data"]
    assert data["scenario"]["id"] == tutor_session.scenario_id
    assert data["scenario"]["title"]
    assert data["scenario"]["ai_role"]
    assert data["scenario"]["user_role"]
    assert "goal_prompt" in data["scenario"]
```

Adapt fixtures/names to match the file you extend.

- [x] **Step 2: Run test — expect fail**

```bash
cd backend && python -m pytest tests/ -k "session_includes_scenario" -v
```

Expected: FAIL (missing `scenario` key or field)

- [x] **Step 3: Schema + DTO fill**

```python
# tutor_schema.py — on TutorSessionDTO
scenario: TutorScenarioDTO | None = None
```

```python
# tutor.py — _session_to_dto
from app.models.scenario import ScenarioDB
# ...
scenario = (
    await db.execute(select(ScenarioDB).where(ScenarioDB.id == session.scenario_id))
).scalar_one_or_none()
dto = TutorSessionDTO.model_validate(session)
return dto.model_copy(
    update={
        "messages": [...],
        "scenario": TutorScenarioDTO.model_validate(scenario) if scenario else None,
    }
)
```

Map enum `category`/`level` the same way catalog endpoint already does (string values).

- [x] **Step 4: Re-run test — expect pass**

```bash
cd backend && python -m pytest tests/ -k "session_includes_scenario" -v
```

Expected: PASS

---

### Task 2: Frontend feedback helper

**Files:**
- Create: `frontend/my-app/lib/tutor-feedback.ts`
- Create: `frontend/my-app/lib/tutor-feedback.test.ts` **only if** the app already has a unit-test runner for `lib/`; otherwise skip file and verify via browser checklist in Task 4

**Interfaces:**
- Produces:

```ts
export type TutorFeedbackItem = {
  id: string;
  kind: "correction" | "hint";
  original?: string;
  corrected?: string;
  note: string;
};

export function isTutorTurnMeta(meta: unknown): meta is TutorTurnMeta;
export function collectFeedbackItems(messages: TutorMessage[]): TutorFeedbackItem[];
```

- [x] **Step 1: Implement helper**

```ts
import type { TutorMessage, TutorTurnMeta } from "@/lib/tutor";

export type TutorFeedbackItem = {
  id: string;
  kind: "correction" | "hint";
  original?: string;
  corrected?: string;
  note: string;
};

export function isTutorTurnMeta(meta: unknown): meta is TutorTurnMeta {
  return (
    meta != null &&
    typeof meta === "object" &&
    "goal_progress" in meta
  );
}

export function collectFeedbackItems(
  messages: TutorMessage[],
): TutorFeedbackItem[] {
  const items: TutorFeedbackItem[] = [];
  for (const message of messages) {
    if (message.role !== "assistant") continue;
    if (!isTutorTurnMeta(message.meta)) continue;
    const meta = message.meta;
    if (meta.correction) {
      items.push({
        id: `c-${message.id}`,
        kind: "correction",
        original: meta.correction.original,
        corrected: meta.correction.better,
        note: meta.correction.why ?? "",
      });
    }
    if (meta.hint?.trim()) {
      items.push({
        id: `h-${message.id}`,
        kind: "hint",
        note: meta.hint.trim(),
      });
    }
  }
  return items;
}
```

- [x] **Step 2: Quick node assert (no runner required)**

```bash
cd frontend/my-app && npx --yes tsx -e "
const { collectFeedbackItems } = require('./lib/tutor-feedback.ts');
"
```

If TS require fails, use a tiny vitest addition only when `package.json` already has `vitest`/`jest`. Else mark verified by reading the function and Task 4 manual check.

---

### Task 3: FE types for nested scenario + strip debug usage on page

**Files:**
- Modify: `frontend/my-app/lib/tutor.ts`
- Modify: `frontend/my-app/src/app/ai-tutor/[sessionId]/page.tsx` (debug removal starts here; full layout in Task 4)

**Interfaces:**
- Produces: `TutorSession.scenario?: TutorScenario | null`

- [x] **Step 1: Update types**

```ts
export type TutorSession = {
  // ...existing fields
  scenario?: TutorScenario | null;
};
```

Keep `TutorDebugInfo` / `onDebug` in `lib/tutor.ts` for API compatibility; session page simply never enables debug.

- [x] **Step 2: On session page, delete**
  - `debugEnabled` / `debugInfo` state
  - Debug checkbox UI
  - Debug panel JSX
  - `onDebug` handler and `{ debug: debugEnabled }` → call `streamTutorMessage(..., { signal })` only (default false)

---

### Task 4: 3-column chat layout

**Files:**
- Create: `frontend/my-app/components/tutor/TutorScenarioRail.tsx`
- Create: `frontend/my-app/components/tutor/TutorFeedbackRail.tsx`
- Modify: `frontend/my-app/src/app/ai-tutor/[sessionId]/page.tsx`

**Interfaces:**
- Consumes: `session.scenario`, `messages`, `collectFeedbackItems`
- Produces: presentational rails; page owns SSE/state

- [x] **Step 1: Scenario rail**

Props: `scenario: TutorScenario`, optional `status: string`.

Render: label “Scenario”, title, category/level badges, Your role / AI partner / Goal, suggested vocab chips. Hide below `lg` (`hidden lg:block w-72`).

- [x] **Step 2: Feedback rail**

Props: `items: TutorFeedbackItem[]`, `open: boolean`, `onOpenChange: (v: boolean) => void`.

- Open by default when `items.length > 0` on desktop (parent state).
- List corrections (strikethrough original, better, note) and hints.
- Empty: “Corrections and hints from this session will show up here.”
- Collapsed: floating “Show feedback” control.

- [x] **Step 3: Page shell**

Structure (keep `AppHeader`):

```
<div className="flex min-h-screen flex-col">
  <AppHeader />
  <div className="flex min-h-0 flex-1 flex-col">
    <!-- top: level badge, title, elapsed optional, End session -->
    <div className="flex flex-1 min-h-0">
      <TutorScenarioRail />
      <section><!-- messages + composer --></section>
      <TutorFeedbackRail />
    </div>
  </div>
  {summary && <SummaryModal />}
</div>
```

- Message bubbles: keep streaming; move correction chip **out of bubble** into feedback rail (bubble = text only; optional tiny “corrected” affordance optional — prefer clean bubbles per mock).
- Composer: Input or textarea + Send; Hint button shows latest `hint` from last feedback item of kind hint (or disabled tooltip “No hint yet”).
- Timer: optional `Date.now() - started_at` mm:ss; nice-to-have, skip if timeboxed.
- Elapsed / status copy: “Session in progress” vs completed.

- [x] **Step 4: Manual verify**

1. Start topic from `/ai-tutor` → session loads with left rail filled from `scenario`.
2. Send messages → persist reload shows history.
3. When AI returns correction → right rail lists it; no Debug UI.
4. Roadmap “Practice speaking” → same page layout.
5. End session → summary modal → back to topics.

---

### Task 5: Spec status + optional docs touch

**Files:**
- Modify: `docs/superpowers/specs/2026-08-04-ai-tutor-chat-layout-design.md` — set Status to Implemented when done
- Optionally one line in RAG design noting Debug UI removed from roleplay chat (not required)

- [x] **Step 1: Flip status checklist in layout spec to done**

---

## Spec coverage check

| Spec item | Task |
|-----------|------|
| 3-column layout | 4 |
| Same portal catalog/roadmap | 4 (unchanged routes) |
| Persist DB | existing + unchanged |
| Feedback from meta | 2, 4 |
| Remove Debug RAG UI | 3, 4 |
| End summary modal | 4 (keep) |
| Scenario data on session | 1, 3 |

## Placeholder scan

None intentional. Timer is optional nice-to-have, not blocking.

---

## Execution handoff

Plan saved to `docs/superpowers/plans/2026-08-04-ai-tutor-chat-layout.md`.

**Two execution options:**

1. **Subagent-Driven (recommended)** — fresh subagent per task, review between tasks  
2. **Inline Execution** — implement in this session with checkpoints  

Which approach?
