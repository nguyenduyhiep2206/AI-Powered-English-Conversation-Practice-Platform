# AI Tutor Text Role-play (SSE) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship skill-grounded text role-play from roadmap steps with SSE-streamed assistant replies, gentle corrections, and soft end-session signals (no hard mastery writes).

**Architecture:** New `tutor_sessions` / `tutor_messages` tables; FastAPI `/api/v1/tutor` with SSE on send-message; one streamed LLM turn that emits reply tokens then a `___META___` JSON trailer; sync JSON for `/end`. Frontend CTA on in-progress week → `/ai-tutor/[sessionId]` with token rendering.

**Tech Stack:** FastAPI, SQLAlchemy async, Alembic, LangChain `ChatOpenAI` stream, Next.js App Router, pytest, `EventSource`-style `fetch` + `ReadableStream` on FE.

**Spec:** `docs/superpowers/specs/2026-08-04-ai-tutor-text-roleplay-design.md`

## Global Constraints

- Entry only from roadmap step with user progress `in_progress`
- Max 3 `target_skill_ids` copied at session start from `roadmap_step_skills`
- No writes to `user_skill_mastery` from tutor code paths
- Soft signals’ `skill_id` must ⊆ session `target_skill_ids`
- SSE Must on `POST .../messages`; `/end` is sync JSON
- Do not restore dropped `chat_*` / vocab / gamification tables
- Copy UI strings follow existing EnglishFlow learner English where other surfaces are English; match neighbor components
- Head before migration: expect `s8t9u0v1w2x3` → new revision e.g. `t9u0v1w2x3y4`
- Commit conventional (`feat:`, `test:`, `fix:`) only when session allows commits
- Public services stay orchestrator-style (`.cursor/rules/service-orchestrator.mdc`)

---

## File map

| File | Responsibility |
|------|----------------|
| `backend/alembic/versions/t9u0v1w2x3y4_tutor_sessions.py` | Create tutor tables + enums |
| `backend/app/models/enums.py` | `TutorSessionStatus`, `TutorMessageRole` |
| `backend/app/models/tutor.py` | ORM `TutorSessionDB`, `TutorMessageDB` |
| `backend/app/models/__init__.py` | Export models |
| `backend/app/core/config.py` | `TUTOR_MAX_USER_TURNS`, `TUTOR_MAX_MESSAGE_CHARS` |
| `backend/app/services/llm_client.py` | Add `chat_stream_text()` async generator |
| `backend/app/services/tutor_prompt.py` | Build system/user prompts + parse meta trailer |
| `backend/app/services/tutor_service.py` | start / get / stream_turn / end orchestrators |
| `backend/app/schemas/tutor_schema.py` | Request/response / summary / SSE payload types |
| `backend/app/api/tutor.py` | Router + `StreamingResponse` SSE |
| `backend/main.py` | Include router |
| `backend/tests/test_tutor_prompt.py` | Trailer parse + soft-signal filter |
| `backend/tests/test_tutor_service.py` | Start/end/mastery invariant (mocked LLM) |
| `backend/tests/test_tutor_api_sse.py` | SSE event order (mocked service/LLM) |
| `frontend/my-app/lib/tutor.ts` | Types + `startTutorSession`, `streamTutorMessage`, `endTutorSession` |
| `frontend/my-app/src/app/ai-tutor/[sessionId]/page.tsx` | Chat UI |
| `frontend/my-app/components/roadmap/WeekNode.tsx` (and/or dashboard) | CTA Practice speaking |
| `docs/REQUIREMENTS.md` | Narrow Must for tutor; keep Won't for voice/vocab/streak |
| Spec frontmatter | Status → Accepted; link this plan |

---

### Task 1: Enums + models + migration

**Files:**
- Create: `backend/app/models/tutor.py`
- Modify: `backend/app/models/enums.py`
- Modify: `backend/app/models/__init__.py`
- Create: `backend/alembic/versions/t9u0v1w2x3y4_tutor_sessions.py`
- Test: `backend/tests/test_tutor_models.py`

**Interfaces:**
- Produces: `TutorSessionDB`, `TutorMessageDB`, enums `tutor_session_status_enum`, `tutor_message_role_enum`

