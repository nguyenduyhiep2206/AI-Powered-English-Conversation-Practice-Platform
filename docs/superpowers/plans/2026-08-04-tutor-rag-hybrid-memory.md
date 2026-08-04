# Tutor RAG + Hybrid Memory Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add optional RAG over Mongo `book_chunks` + windowed chat memory + Redis Q-cache + debug SSE/UI to the existing AI Tutor, cutting prompt size vs full-context baseline by ≥50% on a fixed fixture.

**Architecture:** New `tutor_rag` service (route → embed query → filter chunks by skill→unit → cosine Top-K); tutor turn uses memory window + retrieved block; Redis caches grounded Q&A; FE debug panel when `debug=true`.

**Tech Stack:** FastAPI, Mongo book_chunks, Voyage `embed_texts`, Redis, existing tutor SSE, Next.js tutor page, pytest.

**Spec:** `docs/superpowers/specs/2026-08-04-tutor-rag-hybrid-memory-design.md`

## Global Constraints

- Disable path: `TUTOR_RAG_ENABLED=false` restores P0 behavior (no retrieve)
- Corpus only chunks tied to session `target_skill_ids` via `book_skill_sources`
- Embeddings = Voyage (not OpenAI); vector store = Mongo (not Chroma) — document in lab report
- No mastery writes; no supermarket CSV
- SSE `debug` event only when client requests `debug: true`
- Approx tokens = `ceil(chars / 4)`; hybrid ≤ 0.5 × baseline on fixture test
- Commit conventional when allowed; only stage task files

---

## File map

| File | Responsibility |
|------|----------------|
| `backend/app/core/config.py` | `TUTOR_RAG_*`, `TUTOR_MEMORY_MAX_TURNS`, cache TTL |
| `backend/app/services/tutor_rag.py` | Router heuristic, load scope, cosine retrieve, build context block |
| `backend/app/services/tutor_memory.py` | Window transcript; size estimators |
| `backend/app/services/tutor_rag_cache.py` | Redis get/set normalized query cache |
| `backend/app/services/tutor_prompt.py` | Accept `retrieved_context` in system prompt |
| `backend/app/services/tutor_service.py` | Wire hybrid into `_stream_assistant_turn`; emit debug |
| `backend/app/schemas/tutor_schema.py` | `debug` on message body; DebugPayload type |
| `backend/app/api/tutor.py` | Pass debug flag |
| `backend/tests/test_tutor_rag.py` | Cosine, threshold, empty scope, token budget |
| `backend/tests/test_tutor_memory.py` | Windowing |
| `backend/tests/test_tutor_rag_cache.py` | Redis mock hit/miss |
| `frontend/my-app/lib/tutor.ts` | `debug` option + `onDebug` handler |
| `frontend/my-app/src/app/dashboard/tutor/[sessionId]/page.tsx` | Debug toggle + panel |
| Spec status | Accepted after implement |

---

### Task 1: Config + pure retrieve helpers

**Files:**
- Modify: `backend/app/core/config.py`
- Create: `backend/app/services/tutor_rag.py`
- Create: `backend/app/services/tutor_memory.py`
- Test: `backend/tests/test_tutor_rag.py`, `backend/tests/test_tutor_memory.py`

**Interfaces:**
- `needs_rag(text: str) -> bool`
- `cosine(a: list[float], b: list[float]) -> float`
- `select_top_chunks(query_vec, docs, *, top_k, min_score, max_chars) -> list[dict]`
- `format_retrieved_block(chunks) -> str`
- `window_transcript(messages, *, max_turns, keep_first_assistant=True) -> list[dict]`
- `estimate_tokens(text: str) -> int`

- [ ] **Step 1: Failing tests** for cosine, top-k threshold, char cap, needs_rag heuristics, window keeps opener + last N.

- [ ] **Step 2: Implement pure functions** (no Mongo in unit tests — pass fake docs).

- [ ] **Step 3: Pytest green**

```bash
cd backend && PYTHONPATH=. .venv/bin/pytest tests/test_tutor_rag.py tests/test_tutor_memory.py -v
```

