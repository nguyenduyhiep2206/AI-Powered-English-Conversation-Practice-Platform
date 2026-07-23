# Kế hoạch triển khai: Placement adaptive (Busuu-lite)

> **Dành cho agent/kỹ sư thực hiện:** BẮT BUỘC dùng skill `superpowers:subagent-driven-development` (khuyên dùng) hoặc `superpowers:executing-plans` để làm từng task. Các bước dùng checkbox (`- [ ]`) để theo dõi tiến độ.

**Mục tiêu:** Thay placement batch 10 câu bằng session adaptive (6–15 câu): trả lời từng câu → cập nhật ability → chọn câu tiếp (bias `weak_point`) hoặc kết thúc; ghi `current_level` + `placement_score` (sub-level 1–10); seed mastery; retake sau 7 ngày; `goal` không tham gia chọn câu.

**Kiến trúc:** Pure engine trong `placement_adaptive_engine.py` (unit-test không DB). Orchestrator `placement_session_service.py` quản lý attempt/answer/retake. Tái dùng `PlacementCandidate`, `load_published_candidates`, `grade_placement_answer`, `placement_public_dict` từ `placement_service.py`. API session mới trên onboarding router; deprecate batch endpoints sau khi FE chuyển.

**Công nghệ:** FastAPI, SQLAlchemy async, Alembic, pytest, Pydantic, Next.js (`authFetch`).

**Spec:** `docs/superpowers/specs/2026-07-23-adaptive-placement-design.md`

## Global Constraints

- Min câu: **6**; max câu: **15**; dừng sớm khi `confidence >= 0.85` và đã ≥ 6 câu.
- Chỉ bias **`weak_point`** khi pick câu; **`goal` không** xuất hiện trong engine/session pick paths.
- `placement_score` sau attempt mới = sub-level **1–10** (không còn = số câu đúng).
- Không auto-assemble roadmap khi complete placement.
- Không IRT / Redis / đổi schema survey trong plan này.
- Style service: orchestrator ngắn, helper theo ý định (`service-orchestrator`).

---

## Bản đồ file

| File | Vai trò |
|------|---------|
| `backend/app/models/enums.py` | Thêm `PlacementAttemptStatusEnum` + SAEnum |
| `backend/app/models/placement_attempt.py` | `PlacementAttemptDB`, `PlacementAttemptAnswerDB` |
| `backend/app/models/__init__.py` | Export models mới |
| `backend/alembic/versions/j0k1l2m3n4o5_add_placement_attempts.py` | Migration bảng + enum |
| `backend/app/services/placement_adaptive_engine.py` | Pure: ability, confidence, stop, pick, map profile, weak_point prefs |
| `backend/tests/test_placement_adaptive_engine.py` | Unit test engine |
| `backend/app/services/placement_session_service.py` | start / resume / answer / retake-status / complete |
| `backend/tests/test_placement_session_service.py` | Unit/integration nhẹ (mock DB hoặc pure helpers nếu tách được) |
| `backend/app/schemas/onboarding_schema.py` | Schema session adaptive |
| `backend/app/api/onboarding.py` | Routes mới; deprecate/410 batch |
| `frontend/my-app/lib/placement.ts` | Client session API |
| `frontend/my-app/src/app/onboarding/placement/page.tsx` | Wizard 1 câu + resume + kết quả |
| `frontend/my-app/src/app/dashboard/page.tsx` (hoặc settings) | Entry retake nếu có chỗ hợp lý |
| `docs/superpowers/specs/2026-07-23-adaptive-placement-design.md` | Đổi status → Approved / Implemented khi xong |

**Giữ nguyên (tái dùng):** `placement_service.load_published_candidates`, `placement_public_dict`, `grade_placement_answer`, `PlacementCandidate`. Level-challenge không đổi trong plan này.

**Có thể để lại tạm:** `score_to_level` / `select_from_candidates` + test cũ cho đến khi xóa batch endpoints (Task 5); sau đó đánh dấu deprecated hoặc xóa nếu không còn import.

---

### Task 1: Enum + models + migration

**Files:**
- Modify: `backend/app/models/enums.py`
- Create: `backend/app/models/placement_attempt.py`
- Modify: `backend/app/models/__init__.py`
- Create: `backend/alembic/versions/j0k1l2m3n4o5_add_placement_attempts.py`

