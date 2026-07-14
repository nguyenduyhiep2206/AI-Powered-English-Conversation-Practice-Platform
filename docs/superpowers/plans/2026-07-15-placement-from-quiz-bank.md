# Placement Test from Quiz Bank Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** After survey, learners take a 10-question placement test drawn from `quiz_questions` with `status=published`, map score→CEFR, seed mastery, and finish onboarding — without auto-assembling a roadmap; admins can publish drafts from Admin Books.

**Architecture:** Pure helpers in `placement_service` (score map + pick 2/level with skill diversity) are unit-tested without DB. Async methods load published rows joined to `learning_skills`, then update `user_profiles` and call existing `apply_answer`. Onboarding routes expose Functional Spec paths. Admin FE extends Task 10 `BookQuizPanel` with publish; learner FE adds `/onboarding/placement`.

**Tech Stack:** FastAPI, SQLAlchemy async, pytest, Pydantic, Next.js (`authFetch`), existing `mastery_service.grade_mcq` / `apply_answer`.

**Spec:** `docs/superpowers/specs/2026-07-15-placement-from-quiz-bank-design.md`

---

## File map

| File | Role |
|------|------|
| `backend/app/services/placement_service.py` | `score_to_level`, `select_from_candidates`, `load_published_candidates`, `get_placement_questions`, `submit_placement` |
| `backend/tests/test_placement_service.py` | Unit tests for map + selector (+ gates with lightweight fakes if needed) |
| `backend/app/schemas/onboarding_schema.py` | Placement question/answer/result models |
| `backend/app/api/onboarding.py` | `GET /questions`, `POST /placement` |
| `frontend/my-app/lib/admin-quiz.ts` | `listBookQuestions`, `publishQuestions` (+ existing sync/generate) |
| `frontend/my-app/components/admin/BookQuizPanel.tsx` | Draft list + Publish selected |
| `frontend/my-app/lib/placement.ts` | Client for GET questions / POST placement |
| `frontend/my-app/src/app/onboarding/placement/page.tsx` | Placement UI + result |
| `frontend/my-app/src/app/onboarding/page.tsx` | Redirect after survey → `/onboarding/placement` |
| `frontend/my-app/src/app/start-onboarding/page.tsx` | Continue CTA → placement when `current_step === "placement"` |

**Prerequisite (uncommitted Task 10):** If `BookQuizPanel` / `admin-quiz.ts` / books `page.tsx` wire are still untracked, commit or land them **before or as part of Task 4** so Publish UI has a home. Do not invent a second quiz panel.

**No new Alembic migration** — reuse `user_profiles.placement_score`, `current_level`, `quiz_questions.status`.

---

### Task 1: Score map + candidate picker (pure, TDD)

**Files:**
- Create: `backend/tests/test_placement_service.py`
- Create: `backend/app/services/placement_service.py`

- [ ] **Step 1: Write failing tests**