- [ ] **Step 1: Add enums**

```python
# in enums.py — after placement enums
class TutorSessionStatusEnum(str, enum.Enum):
    active = "active"
    completed = "completed"
    abandoned = "abandoned"

class TutorMessageRoleEnum(str, enum.Enum):
    user = "user"
    assistant = "assistant"

tutor_session_status_enum = SAEnum(
    TutorSessionStatusEnum, name="tutor_session_status_enum", create_type=True
)
tutor_message_role_enum = SAEnum(
    TutorMessageRoleEnum, name="tutor_message_role_enum", create_type=True
)
```

- [ ] **Step 2: Write `tutor.py` models**

```python
class TutorSessionDB(Base):
    __tablename__ = "tutor_sessions"
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    roadmap_step_id = Column(BigInteger, ForeignKey("roadmap_steps.id", ondelete="RESTRICT"), nullable=False, index=True)
    scenario_id = Column(BigInteger, ForeignKey("scenarios.id", ondelete="RESTRICT"), nullable=False)
    status = Column(tutor_session_status_enum, nullable=False)
    target_skill_ids = Column(JSON, nullable=False)  # list[int]
    message_count = Column(SmallInteger, nullable=False, default=0)  # user turns
    summary = Column(JSON, nullable=True)
    started_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())
    ended_at = Column(TIMESTAMP(timezone=True), nullable=True)
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

class TutorMessageDB(Base):
    __tablename__ = "tutor_messages"
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    session_id = Column(BigInteger, ForeignKey("tutor_sessions.id", ondelete="CASCADE"), nullable=False, index=True)
    role = Column(tutor_message_role_enum, nullable=False)
    content = Column(TEXT, nullable=False)
    meta = Column(JSON, nullable=True)
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())
```

- [ ] **Step 3: Migration** — create tables + indexes; `down_revision = "s8t9u0v1w2x3"` (verify `alembic heads` first)

- [ ] **Step 4: Failing/passing model smoke test**

```python
# backend/tests/test_tutor_models.py
from app.models.tutor import TutorSessionDB, TutorMessageDB

def test_tutor_table_names():
    assert TutorSessionDB.__tablename__ == "tutor_sessions"
    assert TutorMessageDB.__tablename__ == "tutor_messages"
```

Run: `cd backend && .venv/bin/pytest tests/test_tutor_models.py -v`  
Expected: PASS

- [ ] **Step 5: Commit** (if allowed)

```bash
git add backend/app/models/enums.py backend/app/models/tutor.py backend/app/models/__init__.py \
  backend/alembic/versions/t9u0v1w2x3y4_tutor_sessions.py backend/tests/test_tutor_models.py
git commit -m "feat(tutor): add tutor_sessions and tutor_messages schema"
```

---

### Task 2: Config + prompt helpers + stream LLM

**Files:**
- Modify: `backend/app/core/config.py`
- Create: `backend/app/services/tutor_prompt.py`
- Modify: `backend/app/services/llm_client.py`
- Test: `backend/tests/test_tutor_prompt.py`, extend `backend/tests/test_llm_client.py` if present else new `test_llm_stream.py`

**Interfaces:**
- Produces:
  - `META_DELIMITER = "\n___META___\n"`
  - `build_turn_system_prompt(...) -> str`
  - `build_turn_user_payload(...) -> str`
  - `split_reply_and_meta(full_text: str) -> tuple[str, dict]`
  - `filter_soft_signals(signals, allowed_ids: set[int]) -> list[dict]`
  - `async def chat_stream_text(*, system: str, user: str) -> AsyncIterator[str]` (token deltas)

- [ ] **Step 1: Config**

```python
TUTOR_MAX_USER_TURNS: int = 20
TUTOR_MAX_MESSAGE_CHARS: int = 2000
```

- [ ] **Step 2: Write failing tests for trailer parse**