**Interfaces:**
- Produces: `PlacementAttemptStatusEnum`, `PlacementAttemptDB`, `PlacementAttemptAnswerDB`

- [ ] **Bước 1: Thêm enum**

Trong `enums.py`, thêm:

```python
class PlacementAttemptStatusEnum(str, enum.Enum):
    in_progress = "in_progress"
    completed = "completed"
    abandoned = "abandoned"


placement_attempt_status_enum = SAEnum(
    PlacementAttemptStatusEnum,
    name="placement_attempt_status_enum",
    create_type=True,
)
```

- [ ] **Bước 2: Tạo model**

```python
# backend/app/models/placement_attempt.py
from sqlalchemy import (
    BigInteger,
    Boolean,
    Column,
    Float,
    ForeignKey,
    Integer,
    SmallInteger,
    String,
    Text,
    TIMESTAMP,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSON

from app.core.database import Base
from app.models.enums import cefr_level_enum, placement_attempt_status_enum


class PlacementAttemptDB(Base):
    __tablename__ = "placement_attempts"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id = Column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    status = Column(placement_attempt_status_enum, nullable=False)
    ability_index = Column(Float, nullable=False, default=1.0)
    confidence = Column(Float, nullable=False, default=0.0)
    questions_asked = Column(Integer, nullable=False, default=0)
    seen_question_ids = Column(JSON, nullable=False, default=list)
    current_question_id = Column(
        BigInteger, ForeignKey("quiz_questions.id", ondelete="SET NULL"), nullable=True
    )
    weak_point_bias = Column(String(50), nullable=True)
    result_level = Column(cefr_level_enum, nullable=True)
    result_sublevel = Column(SmallInteger, nullable=True)
    started_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())
    completed_at = Column(TIMESTAMP(timezone=True), nullable=True)


class PlacementAttemptAnswerDB(Base):
    __tablename__ = "placement_attempt_answers"
    __table_args__ = (
        UniqueConstraint("attempt_id", "question_id", name="uq_placement_attempt_question"),
    )

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    attempt_id = Column(
        BigInteger, ForeignKey("placement_attempts.id", ondelete="CASCADE"), nullable=False
    )
    question_id = Column(
        BigInteger, ForeignKey("quiz_questions.id", ondelete="CASCADE"), nullable=False
    )
    skill_id = Column(BigInteger, nullable=False)
    cefr_level = Column(cefr_level_enum, nullable=False)
    given_answer = Column(Text, nullable=False)
    is_correct = Column(Boolean, nullable=False)
    ability_after = Column(Float, nullable=False)
    confidence_after = Column(Float, nullable=False)
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())
```

- [ ] **Bước 3: Export trong `__init__.py`**

Import `PlacementAttemptDB`, `PlacementAttemptAnswerDB` và thêm vào `__all__`.

- [ ] **Bước 4: Migration Alembic**

`down_revision = "i9j0k1l2m3n4"`, `revision = "j0k1l2m3n4o5"`.

Tạo enum `placement_attempt_status_enum`, bảng `placement_attempts`, `placement_attempt_answers` + unique constraint như model. `downgrade` drop tables rồi drop enum.

- [ ] **Bước 5: Chạy migration**

```bash
cd backend && alembic upgrade head
```

Expected: OK, không error.

- [ ] **Bước 6: Commit**

```bash
git add backend/app/models/enums.py backend/app/models/placement_attempt.py \
  backend/app/models/__init__.py \
  backend/alembic/versions/j0k1l2m3n4o5_add_placement_attempts.py
git commit -m "$(cat <<'EOF'
feat: add placement_attempts tables for adaptive sessions

EOF
)"
```

---

### Task 2: Pure adaptive engine (TDD)

**Files:**
- Create: `backend/tests/test_placement_adaptive_engine.py`
- Create: `backend/app/services/placement_adaptive_engine.py`