```python
# backend/tests/test_placement_service.py
from app.models.enums import CEFRLevel
from app.services.placement_service import (
    PlacementCandidate,
    score_to_level,
    select_from_candidates,
    PLACEMENT_SIZE,
)


def test_score_to_level_bang_spec():
    assert score_to_level(0) == CEFRLevel.A1
    assert score_to_level(3) == CEFRLevel.A1
    assert score_to_level(4) == CEFRLevel.A2
    assert score_to_level(5) == CEFRLevel.A2
    assert score_to_level(6) == CEFRLevel.B1
    assert score_to_level(7) == CEFRLevel.B1
    assert score_to_level(8) == CEFRLevel.B2
    assert score_to_level(9) == CEFRLevel.B2
    assert score_to_level(10) == CEFRLevel.C1


def test_select_from_candidates_hai_cau_moi_level():
    from collections import Counter

    cands: list[PlacementCandidate] = []
    n = 0
    for lvl in CEFRLevel:
        for i in range(3):
            n += 1
            cands.append(
                PlacementCandidate(
                    id=n,
                    skill_id=1000 + n,
                    cefr_level=lvl,
                    question_type="mcq",
                    stem=f"{lvl.value}-{i}",
                    options=["a", "b", "c", "d"],
                    difficulty="medium",
                    answer="a",
                )
            )
    picked = select_from_candidates(cands, rng_seed=42)
    assert len(picked) == PLACEMENT_SIZE
    counts = Counter(p.cefr_level for p in picked)
    assert all(counts[lvl] == 2 for lvl in CEFRLevel)


def test_select_thieu_level_raise():
    cands = [
        PlacementCandidate(
            id=i,
            skill_id=1,
            cefr_level=CEFRLevel.B1,
            question_type="mcq",
            stem="x",
            options=["a", "b", "c", "d"],
            difficulty="medium",
            answer="a",
        )
        for i in range(10)
    ]
    try:
        select_from_candidates(cands, rng_seed=1)
        assert False, "expected ValueError"
    except ValueError as exc:
        assert "placement" in str(exc).lower() or "published" in str(exc).lower()


def test_uu_tien_mcq_va_tranh_trung_skill_trong_level():
    cands = [
        PlacementCandidate(1, 10, CEFRLevel.A1, "mcq", "a1", ["a", "b", "c", "d"], "medium", "a"),
        PlacementCandidate(2, 11, CEFRLevel.A1, "mcq", "a2", ["a", "b", "c", "d"], "medium", "a"),
        PlacementCandidate(3, 12, CEFRLevel.A1, "cloze", "a3", None, "medium", "x"),
        PlacementCandidate(4, 20, CEFRLevel.A2, "mcq", "s", ["a", "b", "c", "d"], "medium", "a"),
        PlacementCandidate(5, 21, CEFRLevel.A2, "mcq", "t", ["a", "b", "c", "d"], "medium", "a"),
        PlacementCandidate(6, 20, CEFRLevel.B1, "mcq", "s", ["a", "b", "c", "d"], "medium", "a"),
        PlacementCandidate(7, 21, CEFRLevel.B1, "mcq", "t", ["a", "b", "c", "d"], "medium", "a"),
        PlacementCandidate(8, 20, CEFRLevel.B2, "mcq", "s", ["a", "b", "c", "d"], "medium", "a"),
        PlacementCandidate(9, 21, CEFRLevel.B2, "mcq", "t", ["a", "b", "c", "d"], "medium", "a"),
        PlacementCandidate(10, 20, CEFRLevel.C1, "mcq", "s", ["a", "b", "c", "d"], "medium", "a"),
        PlacementCandidate(11, 21, CEFRLevel.C1, "mcq", "t", ["a", "b", "c", "d"], "medium", "a"),
    ]
    picked = select_from_candidates(cands, rng_seed=7)
    a1 = [p for p in picked if p.cefr_level == CEFRLevel.A1]
    assert len(a1) == 2
    assert all(p.question_type == "mcq" for p in a1)
    assert len({p.skill_id for p in a1}) == 2
```

- [ ] **Step 2: Run tests — expect FAIL**

```bash
cd backend && python -m pytest tests/test_placement_service.py -v
```

Expected: `ModuleNotFoundError` or `ImportError` for `placement_service`.

- [ ] **Step 3: Minimal implementation**