```python
# backend/tests/test_tutor_prompt.py
from app.services.tutor_prompt import split_reply_and_meta, filter_soft_signals, META_DELIMITER

def test_split_reply_and_meta_happy():
    raw = "Hello there!" + META_DELIMITER + '{"correction":null,"hint":null,"goal_progress":"none"}'
    reply, meta = split_reply_and_meta(raw)
    assert reply == "Hello there!"
    assert meta["goal_progress"] == "none"

def test_split_without_meta_defaults():
    reply, meta = split_reply_and_meta("Only text")
    assert reply == "Only text"
    assert meta["correction"] is None

def test_filter_soft_signals_drops_unknown_skills():
    out = filter_soft_signals(
        [{"skill_id": 1, "signal": "needs_practice", "note": "x"},
         {"skill_id": 99, "signal": "needs_practice", "note": "y"}],
        {1},
    )
    assert out == [{"skill_id": 1, "signal": "needs_practice", "note": "x"}]
```

Run: `cd backend && .venv/bin/pytest tests/test_tutor_prompt.py -v`  
Expected: FAIL (import error)

- [ ] **Step 3: Implement `tutor_prompt.py`**

```python
META_DELIMITER = "\n___META___\n"
_DEFAULT_META = {"correction": None, "hint": None, "goal_progress": "none"}

def split_reply_and_meta(full_text: str) -> tuple[str, dict]:
    if META_DELIMITER not in full_text:
        return full_text.strip(), dict(_DEFAULT_META)
    reply, _, rest = full_text.partition(META_DELIMITER)
    try:
        meta = json.loads(rest.strip())
    except json.JSONDecodeError:
        meta = dict(_DEFAULT_META)
    for k, v in _DEFAULT_META.items():
        meta.setdefault(k, v)
    return reply.strip(), meta

def filter_soft_signals(signals: list | None, allowed_ids: set[int]) -> list[dict]:
    out = []
    for s in signals or []:
        sid = int(s.get("skill_id", -1))
        if sid in allowed_ids:
            out.append({
                "skill_id": sid,
                "signal": s.get("signal") or "needs_practice",
                "note": (s.get("note") or "")[:240],
            })
    return out
```

Also implement `build_turn_system_prompt` / `build_end_prompts` embedding CEFR, roles, goal, skill titles, and instructing the model to end with exact delimiter + JSON meta schema.

- [ ] **Step 4: `chat_stream_text`**

```python
async def chat_stream_text(*, system: str, user: str):
    """Yield text chunks from ChatOpenAI.astream."""
    if not settings.OPENAI_API_KEY:
        raise RuntimeError("OPENAI_API_KEY chưa được cấu hình")
    from langchain_core.messages import HumanMessage, SystemMessage
    from langchain_openai import ChatOpenAI
    kwargs = {
        "model": settings.OPENAI_MODEL,
        "api_key": settings.OPENAI_API_KEY,
        "temperature": 0.5,
        "streaming": True,
    }
    if settings.OPENAI_BASE_URL:
        kwargs["base_url"] = settings.OPENAI_BASE_URL
    llm = ChatOpenAI(**kwargs)
    async for chunk in llm.astream([SystemMessage(content=system), HumanMessage(content=user)]):
        text = chunk.content if isinstance(chunk.content, str) else str(chunk.content or "")
        if text:
            yield text
```

Unit-test with monkeypatched fake async iterator (no network).

- [ ] **Step 5: Commit**

```bash
git commit -m "feat(tutor): add stream LLM helper and meta trailer parsing"
```

---

### Task 3: Tutor service (start / get / stream_turn / end)

**Files:**
- Create: `backend/app/services/tutor_service.py`
- Create: `backend/app/schemas/tutor_schema.py`
- Test: `backend/tests/test_tutor_service.py`

**Interfaces:**
- Consumes: models, `UserProgressDB`, `RoadmapStepDB`, `ScenarioDB`, `RoadmapStepSkillDB`, `LearningSkillDB`, prompt + stream helpers
- Produces:
  - `async def start_session(db, user_id: int, roadmap_step_id: int) -> TutorSessionDB`
  - `async def get_session_for_user(db, user_id: int, session_id: int) -> TutorSessionDB`
  - `async def iter_turn_sse(db, user_id: int, session_id: int, content: str) -> AsyncIterator[tuple[str, dict]]`  
    yields `("user_message"|"token"|"meta"|"assistant_message"|"error"|"done", payload)`
  - `async def end_session(db, user_id: int, session_id: int) -> dict` summary
  - Assert helper used in tests: no `UserSkillMasteryDB` mutations