**Interfaces:**
- Consumes: `PlacementCandidate`, `CEFRLevel`, `WeakPointEnum`, `SkillTypeEnum`
- Produces:
  - `MIN_QUESTIONS = 6`, `MAX_QUESTIONS = 15`, `CONFIDENCE_STOP = 0.85`, `ABILITY_STEP = 0.45`
  - `preferred_skill_types(weak_point) -> frozenset[str]`
  - `update_ability(ability, confidence, item_level, correct) -> tuple[float, float]`
  - `should_stop(asked, confidence) -> bool`
  - `map_ability_to_profile(ability_index) -> tuple[CEFRLevel, int]`  # level, sublevel 1..10
  - `pick_next_candidate(candidates, *, ability_index, seen_ids, used_skill_ids, weak_point, rng_seed=None) -> PlacementCandidate`

- [ ] **Bước 1: Viết test FAIL**

```python
# backend/tests/test_placement_adaptive_engine.py
from app.models.enums import CEFRLevel, WeakPointEnum
from app.services.placement_adaptive_engine import (
    MAX_QUESTIONS,
    MIN_QUESTIONS,
    map_ability_to_profile,
    pick_next_candidate,
    preferred_skill_types,
    should_stop,
    update_ability,
)
from app.services.placement_service import PlacementCandidate


def test_preferred_skill_types_mapping():
    assert "grammar" in preferred_skill_types(WeakPointEnum.grammar)
    assert "vocabulary" in preferred_skill_types(WeakPointEnum.vocabulary)
    assert "functional" in preferred_skill_types(WeakPointEnum.writing)
    assert preferred_skill_types(WeakPointEnum.confidence) == frozenset()
    assert preferred_skill_types(None) == frozenset()


def test_update_ability_correct_increases():
    a, c = update_ability(1.0, 0.0, item_level=1.0, correct=True)
    assert a > 1.0
    assert 0.0 <= c <= 1.0


def test_update_ability_wrong_decreases():
    a, c = update_ability(1.0, 0.5, item_level=1.0, correct=False)
    assert a < 1.0


def test_should_stop_rules():
    assert should_stop(5, 1.0) is False
    assert should_stop(6, 0.84) is False
    assert should_stop(6, 0.85) is True
    assert should_stop(MAX_QUESTIONS, 0.0) is True
    assert MIN_QUESTIONS == 6


def test_map_ability_to_profile_bounds():
    level, sub = map_ability_to_profile(0.0)
    assert level == CEFRLevel.A1
    assert 1 <= sub <= 10
    level, sub = map_ability_to_profile(4.0)
    assert level == CEFRLevel.C1
    assert 1 <= sub <= 10
    level, _ = map_ability_to_profile(2.2)
    assert level == CEFRLevel.B1


def _cand(id_, skill_id, level, skill_type="grammar"):
    # PlacementCandidate không có skill_type — engine pick nhận thêm map skill_id->type
    return PlacementCandidate(
        id=id_,
        skill_id=skill_id,
        cefr_level=level,
        question_type="mcq",
        stem="s",
        options=["a", "b"],
        difficulty="medium",
        answer="a",
    )


def test_pick_next_prefers_target_cefr_and_weak_point():
    cands = [
        _cand(1, 10, CEFRLevel.A1),
        _cand(2, 11, CEFRLevel.A2),
        _cand(3, 12, CEFRLevel.A2),
        _cand(4, 13, CEFRLevel.B1),
    ]
    skill_types = {10: "grammar", 11: "vocabulary", 12: "grammar", 13: "grammar"}
    picked = pick_next_candidate(
        cands,
        ability_index=1.0,
        seen_ids=set(),
        used_skill_ids=set(),
        weak_point=WeakPointEnum.grammar,
        skill_types_by_skill_id=skill_types,
        rng_seed=1,
    )
    assert picked.cefr_level == CEFRLevel.A2
    assert skill_types[picked.skill_id] == "grammar"
```

**Lưu ý implement:** `PlacementCandidate` hiện không có `skill_type` — truyền `skill_types_by_skill_id: dict[int, str]` vào `pick_next_candidate` (session service build map từ `LearningSkillDB` khi load bank). Cập nhật chữ ký test/engine cho khớp.

- [ ] **Bước 2: Chạy test — kỳ vọng FAIL**

```bash
cd backend && python -m pytest tests/test_placement_adaptive_engine.py -v
```

Expected: import error / FAIL.

- [ ] **Bước 3: Implement engine**

