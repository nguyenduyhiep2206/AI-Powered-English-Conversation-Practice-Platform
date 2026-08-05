# Lesson Q&A RAG Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** Collapsible Lesson Q&A chatbot under the practice lesson that retrieves book chunks for the current skill, answers with CEFR-aware prompts, persists chat per user+skill, shows cite + suggested question chips.

**Architecture:** New `lesson_qa_*` tables + FastAPI routes under `/api/v1/lessons/{skill_id}/qa`. Turn pipeline: off-topic → `should_retrieve` → `tutor_rag.retrieve_for_session` (+ Redis cache with `lesson_qa:` key prefix) → Q&A system prompt → SSE. Frontend `LessonQaPanel` on `/dashboard/practice/[skillId]`.

**Tech Stack:** FastAPI, SQLAlchemy/Alembic, Postgres, Mongo `book_chunks`, Voyage embeddings, Redis, Next.js, existing tutor SSE helpers.

**Spec:** `docs/superpowers/specs/2026-08-05-lesson-qa-rag-design.md`

> **Note (commits):** Tasks 1–7 committed on this branch. Task 8 practice-page mount already present in `3d58969` (imports `LessonQaPanel`); this docs commit accepts the design.

## Global Constraints

- **Do not commit** unless the user explicitly asks to commit (stage files only otherwise)
- Reuse `tutor_rag` / `tutor_memory` / Redis patterns — do **not** add Chroma/FAISS/OpenAI embeddings
- Scope retrieve only via `skill_id` path param → `retrieve_for_session(skill_ids=[skill_id])`
- Lesson Q&A uses `should_retrieve` (default retrieve), **not** Tutor `needs_rag`
- Suggested chips: deterministic from skill/pack — **no LLM** for chip generation
- P1 lesson-pack-as-corpus fallback is **out of scope**
- Public service orchestrators ≤ ~15–20 lines of real logic (`.cursor/rules/service-orchestrator.mdc`)
- Alembic `down_revision` = `u0v1w2x3y4z5` (current tutor nullable-step head)

---

## File map

| File | Responsibility |
|------|----------------|
| `backend/app/core/config.py` | `LESSON_QA_RAG_ENABLED`, `LESSON_QA_MEMORY_MAX_TURNS` (reuse `TUTOR_RAG_*` for top-k/score/chars/ttl) |
| `backend/app/models/enums.py` | `LessonQaSessionStatusEnum`, role enum (or reuse tutor message roles) |
| `backend/app/models/lesson_qa.py` | `LessonQaSessionDB`, `LessonQaMessageDB` |
| `backend/alembic/versions/v1w2x3y4z5a6_lesson_qa_sessions.py` | tables + unique `(user_id, skill_id)` |
| `backend/app/schemas/lesson_qa_schema.py` | DTOs + post body |
| `backend/app/services/lesson_qa_gates.py` | `should_retrieve` |
| `backend/app/services/lesson_qa_suggest.py` | `build_suggested_prompts(...)` |
| `backend/app/services/lesson_qa_prompt.py` | CEFR Q&A system + user payload |
| `backend/app/services/lesson_qa_cache.py` | thin wrapper: cache key prefix `lesson_qa:rag:` (or pass prefix into shared helpers) |
| `backend/app/services/lesson_qa_service.py` | ensure session, get, clear, turn SSE |
| `backend/app/api/lesson_qa.py` | GET/POST/DELETE routes |
| `backend/main.py` | `include_router` |
| `backend/tests/test_lesson_qa_*.py` | gates, suggest, prompt, service/API |
| `frontend/my-app/lib/lesson-qa.ts` | API + SSE client |
| `frontend/my-app/components/lesson/LessonQaPanel.tsx` | collapsible UI, chips, cite, debug |
| `frontend/my-app/src/app/dashboard/practice/[skillId]/page.tsx` | mount panel |

---

### Task 1: Config + `should_retrieve`

**Files:**
- Modify: `backend/app/core/config.py`
- Create: `backend/app/services/lesson_qa_gates.py`
- Test: `backend/tests/test_lesson_qa_gates.py`

**Interfaces:**
- Produces: `should_retrieve(content: str) -> bool`

- [x] **Step 1: Write the failing test**

```python
# backend/tests/test_lesson_qa_gates.py
from app.services.lesson_qa_gates import should_retrieve

def test_should_retrieve_skips_short_and_acks():
    assert should_retrieve("Hi") is False
    assert should_retrieve("ok") is False
    assert should_retrieve("thanks") is False
    assert should_retrieve("  ") is False

def test_should_retrieve_accepts_lesson_questions():
    assert should_retrieve("What does reservation mean?") is True
    assert should_retrieve("How do I use I'd like?") is True
```