- [ ] **Step 1: Failing tests**

```python
@pytest.mark.asyncio
async def test_start_rejects_locked_step(db_session, user_with_locked_step):
    with pytest.raises(ValueError, match="in_progress"):
        await start_session(db_session, user_with_locked_step.id, step_id)

@pytest.mark.asyncio
async def test_end_filters_unknown_skill_ids(monkeypatch, db_session, active_tutor_session):
    async def fake_chat_json(system, user):
        return {
            "went_well": ["ok"],
            "fix_next": ["articles"],
            "soft_skill_signals": [
                {"skill_id": active_tutor_session.target_skill_ids[0], "signal": "needs_practice", "note": "a"},
                {"skill_id": 999999, "signal": "needs_practice", "note": "bad"},
            ],
        }
    monkeypatch.setattr("app.services.tutor_service.chat_json", fake_chat_json)
    summary = await end_session(db_session, user_id, active_tutor_session.id)
    assert all(s["skill_id"] != 999999 for s in summary["soft_skill_signals"])

@pytest.mark.asyncio
async def test_end_does_not_touch_mastery(monkeypatch, db_session, active_tutor_session):
    # snapshot mastery rows; end_session; assert unchanged
    ...
```

Use existing test DB fixtures patterns from `test_roadmap_assembler_service.py` / `conftest` if available; otherwise lightweight in-memory setup matching project norms.

- [ ] **Step 2: Implement orchestrators**

`start_session`:
1. Load progress for `(user_id, roadmap_step_id)` — must be `in_progress`
2. Load step + scenario
3. Load up to 3 skill ids for step ordered by existing join
4. Insert session + optional opener assistant message (static template: greet in role + state goal — **no LLM** for opener to keep start fast)
5. Commit; return session

`iter_turn_sse`:
1. Validate session owner + `active`
2. Validate `len(content)` and `message_count < TUTOR_MAX_USER_TURNS`
3. Persist user message; `yield ("user_message", {...})`; commit
4. Build prompts from scenario + transcript tail (last N messages)
5. Stream `chat_stream_text`; accumulate; for tokens **before** delimiter appears in buffer, yield `("token", {"text": visible_delta})` — use a small buffer so delimiter never leaks to FE
6. `split_reply_and_meta(full)`; yield `meta`; persist assistant; yield `assistant_message`; bump `message_count`; yield `done`
7. On exception after user saved: yield `error`; do not raise past generator without event

`end_session`:
1. Validate active
2. `chat_json` summary prompt; filter signals; set status completed + ended_at + summary
3. Never import/update mastery models except read-only if needed

- [ ] **Step 3: Run tests**

Run: `cd backend && .venv/bin/pytest tests/test_tutor_service.py -v`  
Expected: PASS

- [ ] **Step 4: Commit**

```bash
git commit -m "feat(tutor): add tutor session service with streamed turns"
```

---

### Task 4: API router SSE + wire `main.py`

**Files:**
- Create: `backend/app/api/tutor.py`
- Modify: `backend/main.py`
- Test: `backend/tests/test_tutor_api_sse.py`

**Interfaces:**
- `POST /api/v1/tutor/sessions` → `{ data: session_dto }`
- `GET /api/v1/tutor/sessions/{id}` → session + messages
- `POST /api/v1/tutor/sessions/{id}/messages` → `StreamingResponse` `text/event-stream`
- `POST /api/v1/tutor/sessions/{id}/end` → `{ data: summary }`

- [ ] **Step 1: SSE formatter**

```python
def _sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"
```

- [ ] **Step 2: Messages endpoint**

```python
@router.post("/sessions/{session_id}/messages")
async def post_message(...):
    async def gen():
        async for event, payload in iter_turn_sse(db, user_id, session_id, body.content):
            yield _sse(event, payload)
    return StreamingResponse(gen(), media_type="text/event-stream")
```