```python
# backend/app/services/placement_adaptive_engine.py
"""Pure adaptive placement engine (no DB / IRT)."""

from __future__ import annotations

import math
import random
from typing import Sequence

from app.models.enums import CEFRLevel, WeakPointEnum
from app.services.placement_service import CEFR_ORDER, PlacementCandidate

MIN_QUESTIONS = 6
MAX_QUESTIONS = 15
CONFIDENCE_STOP = 0.85
ABILITY_STEP = 0.45

_CEFR_INDEX = {lvl: i for i, lvl in enumerate(CEFR_ORDER)}


def preferred_skill_types(weak_point: WeakPointEnum | str | None) -> frozenset[str]:
    if weak_point is None:
        return frozenset()
    value = weak_point.value if hasattr(weak_point, "value") else str(weak_point)
    mapping = {
        "grammar": frozenset({"grammar"}),
        "vocabulary": frozenset({"vocabulary"}),
        "writing": frozenset({"functional"}),
        "confidence": frozenset(),
    }
    return mapping.get(value, frozenset())


def cefr_index(level: CEFRLevel) -> int:
    return _CEFR_INDEX[level]


def update_ability(
    ability_index: float,
    confidence: float,
    *,
    item_level: float,
    correct: bool,
) -> tuple[float, float]:
    before = float(ability_index)
    conf = float(confidence)
    if correct:
        delta = ABILITY_STEP * (1.0 + 0.25 * max(0.0, item_level - before))
        ability = before + delta
    else:
        delta = ABILITY_STEP * (1.0 + 0.25 * max(0.0, before - item_level))
        ability = before - delta
    ability = max(0.0, min(4.0, ability))

    surprise = abs(item_level - before)
    expected_ok = correct and item_level >= before - 0.5
    expected_miss = (not correct) and item_level <= before + 0.5
    if expected_ok or expected_miss:
        conf += 0.12 + 0.03 * surprise
    else:
        conf -= 0.08
    conf = max(0.0, min(1.0, conf))
    return ability, conf


def should_stop(asked: int, confidence: float) -> bool:
    if asked >= MAX_QUESTIONS:
        return True
    if asked >= MIN_QUESTIONS and float(confidence) >= CONFIDENCE_STOP:
        return True
    return False


def map_ability_to_profile(ability_index: float) -> tuple[CEFRLevel, int]:
    a = max(0.0, min(4.0, float(ability_index)))
    idx = int(round(a))
    idx = max(0, min(4, idx))
    level = CEFR_ORDER[idx]
    # Sub-level from position within the rounded band's neighborhood
    low = idx - 0.5
    high = idx + 0.5
    frac = (a - low) / (high - low) if high > low else 0.5
    frac = max(0.0, min(1.0, frac))
    sub = int(frac * 10)
    sub = max(1, min(10, sub if sub >= 1 else 1))
    if sub == 0:
        sub = 1
    # Ensure 1..10 even at exact boundaries
    sub = max(1, min(10, int(math.floor(frac * 9)) + 1))
    return level, sub


def pick_next_candidate(
    candidates: Sequence[PlacementCandidate],
    *,
    ability_index: float,
    seen_ids: set[int],
    used_skill_ids: set[int],
    weak_point: WeakPointEnum | str | None,
    skill_types_by_skill_id: dict[int, str],
    rng_seed: int | None = None,
) -> PlacementCandidate:
    rng = random.Random(rng_seed)
    preferred = preferred_skill_types(weak_point)
    target_idx = max(0, min(4, int(round(float(ability_index)))))
    pool = [c for c in candidates if int(c.id) not in seen_ids]
    if not pool:
        raise ValueError("Không còn câu hỏi published phù hợp cho placement adaptive.")

    def at_levels(indexes: set[int]) -> list[PlacementCandidate]:
        return [c for c in pool if cefr_index(c.cefr_level) in indexes]

    window = at_levels({target_idx})
    if not window:
        window = at_levels({target_idx - 1, target_idx, target_idx + 1} & {0, 1, 2, 3, 4})
    if not window:
        raise ValueError("Không còn câu hỏi published phù hợp cho placement adaptive.")

    def sort_key(c: PlacementCandidate) -> tuple:
        st = skill_types_by_skill_id.get(int(c.skill_id), "")
        pref = 0 if (preferred and st in preferred) else 1
        unused = 0 if int(c.skill_id) not in used_skill_ids else 1
        return (pref, unused, rng.random())

    return sorted(window, key=sort_key)[0]
```