- [x] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_lesson_qa_gates.py -v`  
Expected: FAIL import / not found

- [x] **Step 3: Implement**

```python
# backend/app/services/lesson_qa_gates.py
from __future__ import annotations

_ACK = frozenset({
    "hi", "hello", "ok", "okay", "thanks", "thank you", "yeah", "yup",
})

def should_retrieve(content: str) -> bool:
    t = (content or "").strip()
    if not t:
        return False
    if len(t) < 8:
        return False
    if " ".join(t.lower().split()) in _ACK:
        return False
    return True
```

Add to `Settings` in `config.py`:

```python
LESSON_QA_RAG_ENABLED: bool = True
LESSON_QA_MEMORY_MAX_TURNS: int = 6
```

- [x] **Step 4: Run tests — expect PASS**

Run: `cd backend && python -m pytest tests/test_lesson_qa_gates.py -v`

- [x] **Step 5: Stage only (no commit unless user asked)**

```bash
git add backend/app/core/config.py backend/app/services/lesson_qa_gates.py backend/tests/test_lesson_qa_gates.py
```

---

### Task 2: Suggested prompts builder

**Files:**
- Create: `backend/app/services/lesson_qa_suggest.py`
- Test: `backend/tests/test_lesson_qa_suggest.py`

**Interfaces:**
- Produces: `build_suggested_prompts(*, skill_title: str, objective: str | None, targets: list[str], max_n: int = 5) -> list[str]` (len 3..5 when enough signal; never empty — fall back to title-based generics)

- [x] **Step 1: Failing test**

```python
from app.services.lesson_qa_suggest import build_suggested_prompts

def test_suggest_uses_targets_not_generic_only():
    prompts = build_suggested_prompts(
        skill_title="Making a reservation",
        objective="Book a table politely",
        targets=["reservation", "I'd like"],
    )
    assert 3 <= len(prompts) <= 5
    joined = " ".join(prompts).lower()
    assert "reservation" in joined
    assert "i'd like" in joined or "i'd like" in joined.replace("’", "'")

def test_suggest_falls_back_to_skill_title():
    prompts = build_suggested_prompts(
        skill_title="Past simple",
        objective=None,
        targets=[],
    )
    assert 3 <= len(prompts) <= 5
    assert any("past simple" in p.lower() for p in prompts)
```

- [x] **Step 2: Run — expect FAIL**

- [x] **Step 3: Implement** (deterministic templates)

```python
def build_suggested_prompts(*, skill_title: str, objective: str | None, targets: list[str], max_n: int = 5) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()

    def add(s: str) -> None:
        t = " ".join(s.split())
        key = t.lower()
        if not t or key in seen or len(out) >= max_n:
            return
        seen.add(key)
        out.append(t)

    for surface in targets[:3]:
        s = (surface or "").strip()
        if s:
            add(f'What does "{s}" mean?')
            add(f'How do I use "{s}"?')
    title = (skill_title or "this lesson").strip() or "this lesson"
    add(f"Give an example sentence for {title}.")
    if objective and objective.strip():
        add(f"Can you explain: {objective.strip()}?")
    add(f"What should I practice in {title}?")
    # Ensure at least 3
    fallbacks = [
        f"What is the main point of {title}?",
        f"Common mistakes with {title}?",
        f"Give me two useful phrases for {title}.",
    ]
    for f in fallbacks:
        add(f)
        if len(out) >= 3:
            break
    return out[:max_n]
```

- [x] **Step 4: Run — expect PASS**

- [x] **Step 5: Stage**

---

### Task 3: Models + Alembic migration

**Files:**
- Modify: `backend/app/models/enums.py`
- Create: `backend/app/models/lesson_qa.py`
- Modify: `backend/app/models/__init__.py` (export)
- Create: `backend/alembic/versions/v1w2x3y4z5a6_lesson_qa_sessions.py`

**Interfaces:**
- Produces: `LessonQaSessionDB`, `LessonQaMessageDB`

- [x] **Step 1: Add enums** (mirror tutor style)

```python
class LessonQaSessionStatusEnum(str, enum.Enum):
    active = "active"
    ended = "ended"

class LessonQaMessageRoleEnum(str, enum.Enum):
    user = "user"
    assistant = "assistant"
