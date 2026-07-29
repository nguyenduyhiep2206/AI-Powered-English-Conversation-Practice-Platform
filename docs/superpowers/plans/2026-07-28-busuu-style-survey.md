# Busuu-style Survey Onboarding (Option C) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the 4-question one-page survey with a Busuu-style wizard (why + daily time + level fork) so beginners/self-selected CEFR can skip placement while placement remains available; keep `occupation`/`weak_point` columns unused by the new survey.

**Architecture:** Alembic updates `GoalEnum` + survey question seed. `submit_survey` accepts `level_resolution` and sets `current_level`/`placement_score` when skipping the test. FE `/onboarding` becomes a multi-step card wizard; redirect uses `next_step` from submit response.

**Tech Stack:** FastAPI, SQLAlchemy async, Alembic, Pydantic, pytest, Next.js (App Router), existing `authFetch`.

**Spec:** `docs/superpowers/specs/2026-07-28-busuu-style-survey-design.md`

## Global Constraints

- Do **not** drop `user_profiles.occupation` or `user_profiles.weak_point`.
- Do **not** remove placement `preferred_skill_types` / roadmap weak_point boost (they no-op when null).
- Active survey maps only to `goal` and `daily_time_min`.
- `onboarding_complete` remains `survey_done and placement_score is not None`.
- Self-skip paths must set `placement_score` (beginner=`1`, self_selected=`5`).
- Service style: short orchestrator + named helpers (`service-orchestrator`).
- FE: one primary question per screen; preserve existing EnglishFlow visual language (no Busuu green/blue copycat theme required).

---

## File map

| File | Role |
|------|------|
| `docs/superpowers/specs/2026-07-28-busuu-style-survey-design.md` | Locked decisions (already written) |
| `backend/app/models/enums.py` | Add GoalEnum members |
| `backend/alembic/versions/l2m3n4o5p6q7_busuu_style_survey.py` | Enum values + deactivate/update survey rows |
| `backend/app/services/roadmap_assembler_service.py` | Extend `GOAL_TO_CATEGORY` |
| `backend/app/schemas/survey_schema.py` | `LevelResolution`, extend submit request/response |
| `backend/app/services/survey_service.py` | Apply level_resolution; return next_step |
| `backend/app/api/onboarding.py` | Wire new payload/response |
| `backend/tests/test_survey_service.py` | Unit tests for submit + level paths |
| `frontend/my-app/lib/survey.ts` | Types + submit with level_resolution |
| `frontend/my-app/src/app/onboarding/page.tsx` | Wizard UI |
| `frontend/my-app/src/app/start-onboarding/page.tsx` | Copy: survey may skip placement |
| `frontend/my-app/src/app/onboarding/placement/page.tsx` | No gate change beyond existing `survey_done` |

---

### Task 1: GoalEnum + GOAL_TO_CATEGORY + Alembic survey seed

**Files:**
- Modify: `backend/app/models/enums.py`
- Modify: `backend/app/services/roadmap_assembler_service.py` (`GOAL_TO_CATEGORY`)
- Create: `backend/alembic/versions/l2m3n4o5p6q7_busuu_style_survey.py`
- Test: `backend/tests/test_goal_to_category_busuu.py`

**Interfaces:**
- Produces: `GoalEnum.work|school|culture|family|challenge|other` (+ keep existing)
- Produces: updated `GOAL_TO_CATEGORY` keys for new goals
- Produces: migration that deactivates occupation/weak_point questions and rewrites goal/daily_time rows

- [ ] **Step 1: Write failing test for category map**

Create `backend/tests/test_goal_to_category_busuu.py`:

```python
from app.models.enums import GoalEnum, ScenarioCategoryEnum
from app.services.roadmap_assembler_service import GOAL_TO_CATEGORY


def test_busuu_goals_map_to_scenario_categories():
    assert GOAL_TO_CATEGORY[GoalEnum.work] == ScenarioCategoryEnum.job_interview
    assert GOAL_TO_CATEGORY[GoalEnum.school] == ScenarioCategoryEnum.custom
    assert GOAL_TO_CATEGORY[GoalEnum.travel] == ScenarioCategoryEnum.travel
    assert GOAL_TO_CATEGORY[GoalEnum.culture] == ScenarioCategoryEnum.small_talk
    assert GOAL_TO_CATEGORY[GoalEnum.family] == ScenarioCategoryEnum.small_talk
    assert GOAL_TO_CATEGORY[GoalEnum.challenge] == ScenarioCategoryEnum.small_talk
    assert GOAL_TO_CATEGORY[GoalEnum.other] == ScenarioCategoryEnum.small_talk
```