```python
# backend/app/services/placement_service.py
"""Placement test: sample published quiz bank → score → CEFR; seed mastery. No roadmap assemble."""

from __future__ import annotations

import random
from collections import defaultdict
from dataclasses import dataclass
from typing import Any, Sequence

from app.models.enums import CEFRLevel

PLACEMENT_SIZE = 10
PER_LEVEL = 2
CEFR_ORDER: tuple[CEFRLevel, ...] = (
    CEFRLevel.A1,
    CEFRLevel.A2,
    CEFRLevel.B1,
    CEFRLevel.B2,
    CEFRLevel.C1,
)
INSUFFICIENT_BANK_MSG = (
    "Chưa đủ câu hỏi published cho placement (cần 10 câu trải A1–C1)."
)


@dataclass(frozen=True)
class PlacementCandidate:
    id: int
    skill_id: int
    cefr_level: CEFRLevel
    question_type: str
    stem: str
    options: list[str] | None
    difficulty: str
    answer: str


def score_to_level(score: int) -> CEFRLevel:
    if score <= 3:
        return CEFRLevel.A1
    if score <= 5:
        return CEFRLevel.A2
    if score <= 7:
        return CEFRLevel.B1
    if score <= 9:
        return CEFRLevel.B2
    return CEFRLevel.C1


def _type_rank(question_type: str) -> int:
    # lower = better
    if question_type == "mcq":
        return 0
    if question_type == "cloze":
        return 1
    return 2


def select_from_candidates(
    candidates: Sequence[PlacementCandidate],
    *,
    rng_seed: int | None = None,
) -> list[PlacementCandidate]:
    rng = random.Random(rng_seed)
    by_level: dict[CEFRLevel, list[PlacementCandidate]] = defaultdict(list)
    for c in candidates:
        by_level[c.cefr_level].append(c)

    picked: list[PlacementCandidate] = []
    for level in CEFR_ORDER:
        pool = list(by_level.get(level, []))
        if len(pool) < PER_LEVEL:
            raise ValueError(INSUFFICIENT_BANK_MSG)
        pool.sort(key=lambda c: (_type_rank(c.question_type), c.id))
        rng.shuffle(pool)
        chosen: list[PlacementCandidate] = []
        used_skills: set[int] = set()
        # Prefer unique skill_id
        for c in pool:
            if len(chosen) >= PER_LEVEL:
                break
            if c.skill_id in used_skills:
                continue
            chosen.append(c)
            used_skills.add(c.skill_id)
        if len(chosen) < PER_LEVEL:
            for c in pool:
                if len(chosen) >= PER_LEVEL:
                    break
                if c in chosen:
                    continue
                chosen.append(c)
        if len(chosen) < PER_LEVEL:
            raise ValueError(INSUFFICIENT_BANK_MSG)
        picked.extend(chosen[:PER_LEVEL])

    if len(picked) != PLACEMENT_SIZE:
        raise ValueError(INSUFFICIENT_BANK_MSG)
    rng.shuffle(picked)
    return picked
```

- [ ] **Step 4: Run tests — expect PASS**

```bash
cd backend && python -m pytest tests/test_placement_service.py -v
```

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/placement_service.py backend/tests/test_placement_service.py
git commit -m "$(cat <<'EOF'
feat: add placement score map and published-bank picker

EOF
)"
```

---

### Task 2: Load published candidates + get/submit placement (DB)

**Files:**
- Modify: `backend/app/services/placement_service.py`
- Modify: `backend/tests/test_placement_service.py` (add pure grading helper tests only; keep DB optional)
- Modify: `backend/app/services/mastery_service.py` — **only if needed**: export/reuse `grade_mcq` as `grade_answer` alias (prefer importing `grade_mcq` for all types in placement to avoid new module)

- [ ] **Step 1: Add tests for public DTO helper + grading batch**

```python
# append to backend/tests/test_placement_service.py
from app.services.placement_service import grade_placement_answer, placement_public_dict


def test_grade_placement_answer_dung_grade_mcq():
    assert grade_placement_answer("Has gone", "has gone") is True
    assert grade_placement_answer("x", "y") is False


def test_placement_public_dict_khong_co_answer():
    c = PlacementCandidate(
        id=9,
        skill_id=1,
        cefr_level=CEFRLevel.B1,
        question_type="mcq",
        stem="Stem",
        options=["a", "b", "c", "d"],
        difficulty="easy",
        answer="SECRET",
    )
    d = placement_public_dict(c)
    assert "answer" not in d
    assert d["id"] == 9
    assert d["cefr_level"] == "B1"