Chỉnh `map_ability_to_profile` nếu test biên cần tinh chỉnh — ưu tiên test xanh với `1 <= sub <= 10` và level đúng.

- [ ] **Bước 4: Chạy test — PASS**

```bash
cd backend && python -m pytest tests/test_placement_adaptive_engine.py -v
```

- [ ] **Bước 5: Commit**

```bash
git add backend/app/services/placement_adaptive_engine.py \
  backend/tests/test_placement_adaptive_engine.py
git commit -m "$(cat <<'EOF'
feat: add pure adaptive placement engine

EOF
)"
```

---

### Task 3: Session service (orchestrator)

**Files:**
- Create: `backend/app/services/placement_session_service.py`
- Create: `backend/tests/test_placement_session_helpers.py` (pure helpers: retake window, progress dict)

**Interfaces:**
- Consumes: engine + `load_published_candidates` + `grade_placement_answer` + `apply_answer` + models
- Produces:
  - `RETAKE_COOLDOWN_DAYS = 7`
  - `async def get_retake_status(db, user_id) -> dict`
  - `async def start_or_resume_session(db, user_id) -> dict`  # attempt + question + progress
  - `async def get_current_session(db, user_id) -> dict | None`
  - `async def submit_session_answer(db, user_id, attempt_id, question_id, answer) -> dict`

Response shapes (khóa ổn định cho schema):

```python
# progress
{"asked": int, "min_questions": 6, "max_questions": 15}

# mid
{"done": False, "attempt_id": int, "question": dict, "progress": dict}

# final
{
  "done": True,
  "attempt_id": int,
  "placement_score": int,
  "current_level": str,
  "questions_asked": int,
  "onboarding_complete": True,
}
```

- [ ] **Bước 1: Test helper retake / progress**

```python
# backend/tests/test_placement_session_helpers.py
from datetime import datetime, timedelta, timezone

from app.services.placement_session_service import (
    RETAKE_COOLDOWN_DAYS,
    retake_allowed,
    progress_dict,
)


def test_progress_dict():
    assert progress_dict(3) == {
        "asked": 3,
        "min_questions": 6,
        "max_questions": 15,
    }


def test_retake_allowed_never_completed():
    assert retake_allowed(last_completed_at=None, now=datetime.now(timezone.utc)) is True


def test_retake_cooldown():
    now = datetime(2026, 7, 23, tzinfo=timezone.utc)
    assert retake_allowed(now - timedelta(days=6), now) is False
    assert retake_allowed(now - timedelta(days=7), now) is True
    assert RETAKE_COOLDOWN_DAYS == 7
```

- [ ] **Bước 2: Implement helpers + orchestrator**

Skeleton `placement_session_service.py`:

```python
async def start_or_resume_session(db, user_id: int) -> dict:
    profile = await _require_survey_done(db, user_id)
    current = await _get_in_progress(db, user_id)
    if current is not None:
        return await _session_payload(db, current, done=False)

    if profile.placement_score is not None:
        status = await get_retake_status(db, user_id)
        if not status["allowed"]:
            raise RuntimeError("Chưa đến lúc làm lại placement")
        await _abandon_in_progress(db, user_id)  # no-op if none

    attempt = await _create_attempt(db, profile)
    question = await _serve_next_question(db, attempt, profile.weak_point)
    await db.commit()
    await db.refresh(attempt)
    return {
        "done": False,
        "attempt_id": int(attempt.id),
        "question": placement_public_dict(question),
        "progress": progress_dict(int(attempt.questions_asked)),
    }


async def submit_session_answer(...):
    attempt = await _require_in_progress_owned(db, user_id, attempt_id)
    if int(attempt.current_question_id) != int(question_id):
        raise ValueError("question_id không khớp câu hiện tại")
    # load question+skill, grade, write answer row
    # update ability/confidence/questions_asked/seen
    # if should_stop: complete profile + mastery; return done True
    # else serve next; return done False
```