- [ ] **Step 2: Run test — expect fail**

Run: `cd backend && python -m pytest tests/test_goal_to_category_busuu.py -v`  
Expected: FAIL (`GoalEnum` missing new members and/or map keys)

- [ ] **Step 3: Extend GoalEnum**

In `backend/app/models/enums.py`, keep existing members and add:

```python
class GoalEnum(str, enum.Enum):
    job_interview = "job_interview"
    daily_conversation = "daily_conversation"
    travel = "travel"
    ielts = "ielts"
    business = "business"
    work = "work"
    school = "school"
    culture = "culture"
    family = "family"
    challenge = "challenge"
    other = "other"
```

- [ ] **Step 4: Extend GOAL_TO_CATEGORY**

In `roadmap_assembler_service.py`:

```python
GOAL_TO_CATEGORY: dict[GoalEnum, ScenarioCategoryEnum] = {
    GoalEnum.job_interview: ScenarioCategoryEnum.job_interview,
    GoalEnum.daily_conversation: ScenarioCategoryEnum.small_talk,
    GoalEnum.travel: ScenarioCategoryEnum.travel,
    GoalEnum.ielts: ScenarioCategoryEnum.custom,
    GoalEnum.business: ScenarioCategoryEnum.job_interview,
    GoalEnum.work: ScenarioCategoryEnum.job_interview,
    GoalEnum.school: ScenarioCategoryEnum.custom,
    GoalEnum.culture: ScenarioCategoryEnum.small_talk,
    GoalEnum.family: ScenarioCategoryEnum.small_talk,
    GoalEnum.challenge: ScenarioCategoryEnum.small_talk,
    GoalEnum.other: ScenarioCategoryEnum.small_talk,
}
```

- [ ] **Step 5: Re-run test — expect pass**

Run: `cd backend && python -m pytest tests/test_goal_to_category_busuu.py -v`  
Expected: PASS

- [ ] **Step 6: Alembic migration**

Create `backend/alembic/versions/l2m3n4o5p6q7_busuu_style_survey.py` with:

- `revision = "l2m3n4o5p6q7"`
- `down_revision = "k1l2m3n4o5p6"`
- `upgrade`:
  1. `ALTER TYPE goal_enum ADD VALUE IF NOT EXISTS 'work'` (and school, culture, family, challenge, other) — use `op.execute` with `IF NOT EXISTS` if PG version supports it, otherwise catch duplicate.
  2. SQL: set `is_active=false` where `maps_to_profile_field in ('occupation','weak_point')`.
  3. Update goal question (where `maps_to_profile_field='goal'` and active): prompt `Why are you learning English?`, options JSON:

```python
[
    {"value": "work", "label": "Work"},
    {"value": "school", "label": "School"},
    {"value": "travel", "label": "Travel"},
    {"value": "culture", "label": "Culture"},
    {"value": "family", "label": "Family & community"},
    {"value": "challenge", "label": "Challenge myself"},
    {"value": "other", "label": "Other"},
]
```

  4. Update daily_time question: prompt `Set a daily study goal`, options:

```python
[
    {"value": "5", "label": "5 minutes / day — Casual"},
    {"value": "10", "label": "10 minutes / day — Regular"},
    {"value": "15", "label": "15 minutes / day — Serious"},
    {"value": "25", "label": "25 minutes / day — Intense"},
]
```

- `downgrade`: re-activate old questions if identifiable; do **not** remove enum values (Postgres cannot easily drop enum values).

- [ ] **Step 7: Commit**

```bash
git add backend/app/models/enums.py \
  backend/app/services/roadmap_assembler_service.py \
  backend/alembic/versions/l2m3n4o5p6q7_busuu_style_survey.py \
  backend/tests/test_goal_to_category_busuu.py \
  docs/superpowers/specs/2026-07-28-busuu-style-survey-design.md
git commit -m "$(cat <<'EOF'
feat(survey): add Busuu-style goals and seed questions

Extend GoalEnum/scenario map and deactivate occupation/weak_point survey rows.
EOF
)"
```