```

- [ ] **Step 2: Run — expect FAIL** (`grade_placement_answer` missing)

```bash
cd backend && python -m pytest tests/test_placement_service.py::test_grade_placement_answer_dung_grade_mcq tests/test_placement_service.py::test_placement_public_dict_khong_co_answer -v
```

- [ ] **Step 3: Implement load + get + submit**

Append to `placement_service.py`:

```python
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.learning_skill import LearningSkillDB
from app.models.enums import QuizQuestionStatusEnum
from app.models.profile import UserProfileDB
from app.models.quiz_question import QuizQuestionDB
from app.services.mastery_service import apply_answer, grade_mcq


def grade_placement_answer(expected: str, given: str) -> bool:
    return grade_mcq(expected, given)


def placement_public_dict(c: PlacementCandidate) -> dict[str, Any]:
    return {
        "id": c.id,
        "skill_id": c.skill_id,
        "cefr_level": c.cefr_level.value if hasattr(c.cefr_level, "value") else str(c.cefr_level),
        "question_type": c.question_type,
        "stem": c.stem,
        "options": c.options,
        "difficulty": c.difficulty,
    }


async def load_published_candidates(db: AsyncSession) -> list[PlacementCandidate]:
    q = (
        select(QuizQuestionDB, LearningSkillDB)
        .join(LearningSkillDB, LearningSkillDB.id == QuizQuestionDB.skill_id)
        .where(
            QuizQuestionDB.status == QuizQuestionStatusEnum.published,
            LearningSkillDB.is_active.is_(True),
        )
    )
    rows = (await db.execute(q)).all()
    out: list[PlacementCandidate] = []
    for question, skill in rows:
        qtype = question.question_type
        qtype_s = qtype.value if hasattr(qtype, "value") else str(qtype)
        out.append(
            PlacementCandidate(
                id=int(question.id),
                skill_id=int(question.skill_id),
                cefr_level=skill.cefr_level,
                question_type=qtype_s,
                stem=question.stem,
                options=list(question.options) if question.options else None,
                difficulty=question.difficulty or "medium",
                answer=question.answer,
            )
        )
    return out


async def get_placement_questions_for_user(
    db: AsyncSession,
    user_id: int,
) -> list[PlacementCandidate]:
    profile = (
        await db.execute(select(UserProfileDB).where(UserProfileDB.user_id == user_id))
    ).scalar_one_or_none()
    if profile is None or not profile.survey_done:
        raise PermissionError("Hoàn thành survey trước khi làm placement")
    if profile.placement_score is not None:
        raise RuntimeError("Đã hoàn thành placement")

    candidates = await load_published_candidates(db)
    return select_from_candidates(candidates)


async def submit_placement(
    db: AsyncSession,
    user_id: int,
    answers: list[dict[str, Any]],
) -> dict[str, Any]:
    """answers: [{question_id, answer}, ...] — exactly PLACEMENT_SIZE published ids."""
    profile = (
        await db.execute(select(UserProfileDB).where(UserProfileDB.user_id == user_id))
    ).scalar_one_or_none()
    if profile is None or not profile.survey_done:
        raise PermissionError("Hoàn thành survey trước khi làm placement")
    if profile.placement_score is not None:
        raise RuntimeError("Đã hoàn thành placement")

    if len(answers) != PLACEMENT_SIZE:
        raise ValueError(f"Cần đúng {PLACEMENT_SIZE} câu trả lời")

    ids = [int(a["question_id"]) for a in answers]
    if len(set(ids)) != PLACEMENT_SIZE:
        raise ValueError("question_id trùng hoặc thiếu")

    q = (
        select(QuizQuestionDB)
        .where(
            QuizQuestionDB.id.in_(ids),
            QuizQuestionDB.status == QuizQuestionStatusEnum.published,
        )
    )
    rows = list((await db.execute(q)).scalars().all())
    by_id = {int(r.id): r for r in rows}
    if len(by_id) != PLACEMENT_SIZE:
        raise ValueError("Một số câu không tồn tại hoặc chưa published")

    correct_count = 0
    graded: list[tuple[QuizQuestionDB, bool]] = []
    answer_map = {int(a["question_id"]): str(a["answer"]) for a in answers}
    for qid in ids:
        row = by_id[qid]
        ok = grade_placement_answer(row.answer, answer_map[qid])
        if ok:
            correct_count += 1
        graded.append((row, ok))

    level = score_to_level(correct_count)
    profile.placement_score = correct_count
    profile.current_level = level
    await db.commit()

    for row, ok in graded:
        await apply_answer(db, user_id, int(row.skill_id), ok)

    return {
        "placement_score": correct_count,
        "current_level": level.value,
        "correct_count": correct_count,
        "total": PLACEMENT_SIZE,
        "onboarding_complete": True,
    }