```

Wire SAEnum helpers like existing tutor enums.

- [x] **Step 2: Models**

```python
# backend/app/models/lesson_qa.py
class LessonQaSessionDB(Base):
    __tablename__ = "lesson_qa_sessions"
    __table_args__ = (UniqueConstraint("user_id", "skill_id", name="uq_lesson_qa_user_skill"),)

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    skill_id = Column(BigInteger, ForeignKey("learning_skills.id", ondelete="CASCADE"), nullable=False, index=True)
    status = Column(lesson_qa_session_status_enum, nullable=False)
    message_count = Column(SmallInteger, nullable=False, default=0)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

class LessonQaMessageDB(Base):
    __tablename__ = "lesson_qa_messages"
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    session_id = Column(BigInteger, ForeignKey("lesson_qa_sessions.id", ondelete="CASCADE"), nullable=False, index=True)
    role = Column(lesson_qa_message_role_enum, nullable=False)
    content = Column(Text, nullable=False)
    meta = Column(JSON, nullable=True)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)
```

- [x] **Step 3: Migration** `revision=v1w2x3y4z5a6`, `down_revision=u0v1w2x3y4z5`  
  Create enums + tables + unique constraint (follow `t9u0v1w2x3y4_tutor_sessions.py` patterns).

- [x] **Step 4: Register in `models/__init__.py`**

- [x] **Step 5: Smoke migrate if DB available**

Run: `cd backend && alembic upgrade head`  
Expected: OK (skip locally if no DB; CI/dev applies later)

- [x] **Step 6: Stage**

---

### Task 4: Prompt builder (CEFR + retrieved block)

**Files:**
- Create: `backend/app/services/lesson_qa_prompt.py`
- Test: `backend/tests/test_lesson_qa_prompt.py`

**Interfaces:**
- Produces:
  - `build_qa_system_prompt(*, cefr_level: str, skill_title: str, retrieved_context: str | None, force_off_topic: bool = False) -> str`
  - `build_qa_user_payload(*, transcript: list[dict]) -> str`
  - `sources_from_chunks(chunks: list[dict]) -> list[dict]` → `[{unit_title, score}]` unique titles max 3

- [x] **Step 1: Failing tests**

```python
from app.services.lesson_qa_prompt import (
    build_qa_system_prompt,
    sources_from_chunks,
)

def test_prompt_includes_cefr_and_retrieved():
    p = build_qa_system_prompt(
        cefr_level="A2",
        skill_title="Making a reservation",
        retrieved_context="[1] (Unit 3, score=0.8)\nA reservation is...",
    )
    assert "CEFR A2" in p or "A2" in p
    assert "Retrieved book context" in p
    assert "do not invent" in p.lower() or "Do not invent" in p

def test_sources_dedupe_titles():
    src = sources_from_chunks([
        {"unit_title": "Unit 3", "score": 0.9},
        {"unit_title": "Unit 3", "score": 0.8},
        {"unit_title": "Unit 4", "score": 0.7},
    ])
    assert [s["unit_title"] for s in src] == ["Unit 3", "Unit 4"]
```

- [x] **Step 2: Run — FAIL**

- [x] **Step 3: Implement** — embed CEFR length rules (A1–A2 short sentences; B1+ slightly longer), answer-only-from-retrieved, off-topic redirect copy (not in character). Use `format_retrieved_block` from `tutor_rag` at call site; prompt receives already-formatted string.

- [x] **Step 4: Run — PASS**

- [x] **Step 5: Stage**

---

### Task 5: Schemas + ensure/get/clear service + GET API

**Files:**
- Create: `backend/app/schemas/lesson_qa_schema.py`
- Create: `backend/app/services/lesson_qa_service.py` (get/ensure/clear first)
- Create: `backend/app/api/lesson_qa.py`
- Modify: `backend/main.py` — `include_router(..., prefix="/api/v1/lessons", tags=["lesson-qa"])`
- Test: `backend/tests/test_lesson_qa_service.py` (DB fixtures — follow patterns in `test_tutor_*` / lesson tests; if heavy, test pure helpers + mock ensure)

**Interfaces:**
- Produces:
  - `async def get_or_create_session(db, user_id: int, skill_id: int) -> LessonQaSessionDB`
  - `async def get_qa_bundle(db, user_id: int, skill_id: int) -> dict`  
    `{session, messages, suggested_prompts}`  
  - `async def clear_messages(db, user_id: int, skill_id: int) -> None`
- API:
  - `GET /api/v1/lessons/{skill_id}/qa` → `{ data: LessonQaBundleDTO }`
  - `DELETE /api/v1/lessons/{skill_id}/qa/messages`

**DTO sketch:**

```python
class LessonQaMessageDTO(BaseModel):
    id: int
    role: str
    content: str
    meta: dict | None = None
    created_at: datetime