---

### Task 2: Submit survey with level_resolution

**Files:**
- Modify: `backend/app/schemas/survey_schema.py`
- Modify: `backend/app/services/survey_service.py`
- Modify: `backend/app/api/onboarding.py`
- Create: `backend/tests/test_survey_service.py`

**Interfaces:**
- Consumes: Task 1 GoalEnum values; existing `_apply_answers_to_profile`
- Produces: `submit_survey(...) -> dict` with `next_step: Literal["placement","completed"]`
- Produces: `SubmitSurveyRequest.level_resolution`, `SubmitSurveyData.next_step`

- [ ] **Step 1: Write failing tests**

Create `backend/tests/test_survey_service.py` focusing on pure helpers first:

```python
import pytest
from app.models.enums import CEFRLevel
from app.services.survey_service import (
    resolve_level_for_survey,
    LevelResolutionError,
)


def test_beginner_sets_a1_and_score_1():
    level, score, next_step = resolve_level_for_survey(
        {"mode": "beginner"}
    )
    assert level == CEFRLevel.A1
    assert score == 1
    assert next_step == "completed"


def test_self_selected_requires_cefr_and_sets_score_5():
    level, score, next_step = resolve_level_for_survey(
        {"mode": "self_selected", "cefr_level": "B1"}
    )
    assert level == CEFRLevel.B1
    assert score == 5
    assert next_step == "completed"


def test_self_selected_missing_cefr_raises():
    with pytest.raises(LevelResolutionError):
        resolve_level_for_survey({"mode": "self_selected"})


def test_placement_mode_leaves_score_unset():
    level, score, next_step = resolve_level_for_survey(
        {"mode": "placement"}
    )
    assert level is None
    assert score is None
    assert next_step == "placement"
```

- [ ] **Step 2: Run tests — expect fail**

Run: `cd backend && python -m pytest tests/test_survey_service.py -v`  
Expected: FAIL (import / missing symbols)

- [ ] **Step 3: Schema**

In `survey_schema.py`:

```python
from typing import Any, Literal, Optional
from pydantic import BaseModel, Field, model_validator
from app.models.enums import CEFRLevel, SurveyQuestionTypeEnum


class LevelResolution(BaseModel):
    mode: Literal["beginner", "self_selected", "placement"]
    cefr_level: Optional[CEFRLevel] = None

    @model_validator(mode="after")
    def _require_cefr_when_self(self):
        if self.mode == "self_selected" and self.cefr_level is None:
            raise ValueError("cefr_level is required when mode is self_selected")
        return self


class SubmitSurveyRequest(BaseModel):
    answers: list[SurveyAnswerItem]
    level_resolution: LevelResolution


class SubmitSurveyData(BaseModel):
    survey_done: bool = True
    next_step: Literal["placement", "completed"]
    message: str = "Survey submitted successfully"
```

- [ ] **Step 4: Implement resolve + wire submit**

In `survey_service.py` add:

```python
class LevelResolutionError(ValueError):
    pass


def resolve_level_for_survey(
    raw: dict,
) -> tuple[CEFRLevel | None, int | None, Literal["placement", "completed"]]:
    mode = raw.get("mode")
    if mode == "beginner":
        return CEFRLevel.A1, 1, "completed"
    if mode == "self_selected":
        cefr = raw.get("cefr_level")
        if cefr is None:
            raise LevelResolutionError("cefr_level is required when mode is self_selected")
        level = cefr if isinstance(cefr, CEFRLevel) else CEFRLevel(str(cefr))
        return level, 5, "completed"
    if mode == "placement":
        return None, None, "placement"
    raise LevelResolutionError(f"Unknown level mode: {mode}")
```

Update `submit_survey` signature:

```python
async def submit_survey(
    db: AsyncSession,
    user_id: int,
    answers: list[SurveyAnswerItem],
    level_resolution: LevelResolution,
) -> dict:
    profile = await _get_user_profile(db, user_id)
    _require_survey_not_done(profile)

    active_questions = await _require_active_question_map(db)
    answers_by_question = {item.question_id: item for item in answers}
    _require_required_answers(active_questions, answers_by_question)

    profile = _ensure_profile(db, user_id, profile)
    _apply_answers_to_profile(profile, active_questions, answers_by_question)

    level, score, next_step = resolve_level_for_survey(
        level_resolution.model_dump()
    )
    if level is not None:
        profile.current_level = level
    if score is not None:
        profile.placement_score = score

    profile.survey_done = True
    await db.commit()
    return {"survey_done": True, "next_step": next_step}
```