Chi tiết bắt buộc:
- Snapshot `weak_point_bias` lúc create.
- `seen_question_ids` luôn list[int] JSON.
- Complete: `map_ability_to_profile` → profile + attempt.result_*; seed mastery mọi answer của attempt; `completed_at=now`.
- Insufficient bank → `ValueError` message rõ (API map 503).
- **Không** đọc `profile.goal` trong file này.

- [ ] **Bước 3: pytest helpers PASS**

```bash
cd backend && python -m pytest tests/test_placement_session_helpers.py tests/test_placement_adaptive_engine.py -v
```

- [ ] **Bước 4: Commit**

```bash
git add backend/app/services/placement_session_service.py \
  backend/tests/test_placement_session_helpers.py
git commit -m "$(cat <<'EOF'
feat: add adaptive placement session orchestrator

EOF
)"
```

---

### Task 4: Schemas + API routes

**Files:**
- Modify: `backend/app/schemas/onboarding_schema.py`
- Modify: `backend/app/api/onboarding.py`

**Interfaces:**
- Produces HTTP:
  - `POST /api/v1/onboarding/placement/sessions`
  - `GET /api/v1/onboarding/placement/sessions/current`
  - `POST /api/v1/onboarding/placement/sessions/{attempt_id}/answers`
  - `GET /api/v1/onboarding/placement/retake-status`

- [ ] **Bước 1: Thêm schema**

```python
class PlacementProgressOut(BaseModel):
    asked: int
    min_questions: int = 6
    max_questions: int = 15


class PlacementSessionData(BaseModel):
    done: bool
    attempt_id: int
    question: PlacementQuestionOut | None = None
    progress: PlacementProgressOut | None = None
    placement_score: int | None = None
    current_level: str | None = None
    questions_asked: int | None = None
    onboarding_complete: bool | None = None


class PlacementSessionResponse(BaseModel):
    success: bool = True
    data: PlacementSessionData


class PlacementAnswerRequest(BaseModel):
    question_id: int
    answer: str


class PlacementRetakeStatusData(BaseModel):
    allowed: bool
    has_in_progress: bool
    retry_after_at: datetime | None = None


class PlacementRetakeStatusResponse(BaseModel):
    success: bool = True
    data: PlacementRetakeStatusData
```

- [ ] **Bước 2: Wire routes** — map `PermissionError`→400/403, `RuntimeError`→409, bank `ValueError`→503, validation→400. Giữ level-challenge routes nguyên.

- [ ] **Bước 3: Smoke thủ công hoặc httpx test tối thiểu** (optional file `tests/test_placement_session_api.py` nếu repo đã có pattern API test với DB fixture; nếu chưa có fixture sẵn thì smoke bằng cách gọi service với DB test — không block nếu môi trường thiếu).

- [ ] **Bước 4: Commit**

```bash
git commit -m "$(cat <<'EOF'
feat: expose adaptive placement session API

EOF
)"
```

---

### Task 5: Deprecate batch placement endpoints

**Files:**
- Modify: `backend/app/api/onboarding.py`

- [ ] **Bước 1:** Đổi `GET /questions` và `POST /placement` trả **410** với detail hướng dẫn dùng `/placement/sessions` (sau khi FE Task 6 merge cùng nhánh — nếu FE chưa xong, làm Task 5 **sau** Task 6 trên cùng branch).

```python
raise HTTPException(
    status_code=410,
    detail="Deprecated. Use POST /onboarding/placement/sessions",
)
```

- [ ] **Bước 2:** Commit

```bash
git commit -m "$(cat <<'EOF'
chore: deprecate batch placement endpoints

EOF
)"
```

---

### Task 6: Frontend client + placement wizard

**Files:**
- Modify: `frontend/my-app/lib/placement.ts`
- Modify: `frontend/my-app/src/app/onboarding/placement/page.tsx`
- Modify copy nếu cần: `frontend/my-app/src/app/start-onboarding/page.tsx`, `onboarding/page.tsx`

- [ ] **Bước 1: Đổi `placement.ts`**

