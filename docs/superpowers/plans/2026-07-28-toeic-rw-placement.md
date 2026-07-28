# TOEIC R+W Placement + Reading Quiz Generation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans`. Steps use checkbox (`- [ ]`) syntax.

**Goal:** Unify on extended `quiz_questions` + `quiz_passages`; AI generates TOEIC Reading (R5/R6/R7) for skill practice; Writing (W1–W3) in same bank; replace adaptive placement with timed R+W assembled from published pool.

**Architecture:** Schema extend quiz bank (no `placement_*` tables). Generator + validators emit `toeic_part` and passage groups. Placement session assembles quotas from published items. Writing graded via `chat_json` (ZIM rubrics). Practice FE renders TOEIC reading parts.

**Tech Stack:** FastAPI, SQLAlchemy, Alembic, pytest, Pydantic, `llm_client.chat_json`, Next.js.

**Spec:** `docs/superpowers/specs/2026-07-28-toeic-rw-placement-design.md` (option **C**)

## Global Constraints

- **No** `placement_passages` / `placement_items` tables.
- Quotas: R5=30, R6=16, R7=54, W1=5, W2=2, W3=1.
- Reading 75m / Writing 58m server timers.
- New AI drafts: `toeic_part` in `r5|r6|r7` (default path); no new `cloze`/`fix_grammar` from generator.
- Placement pool: `status=published` AND `toeic_part IS NOT NULL`.
- Retake 7 days; no auto roadmap assemble; no Listening.
- Orchestrator style: short service + helpers.

---

## File map

| File | Role |
|------|------|
| `backend/app/models/enums.py` | `ToeicPartEnum`; extend `QuizQuestionTypeEnum` with `writing` |
| `backend/app/models/quiz_passage.py` | `QuizPassageDB` |
| `backend/app/models/quiz_question.py` | Add toeic columns |
| `backend/app/models/placement_attempt.py` | Timed form session fields; answers support writing scores |
| `backend/alembic/versions/*_toeic_quiz_bank.py` | Migrations |
| `backend/app/services/cefr_descriptors.py` | TOEIC reading blueprints |
| `backend/app/services/quiz_generation_service.py` | Generate R5/R6/R7 + passages |
| `backend/app/services/writing_generation_service.py` | Optional W1–W3 drafts |
| `backend/app/services/placement/assembler.py` | From quiz bank |
| `backend/app/services/placement/score_map.py` | Scales → CEFR |
| `backend/app/services/placement/writing_grader.py` | ZIM AI grade |
| `backend/app/services/placement/session_service.py` | Replace adaptive |
| `backend/app/services/placement/adaptive_engine.py` | Remove from path |
| `frontend/.../placement/page.tsx` + `lib/placement.ts` | Timed R+W UI |
| Practice quiz UI (skill practice page) | Render `toeic_part` |

---

### Task 1: `quiz_passages` + extend `quiz_questions`

**Files:** enums, `quiz_passage.py`, `quiz_question.py`, `__init__.py`, Alembic

**Produces:** `ToeicPartEnum`, `QuizPassageDB`, columns `toeic_part`, `passage_id`, `prompt_words`, `media_url`, `task_brief`; type `writing`

- [ ] Failing test importing models / enum values
- [ ] Implement + migrate
- [ ] Commit: `feat(quiz): add quiz_passages and TOEIC fields on quiz_questions`

---

### Task 2: Reshape placement attempts for timed R+W

**Files:** `placement_attempt.py`, Alembic, answer columns (`score`, `ai_scores`, `ai_feedback`; nullable `is_correct`)

- [ ] Migration + models (`form_snapshot`, `section`, `section_ends_at`, reading/writing scales)
- [ ] Stop relying on ability/confidence in models
- [ ] Commit: `feat(placement): timed TOEIC session columns on attempts`

---

### Task 3: CEFR blueprints → TOEIC Reading + generator

**Files:** `cefr_descriptors.py`, `quiz_generation_service.py`, `tests/test_quiz_generation_service.py`

**Produces:**

```python
def blueprint_for(book_type, skill_type, count) -> list[dict]:
    # each entry: {toeic_part, type: "mcq", requires_passage: bool, ...}
```

- [ ] Tests: grammar-heavy blueprint prefers `r5`; reading skill includes `r6`/`r7`
- [ ] SYSTEM_PROMPT documents Part 5/6/7; validate `toeic_part`; create `QuizPassageDB` for groups; persist `passage_id`
- [ ] Reject generator output with `cloze`/`fix_grammar`
- [ ] Commit: `feat(quiz): generate TOEIC Reading parts for skills`

---

### Task 4: Writing item generation (same bank)

**Files:** `writing_generation_service.py` (or extend quiz gen), admin hook, tests

- [ ] Generate W2 email passage + task_brief; W3 stem; W1 needs media_url (skip publish without media)
- [ ] Commit: `feat(quiz): generate TOEIC Writing tasks into quiz bank`

---

### Task 5: Assembler + score_map (pure)

**Files:** `placement/quotas.py`, `assembler.py`, `score_map.py`, tests

- [ ] `assemble_form` from items grouped by `toeic_part` / `passage_id`; `BankTooSmallError`
- [ ] `reading_scale`, `writing_scale`, `blend_to_cefr` (min-of-two), `placement_sublevel`
- [ ] Commit: `feat(placement): assemble TOEIC form from quiz bank`

---

### Task 6: Writing grader (ZIM)

**Files:** `writing_grader.py`, tests with mocked `chat_json`

- [ ] Empty → 0; clamp W1≤3, W2≤4, W3≤5; feedback string
- [ ] Commit: `feat(placement): AI grade writing with ZIM rubrics`

---

### Task 7: Session service + API (replace adaptive)

**Files:** `session_service.py`, `onboarding_schema.py`, `onboarding.py`, `__init__.py`, tests

- [ ] start / current / reading-answers / writing-answers / advance / complete / retake-status
- [ ] Old adaptive answers endpoint → 410
- [ ] Profile update + mastery for correct reading with skill_id
- [ ] Commit: `feat(placement): TOEIC R+W session API`

---

### Task 8: Remove adaptive + fix tests

- [ ] `rg adaptive_engine ability_index` clean on runtime path
- [ ] Delete/rewrite adaptive tests
- [ ] Commit: `refactor(placement): remove adaptive placement engine`

---

### Task 9: Seed / publish enough pool (dev)

- [ ] Script or admin publish path ensuring ≥ quotas (can mix generated drafts)
- [ ] Commit: `chore(placement): ensure TOEIC published pool for local`

---

### Task 10: Frontend placement + practice render

**Files:** `lib/placement.ts`, `onboarding/placement/page.tsx`, practice quiz component(s)

- [ ] Timed R→W→result placement
- [ ] Practice: branch UI on `toeic_part` (R5 vs passage sets)
- [ ] Commit: `feat(placement): TOEIC R+W UI and reading practice render`

---

### Task 11: Spec checklist + verify

- [ ] Spec §11 checked; `pytest` placement + quiz generation green
- [ ] Commit: `docs: mark unified TOEIC quiz/placement spec implemented`

---

## Spec coverage

| Spec | Tasks |
|------|-------|
| Unified schema §4 | 1 |
| AI Reading gen §5 | 3 |
| Writing gen §5 | 4 |
| Placement assemble §6 | 5, 7 |
| Writing grade §7 | 6 |
| Practice §8 | 10 |
| API §9 | 7 |
| Remove adaptive | 7, 8 |
| No placement_* tables | 1, all |

## Note vs previous plan

Previous plan created `placement_items` — **superseded**. Use this plan only.