Import `CEFRLevel` and `LevelResolution` as needed. Map `LevelResolutionError` to HTTP 400 in the API layer.

- [ ] **Step 5: API**

In `onboarding.py`:

```python
result = await submit_survey(
    db,
    int(current_user.id),
    payload.answers,
    payload.level_resolution,
)
return SubmitSurveyResponse(
    data=SubmitSurveyData(next_step=result["next_step"])
)
```

Catch `LevelResolutionError` / Pydantic validation → 400.

- [ ] **Step 6: Run tests — expect pass**

Run: `cd backend && python -m pytest tests/test_survey_service.py -v`  
Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add backend/app/schemas/survey_schema.py \
  backend/app/services/survey_service.py \
  backend/app/api/onboarding.py \
  backend/tests/test_survey_service.py
git commit -m "$(cat <<'EOF'
feat(survey): support level_resolution on survey submit

Allow beginner/self-selected CEFR to complete onboarding without placement.
EOF
)"
```

---

### Task 3: Frontend survey client + wizard

**Files:**
- Modify: `frontend/my-app/lib/survey.ts`
- Modify: `frontend/my-app/src/app/onboarding/page.tsx`
- Modify: `frontend/my-app/src/app/start-onboarding/page.tsx`

**Interfaces:**
- Consumes: `GET /survey/questions` (only goal + daily_time active after migration)
- Consumes: `POST /survey` with `{ answers, level_resolution }` → `{ next_step }`
- Produces: wizard that never sends occupation/weak_point answers

- [ ] **Step 1: Update `lib/survey.ts`**

```typescript
export type LevelResolution =
  | { mode: "beginner" }
  | { mode: "self_selected"; cefr_level: "A1" | "A2" | "B1" | "B2" | "C1" }
  | { mode: "placement" };

export type SubmitSurveyResult = {
  survey_done: boolean;
  next_step: "placement" | "completed";
};

export async function submitSurvey(
  answers: SurveyAnswerPayload[],
  level_resolution: LevelResolution,
): Promise<SubmitSurveyResult> {
  const res = await authFetch("/api/v1/onboarding/survey", {
    method: "POST",
    body: JSON.stringify({ answers, level_resolution }),
  });
  if (!res.ok) {
    const error = await res.json().catch(() => ({}));
    const detail = (error as { detail?: string }).detail;
    throw new Error(detail || "Failed to submit survey");
  }
  const body = (await res.json()) as {
    data: SubmitSurveyResult;
  };
  return body.data;
}
```

- [ ] **Step 2: Rewrite onboarding page as wizard**

Replace `frontend/my-app/src/app/onboarding/page.tsx` with a client wizard:

**Wizard steps (local state, not routes):**

1. `why` — active goal question from API.
2. `time` — daily time question.
3. `know_english` — local-only UI: cards `beginner` | `know_some`.
4. If `beginner` → submit `{ mode: "beginner" }`.
5. If `know_some` → `level_fork`: `self_selected` | `placement`.
6. If `self_selected` → `pick_cefr` (A1…C1) then submit `{ mode: "self_selected", cefr_level }`.
7. If `placement` → submit `{ mode: "placement" }`.

**Submit answers:** only the two API questions as `SurveyAnswerPayload[]`.

**After submit:**

```typescript
const result = await submitSurvey(payload, levelResolution);
if (result.next_step === "placement") {
  router.replace("/onboarding/placement");
} else {
  try {
    await assembleRoadmap();
  } catch {
    // non-blocking; dashboard can assemble later
  }
  router.replace("/dashboard");
}
```

Import `assembleRoadmap` from `@/lib/roadmap` (same as placement page).

**UI details:**
- Progress bar = `currentStepIndex / totalSteps` (account for skipped branches).
- Card selection with selected border (reuse existing selected styles).
- Keep header + LogoutButton patterns from current page.

Identify questions after fetch:

```typescript
function splitQuestions(questions: SurveyQuestion[]) {
  const why = questions.find((q) =>
    (q.options ?? []).some((o) => o.value === "work" || o.value === "travel"),
  );
  const time = questions.find((q) =>
    (q.options ?? []).some((o) => o.value === "10" || o.value === "25"),
  );
  if (!why || !time) {
    throw new Error("Survey is not configured for Busuu-style onboarding");
  }
  return { why, time };
}
```

- [ ] **Step 3: Update start-onboarding copy**

In `start-onboarding/page.tsx`:

- Survey desc: `Why you learn, daily study time, and how we place your level`
- Hero: `A short setup — then lessons at the right level (placement only if you need it).`

- [ ] **Step 4: Manual smoke checklist**

1. Apply migration; ensure only 2 active survey questions.
2. New user → beginner → dashboard with `current_level=A1`.
3. New user → self-select B1 → dashboard, `placement_score=5`.
4. New user → find level → `/onboarding/placement` still works.
5. `GET /survey/questions` returns length 2.

- [ ] **Step 5: Commit**

```bash
git add frontend/my-app/lib/survey.ts \
  frontend/my-app/src/app/onboarding/page.tsx \
  frontend/my-app/src/app/start-onboarding/page.tsx