```typescript
export type PlacementProgress = {
  asked: number;
  min_questions: number;
  max_questions: number;
};

export type PlacementSession = {
  done: boolean;
  attempt_id: number;
  question?: PlacementQuestion | null;
  progress?: PlacementProgress | null;
  placement_score?: number | null;
  current_level?: string | null;
  questions_asked?: number | null;
  onboarding_complete?: boolean | null;
};

export async function startPlacementSession(): Promise<PlacementSession> { ... }
export async function getCurrentPlacementSession(): Promise<PlacementSession | null> { ... }
export async function submitPlacementAnswer(
  attemptId: number,
  payload: { question_id: number; answer: string },
): Promise<PlacementSession> { ... }
export async function fetchRetakeStatus(): Promise<{
  allowed: boolean;
  has_in_progress: boolean;
  retry_after_at?: string | null;
}> { ... }
```

Xóa hoặc ngừng export `fetchPlacementQuestions` / `submitPlacement` batch.

- [ ] **Bước 2: Viết lại page**

Flow:
1. Load status onboarding (như hiện tại).
2. `getCurrentPlacementSession()`; nếu null → `startPlacementSession()`.
3. Hiển thị 1 câu; Submit → `submitPlacementAnswer`.
4. Nếu `done` → màn kết quả CEFR + sub-level + CTA assemble (giữ logic assemble hiện có).
5. Progress text: `asked / max_questions` + ghi chú có thể kết thúc từ câu 6.

- [ ] **Bước 3: Sửa copy “10 câu” → “6–15 câu adaptive”** trên start-onboarding / onboarding nếu còn.

- [ ] **Bước 4: Commit**

```bash
git commit -m "$(cat <<'EOF'
feat: adaptive placement wizard on frontend

EOF
)"
```

---

### Task 7: Retake entry trên dashboard

**Files:**
- Modify: dashboard page phù hợp (kiểm tra `frontend/my-app/src/app/dashboard/page.tsx` — thêm link “Làm lại placement” khi `retake-status.allowed`, hoặc disable + hiện `retry_after_at`).

- [ ] **Bước 1:** Gọi `fetchRetakeStatus`; nếu `has_in_progress` → link resume `/onboarding/placement`; nếu `allowed` → CTA start lại; else hiện ngày mở lại.

- [ ] **Bước 2:** Commit

```bash
git commit -m "$(cat <<'EOF'
feat: show placement retake status on dashboard

EOF
)"
```

---

### Task 8: Spec status + regression check

**Files:**
- Modify: `docs/superpowers/specs/2026-07-23-adaptive-placement-design.md` (Status → Implemented)
- Optionally note superseded learner path trên spec `2026-07-15-...`

- [ ] **Bước 1: Chạy regression**

```bash
cd backend && python -m pytest tests/test_placement_adaptive_engine.py \
  tests/test_placement_session_helpers.py tests/test_placement_service.py \
  tests/test_roadmap_assembler_service.py -v
```

Expected: engine/helpers PASS. `test_placement_service.py` vẫn PASS nếu còn giữ batch helpers; roadmap không gãy.

- [ ] **Bước 2: Cập nhật status spec + commit docs**

```bash
git commit -m "$(cat <<'EOF'
docs: mark adaptive placement spec implemented

EOF
)"
```

---

## Self-review (plan vs spec)

| Spec requirement | Task |
|------------------|------|
| Adaptive session API | 3, 4, 6 |
| Min 6 / max 15 / confidence stop | 2, 3 |
| Bank published only | 3 (load_published_candidates) |
| weak_point bias only; no goal | 2, 3 |
| Attempt + answer tables | 1 |
| current_level + sub-level placement_score | 2, 3 |
| Mastery seed on complete | 3 |
| Retake 7 days | 3, 4, 7 |
| Deprecate batch | 5 (sau FE) |
| FE wizard | 6 |
| No auto-assemble | 3, 6 (giữ CTA riêng) |

Không còn TBD trong plan. Chữ ký `pick_next_candidate` thống nhất qua `skill_types_by_skill_id`.

---

## Handoff thực thi

Plan đã lưu tại `docs/superpowers/plans/2026-07-23-adaptive-placement.md`.

**Hai cách chạy:**

1. **Subagent-Driven (khuyên dùng)** — mỗi task một subagent, review giữa các task  
2. **Inline Execution** — làm tuần tự trong session này với checkpoint  

Bạn muốn cách nào?