class LessonQaSessionDTO(BaseModel):
    id: int
    skill_id: int
    status: str
    message_count: int

class LessonQaBundleDTO(BaseModel):
    session: LessonQaSessionDTO
    messages: list[LessonQaMessageDTO]
    suggested_prompts: list[str]

class LessonQaTurnRequest(BaseModel):
    content: str = Field(..., min_length=1, max_length=2000)
    debug: bool = False
```

- [x] **Step 1: Implement models/schemas + `get_or_create_session`**  
  404 if skill missing. Load published lesson pack (lowest `pack_index` or current progress pack if easy — prefer first published lesson for targets via `content.targets[].surface`). Build suggestions via Task 2.

- [x] **Step 2: Wire GET + DELETE routes** with `get_current_active_user`

- [x] **Step 3: Test ensure is idempotent (same user+skill → same session id)**  
  Use existing async DB test fixtures if present; else unittest.mock for skill load path of suggest only + integration later.

- [x] **Step 4: Stage**

---

### Task 6: Turn pipeline + SSE POST (+ Redis cache)

**Files:**
- Modify: `backend/app/services/lesson_qa_service.py`
- Modify: `backend/app/api/lesson_qa.py`
- Optional create: `backend/app/services/lesson_qa_cache.py` — same as tutor cache but:

```python
def cache_key(normalized_query: str, skill_ids: list[int]) -> str:
    # identical digest to tutor_rag_cache but prefix:
    return f"lesson_qa:rag:{digest}"
```

Reuse `normalize_query`, `cache_get`, `cache_set` from `tutor_rag_cache`.

**Interfaces:**
- Produces: `async def iter_qa_turn_sse(db, user_id, skill_id, content, *, debug: bool) -> AsyncIterator[str]`  
  Events mirror tutor: `token` / `meta` / `debug` / `done` / `error` (match existing tutor SSE event names used by FE `readSseStream`).

**Turn orchestration (keep public fn short):**

```python
async def iter_qa_turn_sse(...):
    session = await _require_session(db, user_id, skill_id)
    await _persist_user(db, session, content)
    cefr = await _load_cefr(db, user_id)  # profile.current_level → str, default "A1"
    skill_title = await _load_skill_title(db, skill_id)
    ctx = await _build_turn_context(db, session, content, skill_id)
    system = build_qa_system_prompt(
        cefr_level=cefr,
        skill_title=skill_title,
        retrieved_context=ctx["retrieved_block"],
        force_off_topic=ctx["force_off_topic"],
    )
    user_payload = build_qa_user_payload(transcript=ctx["transcript"])
    async for event in _stream_llm_and_persist(...):
        yield event
```

`_build_turn_context` logic (exact):

```text
if is_off_topic(content): route=off_topic, no retrieve
elif settings.LESSON_QA_RAG_ENABLED and should_retrieve(content):
    chunks via cache → retrieve_for_session(db, skill_ids=[skill_id], query=content)
    route = rag if chunks else retrieval_empty
else:
    route = smalltalk
memory: window_transcript(..., max_turns=settings.LESSON_QA_MEMORY_MAX_TURNS, keep_first_assistant=True)
sources = sources_from_chunks(chunks) for assistant meta
```

LLM streaming: **copy the pattern** from `tutor_service._stream_assistant_turn` / `iter_turn_sse` (same OpenAI/client helper the tutor uses). Do not invent a new LLM client.

- [x] **Step 1: Unit-test `_build_turn_context` routing** with mocks on `retrieve_for_session` / `is_off_topic`

```python
@pytest.mark.asyncio
async def test_off_topic_skips_retrieve(monkeypatch):
    ...
    assert ctx["route"] == "off_topic"
    assert ctx["retrieved_block"] is None

@pytest.mark.asyncio
async def test_question_sets_rag_route(monkeypatch):
    monkeypatch.setattr(..., lambda *a, **k: [{"unit_title": "U3", "score": 0.9, "text": "..."}])
    ...
    assert ctx["route"] == "rag"
    assert ctx["sources"]
```

- [x] **Step 2: Implement POST SSE route**

```python
@router.post("/{skill_id}/qa/messages")
async def post_message(...):
    async def gen():
        async for chunk in iter_qa_turn_sse(...):
            yield chunk
    return StreamingResponse(gen(), media_type="text/event-stream")