```

Map exceptions in API layer: `PermissionError` → 400, `RuntimeError` → 409, `ValueError` with `INSUFFICIENT_BANK_MSG` → 503, other `ValueError` → 400.

- [ ] **Step 4: Run pure tests again**

```bash
cd backend && python -m pytest tests/test_placement_service.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/placement_service.py backend/tests/test_placement_service.py
git commit -m "$(cat <<'EOF'
feat: load published bank and submit placement profile + mastery

EOF
)"
```

---

### Task 3: Onboarding schemas + API routes

**Files:**
- Modify: `backend/app/schemas/onboarding_schema.py`
- Modify: `backend/app/api/onboarding.py`

- [ ] **Step 1: Extend schemas**

Append to `backend/app/schemas/onboarding_schema.py`:

```python
from pydantic import BaseModel, Field


class PlacementQuestionOut(BaseModel):
    id: int
    skill_id: int
    cefr_level: str
    question_type: str
    stem: str
    options: list[str] | None = None
    difficulty: str


class PlacementQuestionsData(BaseModel):
    question_count: int
    questions: list[PlacementQuestionOut]


class PlacementQuestionsResponse(BaseModel):
    success: bool = True
    data: PlacementQuestionsData


class PlacementAnswerIn(BaseModel):
    question_id: int
    answer: str


class PlacementSubmitRequest(BaseModel):
    answers: list[PlacementAnswerIn] = Field(min_length=10, max_length=10)


class PlacementResultData(BaseModel):
    placement_score: int
    current_level: str
    correct_count: int
    total: int
    onboarding_complete: bool


class PlacementSubmitResponse(BaseModel):
    success: bool = True
    data: PlacementResultData
```

- [ ] **Step 2: Wire routes in `onboarding.py`**

Add imports and endpoints (keep existing survey/status):

```python
from fastapi import APIRouter, Depends, HTTPException
from app.schemas.onboarding_schema import (
    OnboardingStatusResponse,
    PlacementQuestionsResponse,
    PlacementQuestionsData,
    PlacementQuestionOut,
    PlacementSubmitRequest,
    PlacementSubmitResponse,
    PlacementResultData,
)
from app.services.placement_service import (
    INSUFFICIENT_BANK_MSG,
    get_placement_questions_for_user,
    placement_public_dict,
    submit_placement,
)