Map `ValueError` → 400, missing → 404, wrong owner → 403 before streaming starts.

- [ ] **Step 3: API test with httpx / TestClient**

Mock `iter_turn_sse` to yield a fixed sequence; assert response text contains `event: token` then `event: meta` then `event: done`.

- [ ] **Step 4: Commit**

```bash
git commit -m "feat(tutor): expose tutor REST and SSE message endpoints"
```

---

### Task 5: Frontend client + tutor page + roadmap CTA

**Files:**
- Create: `frontend/my-app/lib/tutor.ts`
- Create: `frontend/my-app/src/app/ai-tutor/[sessionId]/page.tsx`
- Modify: `frontend/my-app/components/roadmap/WeekNode.tsx` (and/or `RoadmapPath.tsx` / dashboard)
- Modify: `frontend/my-app/lib/routes.ts` if routes helper exists

**Interfaces:**
- `startTutorSession(roadmapStepId: number): Promise<TutorSession>`
- `getTutorSession(id: number): Promise<TutorSessionDetail>`
- `streamTutorMessage(sessionId, content, handlers): Promise<void>` using `fetch` + `getReader()`, parse SSE frames
- `endTutorSession(id): Promise<TutorSummary>`

- [ ] **Step 1: `lib/tutor.ts` SSE parser**

Parse lines; on `event:` + `data:`; call `onToken`, `onMeta`, `onDone`, `onError`. Use credentials/cookies same as `lib/api.ts`.

- [ ] **Step 2: Page UI**

- Load session on mount
- Message list; local streaming buffer for in-flight assistant bubble
- Form submit → `streamTutorMessage`
- End button → modal with `went_well` / `fix_next` / optional link to weak skills (`/dashboard` section or existing weak-skills UI)

- [ ] **Step 3: CTA**

On week/step `in_progress`, button “Practice speaking” → `startTutorSession` → `router.push(/ai-tutor/${id})`.

- [ ] **Step 4: Manual smoke**

Run API + FE; start from dashboard; send 1 message; confirm stream + end summary.

- [ ] **Step 5: Commit**

```bash
git commit -m "feat(tutor): add learner tutor chat UI with SSE streaming"
```

---

### Task 6: SRS + spec status

**Files:**
- Modify: `docs/REQUIREMENTS.md` (Won't → narrow Must for text tutor role-play; voice/vocab/streak stay Won't)
- Modify: `docs/superpowers/specs/2026-08-04-ai-tutor-text-roleplay-design.md` status → Accepted; Plan link → this file

- [ ] **Step 1: Patch SRS out-of-scope / MoSCoW rows** to allow `/api/v1/tutor` only
- [ ] **Step 2: Commit**

```bash
git commit -m "docs: accept AI tutor P0 and update SRS scope"
```

---

## Spec coverage checklist

| Spec item | Task |
|-----------|------|
| Tables `tutor_*` | T1 |
| Entry from in_progress step | T3 + T5 |
| Target skills ≤3 snapshot | T3 |
| SSE events order | T3–T4 |
| Meta correction/hint/goal_progress | T2–T3 |
| End summary + soft signal filter | T3 |
| No mastery writes | T3 tests |
| FE stream + CTA | T5 |
| No voice / no chat_* restore | Global + T1 |
| Config limits | T2–T3 |
| Alembic after `s8t9u0v1w2x3` | T1 |
| SRS update | T6 |

## Placeholder / consistency self-review

- Concrete revision id `t9u0v1w2x3y4` — re-check `alembic heads` at execute time
- Streaming strategy locked: single completion + `___META___` trailer; buffer so FE never sees delimiter
- `/end` remains sync `chat_json`
- Types: `goal_progress` ∈ `none|partial|done`; status ∈ `active|completed|abandoned`

---

## Execution handoff

Plan complete and saved to `docs/superpowers/plans/2026-08-04-ai-tutor-text-roleplay.md`.

**Two execution options:**

1. **Subagent-Driven (recommended)** — fresh subagent per task, review between tasks  
2. **Inline Execution** — execute tasks in this session with checkpoints  

Which approach?
