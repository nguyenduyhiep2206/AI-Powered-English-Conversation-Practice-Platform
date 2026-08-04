# Tutor RAG + Hybrid Memory Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans. Steps use checkbox (`- [ ]`) syntax.

**Goal:** Topic catalog (Promova-like) + off-topic soft steering + optional RAG over `book_chunks` + windowed memory + Redis retrieval cache + debug UI — with ≥50% token cut vs full-context baseline on a fixture.

**Architecture:** Catalog lists scenarios → START with `scenario_id`; roadmap still can pass `roadmap_step_id`. Turn pipeline: off-topic gate → optional RAG → memory window → SSE. Redis caches retrieval only.

**Tech Stack:** FastAPI, Mongo, Voyage, Redis, tutor SSE, Next.js.

**Spec:** `docs/superpowers/specs/2026-08-04-tutor-rag-hybrid-memory-design.md` + updates in `2026-08-04-ai-tutor-text-roleplay-design.md`

## Global Constraints

- **Do not commit** unless the user explicitly asks to commit (stage files only otherwise)
- `TUTOR_RAG_ENABLED=false` → no retrieve
- Off-topic (news/gold/world facts) → no RAG, in-character redirect
- Catalog-only sessions: RAG off unless `TUTOR_RAG_CATALOG_LEVEL_FALLBACK=true` (default false)
- Corpus scoped by `target_skill_ids` when present
- Voyage + Mongo (not OpenAI/Chroma)
- Debug event only when `debug=true`
- Token hybrid ≤ 0.5 × baseline on fixture

---

## File map

| File | Responsibility |
|------|----------------|
| `config.py` | RAG/memory/cache flags |
| `tutor_rag.py` | `is_off_topic`, `needs_rag`, cosine, retrieve |
| `tutor_memory.py` | Window + token estimate |
| `tutor_rag_cache.py` | Redis |
| `tutor_prompt.py` | Retrieved block + stronger off-topic rules |
| `tutor_service.py` | Start by scenario_id \| roadmap_step_id; wire turn |
| `api/tutor.py` | `GET /scenarios`, start body xor, debug |
| `frontend/.../tutor/page.tsx` | **Catalog** cards |
| `frontend/.../tutor/[sessionId]/page.tsx` | Chat + debug |
| tests | rag, memory, cache, off_topic, catalog start, token budget |

---

### Task 0: Off-topic + prompt hardening (no RAG yet)

**Files:** `tutor_prompt.py`, `tutor_rag.py` (`is_off_topic`), tests, wire `meta.off_topic`

- [x] Heuristic + prompt examples (gold price → redirect)
- [x] Unit tests for `is_off_topic`
- [x] Stage only (no commit unless asked)

---

### Task 1: Config + retrieve/memory pure helpers

- [x] Cosine, top-k, window, estimate_tokens + tests

---

### Task 2: Scope load + embed retrieve

- [x] Skip retrieve when `target_skill_ids` empty (unless fallback flag)

---

### Task 3: Redis cache (retrieval only)

- [x] Redis get/set keyed by normalized query + skills

---

### Task 4: Wire service + API debug + start xor

- [x] `GET /scenarios`
- [x] `POST /sessions` accepts `scenario_id` **or** `roadmap_step_id`
- [x] Turn: off_topic → rag → roleplay routes
- [x] Token budget test

---

### Task 5: Frontend catalog + debug

- [x] `/ai-tutor` card grid + START
- [x] Nav link
- [x] Chat debug panel shows `route`

---

### Task 6: Docs / README lab mapping

- [x] Spec Accepted; **no commit until user asks**

---

## Spec coverage

| Item | Task |
|------|------|
| Off-topic policy | 0, 4 |
| Topic catalog UX | 4–5 |
| RAG + memory + cache | 1–4 |
| Debug | 4–5 |
| Token &lt; 50% | 4 |

## Execution handoff

Wait for user review. When implementing: **never git commit** until user says commit.