@router.get("/questions", response_model=PlacementQuestionsResponse)
async def placement_questions(
    current_user: UserDB = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        picked = await get_placement_questions_for_user(db, int(current_user.id))
    except PermissionError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except ValueError as exc:
        status = 503 if str(exc) == INSUFFICIENT_BANK_MSG else 400
        raise HTTPException(status_code=status, detail=str(exc)) from exc

    questions = [PlacementQuestionOut(**placement_public_dict(c)) for c in picked]
    return PlacementQuestionsResponse(
        data=PlacementQuestionsData(question_count=len(questions), questions=questions)
    )


@router.post("/placement", response_model=PlacementSubmitResponse)
async def placement_submit(
    payload: PlacementSubmitRequest,
    current_user: UserDB = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        result = await submit_placement(
            db,
            int(current_user.id),
            [a.model_dump() for a in payload.answers],
        )
    except PermissionError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return PlacementSubmitResponse(data=PlacementResultData(**result))
```

**Path note:** Functional Spec lists `GET /api/v1/onboarding/questions` (not `/survey/questions`). Router already mounted at `/api/v1/onboarding` → these become `/questions` and `/placement`. Do **not** shadow survey routes.

- [ ] **Step 3: Smoke import**

```bash
cd backend && python -c "from app.api import onboarding; from app.services import placement_service; print('ok')"
```

- [ ] **Step 4: Commit**

```bash
git add backend/app/schemas/onboarding_schema.py backend/app/api/onboarding.py
git commit -m "$(cat <<'EOF'
feat: expose onboarding placement questions and submit APIs

EOF
)"
```

---

### Task 4: Admin publish client + BookQuizPanel UI

**Files:**
- Modify: `frontend/my-app/lib/admin-quiz.ts`
- Modify: `frontend/my-app/components/admin/BookQuizPanel.tsx`
- Ensure: `frontend/my-app/src/app/admin/books/page.tsx` already renders `BookQuizPanel` when `preview.status === "ready"` (Task 10)

- [ ] **Step 1: Extend `admin-quiz.ts`**

```typescript
export async function listBookQuestions(
  bookId: number,
  statusFilter?: "draft" | "published",
): Promise<QuizQuestionRow[]> {
  const q = statusFilter ? `?status_filter=${statusFilter}` : "";
  const res = await authFetch(`/api/v1/admin/quiz/books/${bookId}/questions${q}`);
  if (!res.ok) {
    const error = await res.json().catch(() => ({}));
    throw new Error(extractErrorMessage(error, "Failed to load questions"));
  }
  const body = (await res.json()) as { data: QuizQuestionRow[] };
  return body.data;
}

export async function publishQuestions(questionIds: number[]): Promise<number> {
  const res = await authFetch(`/api/v1/admin/quiz/questions/publish`, {
    method: "POST",
    body: JSON.stringify({ question_ids: questionIds }),
  });
  if (!res.ok) {
    const error = await res.json().catch(() => ({}));
    throw new Error(extractErrorMessage(error, "Failed to publish questions"));
  }
  const body = (await res.json()) as { data: { published: number } };
  return body.data.published;
}
```

- [ ] **Step 2: Publish section in `BookQuizPanel`**

After generate status message, add state + UI:

```tsx
// imports
import { listBookQuestions, publishQuestions, type QuizQuestionRow } from "@/lib/admin-quiz";

// state
const [drafts, setDrafts] = useState<QuizQuestionRow[]>([]);
const [selectedIds, setSelectedIds] = useState<Set<number>>(new Set());
const [loadingDrafts, setLoadingDrafts] = useState(false);
const [publishing, setPublishing] = useState(false);

async function refreshDrafts() {
  setLoadingDrafts(true);
  try {
    const rows = await listBookQuestions(bookId, "draft");
    setDrafts(rows);
    setSelectedIds(new Set());
  } catch (err) {
    onError(err instanceof Error ? err.message : "Failed to load drafts");
  } finally {
    setLoadingDrafts(false);
  }
}

// After successful generateSkillQuiz / syncBookSkills, call void refreshDrafts();
// Also call refreshDrafts once when panel mounts (useEffect on bookId).

async function handlePublish() {
  if (selectedIds.size === 0) return;
  setPublishing(true);
  onError(null);
  try {
    const n = await publishQuestions([...selectedIds]);
    setStatusMessage(`Published ${n} question(s).`);
    await refreshDrafts();
  } catch (err) {
    onError(err instanceof Error ? err.message : "Failed to publish");
  } finally {
    setPublishing(false);
  }
}
```

UI block (below generate table):

```tsx
<div className="mt-6 border-t border-border pt-4">
  <div className="mb-3 flex flex-wrap items-center gap-2">
    <h3 className="text-sm font-semibold">Draft questions</h3>
    <Button type="button" size="sm" variant="outline" disabled={loadingDrafts} onClick={refreshDrafts}>
      {loadingDrafts ? <Loader2 className="h-4 w-4 animate-spin" /> : "Refresh"}
    </Button>
    <Button
      type="button"
      size="sm"
      className="ml-auto"
      disabled={publishing || selectedIds.size === 0}
      onClick={handlePublish}
    >
      {publishing ? <Loader2 className="h-4 w-4 animate-spin" /> : `Publish selected (${selectedIds.size})`}
    </Button>
  </div>
  {drafts.length === 0 ? (
    <p className="text-sm text-muted-foreground">No drafts. Generate quiz for a skill first.</p>
  ) : (
    <ul className="max-h-64 space-y-2 overflow-y-auto text-sm">
      {drafts.map((q) => (
        <li key={q.id} className="flex items-start gap-2 rounded-md border border-border/70 px-3 py-2">
          <input
            type="checkbox"
            className="mt-1"
            checked={selectedIds.has(q.id)}
            onChange={(e) => {
              setSelectedIds((prev) => {
                const next = new Set(prev);
                if (e.target.checked) next.add(q.id);
                else next.delete(q.id);
                return next;
              });
            }}
          />
          <div>
            <p className="font-medium">#{q.id} · skill {q.skill_id} · {q.question_type}</p>
            <p className="text-muted-foreground line-clamp-2">{q.stem}</p>
          </div>
        </li>
      ))}
    </ul>
  )}
</div>
```

- [ ] **Step 3: Manual check**

With API up: open ready book preview → Sync → Generate → Drafts appear → Publish selected → `status_filter=published` has rows (Swagger or Network tab).

- [ ] **Step 4: Commit** (include any still-uncommitted Task 10 quiz panel files)

```bash
git add frontend/my-app/lib/admin-quiz.ts frontend/my-app/components/admin/BookQuizPanel.tsx frontend/my-app/src/app/admin/books/page.tsx
git commit -m "$(cat <<'EOF'
feat: admin UI to publish draft quiz questions for placement bank

EOF
)"
```

---

### Task 5: Learner placement client + page

**Files:**
- Create: `frontend/my-app/lib/placement.ts`
- Create: `frontend/my-app/src/app/onboarding/placement/page.tsx`
- Modify: `frontend/my-app/src/app/onboarding/page.tsx` (redirect after survey)
- Modify: `frontend/my-app/src/app/start-onboarding/page.tsx` (CTA href)

- [ ] **Step 1: Client `lib/placement.ts`**

```typescript
import { authFetch, extractErrorMessage } from "@/lib/api";