```

- [x] **Step 3: Manual smoke** (optional): hit GET then POST with auth cookie/token

- [x] **Step 4: Stage**

---

### Task 7: Frontend client + `LessonQaPanel`

**Files:**
- Create: `frontend/my-app/lib/lesson-qa.ts`
- Create: `frontend/my-app/components/lesson/LessonQaPanel.tsx`
- Reuse SSE reader from `lib/tutor.ts` — **extract or import** `readSseStream` if exported; if not exported, duplicate minimal reader or export it from tutor.ts in this task.

**Interfaces:**
- `getLessonQa(skillId: number): Promise<LessonQaBundle>`
- `streamLessonQaMessage(skillId, content, handlers, { debug?, signal? })`
- `clearLessonQa(skillId: number): Promise<void>`
- Component props: `{ skillId: number; lessonTitle?: string }`

- [x] **Step 1: Implement `lib/lesson-qa.ts`** mimicking `lib/tutor.ts` authFetch + types (`suggested_prompts`, `meta.sources`).

- [x] **Step 2: Implement panel UI**
  - Collapsed: button “Hỏi về bài học”
  - Expanded: message list, cite line under assistant when `meta.sources?.length`, chips when `userMessageCount < 1`, input, optional debug toggle showing `route`
  - Chip click → `streamLessonQaMessage(skillId, chipText, ...)`
  - Match practice page colors (`#2F3437`, `#787774`, `#EAEAEA`) — no new design system

- [x] **Step 3: Typecheck / lint as available**

Run: `cd frontend/my-app && npx tsc --noEmit` (or project’s usual check)

- [x] **Step 4: Stage**

---

### Task 8: Mount on practice page + docs pointer

**Files:**
- Modify: `frontend/my-app/src/app/dashboard/practice/[skillId]/page.tsx`
- Modify: `docs/superpowers/specs/2026-08-05-lesson-qa-rag-design.md` — set **Plan:** path to this file

**Placement:**
- Below the learn/practice main content (or inside `LessonContentWindow` under `LessonMiniUnit` when `phase === "learn"`). Prefer: render `LessonQaPanel` **inside** the lesson window under `LessonMiniUnit` so chat is “under the lesson”; also show on practice phase with same `skillId` if learner wants to ask while drilling — **spec says under LessonMiniUnit**; implement under mini-unit in learn phase first. If practice-only phase has no mini-unit, mount a second instance below practice header with same skillId.

Recommended minimal mount:

```tsx
{phase === "learn" && lessonMeta?.lesson && !completingLesson ? (
  <>
    <LessonMiniUnit ... />
    <LessonQaPanel skillId={skillId} lessonTitle={lessonMeta.lesson.title} />
  </>
) : null}
```

- [x] **Step 1: Mount panel**

- [x] **Step 2: Update spec Plan field** to `docs/superpowers/plans/2026-08-05-lesson-qa-rag.md`

- [x] **Step 3: Stage all remaining files**

---

## Spec coverage

| Spec item | Task |
|-----------|------|
| Panel collapsible under lesson | 7–8 |
| query → retrieve → LLM | 6 |
| Scope skill units via tutor_rag | 6 |
| Persist user+skill | 3, 5 |
| Q&A prompt (not role-play) | 4 |
| CEFR from profile | 4, 6 |
| Cite `meta.sources` | 4, 6, 7 |
| Suggested chips 3–5 from skill/pack | 2, 5, 7 |
| `should_retrieve` ≠ needs_rag | 1, 6 |
| Off-topic no retrieve | 6 |
| Redis cache prefix | 6 |
| Debug SSE | 6–7 |
| DELETE clear history | 5 |
| No Chroma / supermarket / P1 pack corpus | Global |

## Self-review (plan)

- [x] No TBD placeholders for core flow
- [x] Types/names consistent (`should_retrieve`, `build_suggested_prompts`, `iter_qa_turn_sse`)
- [x] Alembic head pinned to `u0v1w2x3y4z5`
- [x] Commit steps are “stage only” per repo/user rule

## Execution handoff

Plan complete and saved to `docs/superpowers/plans/2026-08-05-lesson-qa-rag.md`.

**Two execution options:**

1. **Subagent-Driven (recommended)** — fresh subagent per task, review between tasks  
2. **Inline Execution** — execute tasks in this session with executing-plans checkpoints  

Which approach?