- [ ] **Step 4: Commit** `feat(tutor): add RAG retrieve helpers and memory window`

---

### Task 2: Scope load + embed query integration

**Files:**
- Modify: `backend/app/services/tutor_rag.py`
- Test: `backend/tests/test_tutor_rag.py` (mock Mongo + embed)

**Interfaces:**
- `async def resolve_unit_scope(db, skill_ids: list[int]) -> list[tuple[int, str | int]]`  # book_id, unit key
- `async def load_embedded_chunks(scope) -> list[dict]`
- `async def retrieve_for_session(db, *, skill_ids, query: str) -> list[dict]`

- [ ] **Step 1: Tests** with monkeypatched Mongo collection / `embed_texts`.
- [ ] **Step 2: Implement** using existing `get_unit_chunks` patterns or motor query filtering `embed_status=embedded`.
- [ ] **Step 3: Commit** `feat(tutor): retrieve book_chunks for tutor skill scope`

---

### Task 3: Redis cache

**Files:**
- Create: `backend/app/services/tutor_rag_cache.py`
- Test: `backend/tests/test_tutor_rag_cache.py`

**Interfaces:**
- `cache_key(normalized_query: str, skill_ids: list[int]) -> str`
- `async def cache_get(key) -> dict | None`
- `async def cache_set(key, value: dict, ttl: int) -> None`

Value shape: `{ "answer": str | None, "chunks": [...], "meta": {...} }` — for P0 cache **retrieval+optional canned** or full assistant text after turn (prefer cache retrieval result only to avoid stale roleplay tone; **decision: cache retrieval payload only**).

- [ ] **Step 1–3:** TDD with fakeredis or mock redis client used by project.
- [ ] **Step 4: Commit** `feat(tutor): redis cache for tutor RAG retrieval`

---

### Task 4: Wire tutor_service + prompts + API debug

**Files:**
- Modify: `tutor_prompt.py`, `tutor_service.py`, `tutor_schema.py`, `api/tutor.py`
- Test: extend `test_tutor_service.py` with mocked retrieve/cache

**Behavior:**
1. Window transcript before prompt.
2. If RAG enabled and `needs_rag`: retrieve (cache) → inject.
3. If `debug`: yield `("debug", payload)` before `done`.
4. Token budget test: fixture comparing baseline vs hybrid estimators ≥ 50% reduction.

- [ ] **Step 1: Prompt** add section `Retrieved book context:\n{block or "(none)"}`.
- [ ] **Step 2: Service wire-up** keep orchestrator style.
- [ ] **Step 3: API** accept `debug: bool = False` on message body.
- [ ] **Step 4: Tests green**
- [ ] **Step 5: Commit** `feat(tutor): hybrid memory and RAG in streamed turns`

---

### Task 5: Frontend debug mode

**Files:**
- Modify: `frontend/my-app/lib/tutor.ts`
- Modify: tutor page component

- [ ] Toggle Debug → `streamTutorMessage(..., { debug: true, onDebug })`
- [ ] Side panel lists chunks/scores/cache/memory/tokens
- [ ] Commit `feat(tutor): debug panel for RAG and memory context`

---

### Task 6: Docs + lab mapping note

**Files:**
- Spec status → Accepted
- Short section in `backend/README.md` or tutor section: env flags + “lab equivalence table”
- Commit `docs: accept tutor RAG hybrid memory design`

---

## Spec coverage

| Spec item | Task |
|-----------|------|
| needs_rag + retrieve | 1–2 |
| Memory window | 1, 4 |
| Redis cache | 3–4 |
| SSE debug | 4–5 |
| Token &lt; 50% test | 4 |
| FE debug | 5 |
| Config flags | 1, 4 |
| Lab mapping note | 6 |

## Execution handoff

Plan saved to `docs/superpowers/plans/2026-08-04-tutor-rag-hybrid-memory.md`.

**Options:** (1) Subagent-Driven · (2) Inline · (3) Review specs first only