export type PlacementQuestion = {
  id: number;
  skill_id: number;
  cefr_level: string;
  question_type: string;
  stem: string;
  options?: string[] | null;
  difficulty: string;
};

export type PlacementResult = {
  placement_score: number;
  current_level: string;
  correct_count: number;
  total: number;
  onboarding_complete: boolean;
};

export async function fetchPlacementQuestions(): Promise<PlacementQuestion[]> {
  const res = await authFetch("/api/v1/onboarding/questions");
  if (!res.ok) {
    const error = await res.json().catch(() => ({}));
    throw new Error(extractErrorMessage(error, "Failed to load placement questions"));
  }
  const body = (await res.json()) as {
    data: { question_count: number; questions: PlacementQuestion[] };
  };
  return body.data.questions;
}

export async function submitPlacement(
  answers: { question_id: number; answer: string }[],
): Promise<PlacementResult> {
  const res = await authFetch("/api/v1/onboarding/placement", {
    method: "POST",
    body: JSON.stringify({ answers }),
  });
  if (!res.ok) {
    const error = await res.json().catch(() => ({}));
    throw new Error(extractErrorMessage(error, "Failed to submit placement"));
  }
  const body = (await res.json()) as { data: PlacementResult };
  return body.data;
}
```

- [ ] **Step 2: Page `onboarding/placement/page.tsx`**

Implement a `"use client"` page that:

1. `fetchOnboardingStatus` on mount — if `!survey_done` → `/onboarding`; if `placement_done` → `/dashboard`.
2. Load `fetchPlacementQuestions()`; keep `answers: Record<number, string>`.
3. Show index `current + 1 / questions.length`; for `mcq` render option buttons; else text `Input`.
4. Next/Back; on last question enable Submit.
5. `submitPlacement(Object.entries(answers).map(...))` — require all 10 answered.
6. Result view: score, `current_level`, copy: “You can create your learning roadmap when you are ready.” Link to `/dashboard` (do **not** call assemble).

Match visual language of survey page (`ef-card`, dark layout, `LogoutButton`). Keep file focused — one page component is enough for MVP.

Skeleton outline:

```tsx
"use client";
// imports: useEffect, useState, Link, useRouter, Button, Input, Loader2, fetchOnboardingStatus, fetchPlacementQuestions, submitPlacement