git commit -m "$(cat <<'EOF'
feat(onboarding): Busuu-style survey wizard with level fork

Collect why + daily time, then beginner/self-select/placement paths.
EOF
)"
```

---

### Task 4: Placement page + status copy consistency

**Files:**
- Modify: `frontend/my-app/src/app/onboarding/placement/page.tsx` (copy only if needed)
- Modify: `frontend/my-app/src/app/start-onboarding/page.tsx` steps list
- Verify: `backend/app/services/onboarding_service.py` — no code change if `placement_score` semantics hold

**Interfaces:**
- Consumes: existing `survey_done` gate on placement page
- Produces: consistent UX when user opens placement only via `next_step=placement`

- [ ] **Step 1: Adjust start-onboarding steps array**

Describe placement as optional: `Adaptive test if you need help finding your CEFR level`.

- [ ] **Step 2: Placement page entry**

Keep gate `!survey_done → /onboarding`. Optionally add subtitle: `Based on your survey, we’ll find your CEFR level.`

- [ ] **Step 3: Backend status sanity**

Confirm:

- beginner path → `onboarding_complete=True`, `current_step=completed`
- placement path mid-flow → `survey_done=True`, `placement_done=False`, `current_step=placement`

- [ ] **Step 4: Commit**

```bash
git add frontend/my-app/src/app/start-onboarding/page.tsx \
  frontend/my-app/src/app/onboarding/placement/page.tsx
git commit -m "$(cat <<'EOF'
docs(ui): clarify optional placement after Busuu-style survey
EOF
)"
```

---

### Task 5: Verification + spec status

**Files:**
- Modify: `docs/superpowers/specs/2026-07-28-busuu-style-survey-design.md` (Status → Implemented)

- [ ] **Step 1: Run backend regression**

```bash
cd backend && python -m pytest tests/test_survey_service.py tests/test_goal_to_category_busuu.py tests/test_placement_session_helpers.py tests/test_placement_adaptive_engine.py -v
```

Expected: PASS

- [ ] **Step 2: Run migration on local DB**

```bash
cd backend && alembic upgrade head
```

Expected: head = `l2m3n4o5p6q7`

- [ ] **Step 3: Mark spec Implemented**

Set `Status: Implemented` in the design spec.

- [ ] **Step 4: Final commit if needed**

```bash
git add docs/superpowers/specs/2026-07-28-busuu-style-survey-design.md
git commit -m "$(cat <<'EOF'
docs: mark Busuu-style survey design implemented
EOF
)"
```

---

## Self-review

| Spec requirement | Task |
|---|---|
| Why + daily time only in active survey | Task 1 migration |
| Keep occupation/weak_point columns | Global constraint; no drop migration |
| Busuu why labels / GoalEnum map | Task 1 |
| Level fork beginner/self/placement | Task 2 + 3 |
| Skip placement sets placement_score | Task 2 |
| Wizard UX | Task 3 |
| Optional placement copy | Task 4 |
| No placement engine rewrite | Out of scope |

No TBD placeholders. `next_step` / `LevelResolution` names consistent across tasks.