export default function PlacementPage() {
  // states: questions, index, answers, loading, submitting, error, result
  // effects: status gate + load questions
  // if result: show score/level/CTA
  // else: show stem + options/input + nav
}
```

- [ ] **Step 3: Redirects**

In `onboarding/page.tsx` after successful `submitSurvey`:

```typescript
router.replace("/onboarding/placement");
```

In `start-onboarding/page.tsx` CTA:

```tsx
<Link href={isContinue ? "/onboarding/placement" : "/onboarding"}>
  {isContinue ? "Continue Placement Test" : "Start Onboarding"}
  ...
</Link>
```

- [ ] **Step 4: Manual E2E**

1. Publish ≥2 questions per CEFR level A1–C1 (or enough for selector).
2. New user: survey → placement → 10 questions → submit → see level.
3. `GET /onboarding/status` → `onboarding_complete: true`.
4. Confirm no new roadmap weeks until separate assemble.

- [ ] **Step 5: Commit**

```bash
git add frontend/my-app/lib/placement.ts \
  frontend/my-app/src/app/onboarding/placement/page.tsx \
  frontend/my-app/src/app/onboarding/page.tsx \
  frontend/my-app/src/app/start-onboarding/page.tsx
git commit -m "$(cat <<'EOF'
feat: learner placement test UI after survey from quiz bank

EOF
)"
```

---

### Task 6: Verification checklist (no new code)

- [ ] **Step 1: Backend unit suite**

```bash
cd backend && python -m pytest tests/test_placement_service.py tests/test_mastery_service.py -v
```

Expected: all PASS.

- [ ] **Step 2: Spec acceptance**

| Check | Pass? |
|-------|-------|
| GET `/onboarding/questions` returns 10, no `answer` | |
| Insufficient bank → 503 + clear message | |
| POST placement sets `placement_score` + `current_level` | |
| Mastery rows updated; no `roadmap_steps` created | |
| Second GET/POST after done → 409 | |
| Admin publish removes drafts from draft list | |
| Survey → placement FE → result → dashboard | |

- [ ] **Step 3: Final commit only if checklist left doc notes** — otherwise stop; no empty commit.

---

## Spec coverage (self-review)

| Spec section | Task |
|--------------|------|
| Published-only bank + 2/level + fail-fast | Task 1–2 |
| Score table 0–10 → CEFR | Task 1 |
| GET `/questions` / POST `/placement` contracts | Task 3 |
| Profile + mastery; no assemble | Task 2 |
| Gates 400/409/503 | Task 2–3 |
| Admin list draft + publish | Task 4 |
| Learner FE + redirects | Task 5 |
| Acceptance / no retake / no Redis | Task 6 + non-goals |

**Out of scope (do not implement in this plan):** adaptive IRT, placement session token, Redis cache, retake, assemble CTA wiring, fuzzy cloze grading.

---

## Execution handoff

Plan saved to `docs/superpowers/plans/2026-07-15-placement-from-quiz-bank.md`.

**Two execution options:**

1. **Subagent-Driven (recommended)** — fresh subagent per task, review between tasks  
2. **Inline Execution** — same session with executing-plans + checkpoints  

Which approach?
