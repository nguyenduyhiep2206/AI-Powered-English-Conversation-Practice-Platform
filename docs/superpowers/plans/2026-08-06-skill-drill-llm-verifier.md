# Skill-drill LLM Verifier — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** After structural skill-drill validation, LLM-verify `spot_error` (and `fix_grammar`) so grammatically correct “error” items never persist as drafts.

**Architecture:** New `skill_drill_verifier.py` batches items into one `chat_json` call; `_request_skill_drill_items` keeps rule validation + align, then filters via verifier. Fail-closed for verify-eligible kinds.

**Tech Stack:** Python, existing `chat_json`, pytest + unittest.mock

**Spec:** `docs/superpowers/specs/2026-08-06-skill-drill-llm-verifier-design.md`

## Global Constraints

- Do **not** remove existing structural validators / align / habit-contrast regex.
- V1 verifies only `spot_error` and `fix_grammar`.
- Flag `SKILL_DRILL_LLM_VERIFY` default true; when false, skip verifier (dev offline).
- No new dependencies. Do not commit unless user asks.

---

### Task 1: Module `skill_drill_verifier.py` + unit tests (mock)

**Files:**
- Create: `backend/app/services/skill_drill_verifier.py`
- Create: `backend/tests/test_skill_drill_verifier.py`
- Modify: `backend/app/core/config.py` (optional bool)

- [x] Add `SKILL_DRILL_LLM_VERIFY: bool = True` (env-friendly) on settings
- [x] Implement `kinds_needing_verify`, `verify_skill_drill_items`, parse results fail-closed
- [x] Tests: reject bad contrast; accept real error; non-verify kinds untouched; omit index = fail; flag off = passthrough

### Task 2: Wire into gen pipeline

**Files:**
- Modify: `backend/app/services/quiz_generation_service.py`
- Modify: `backend/tests/test_quiz_generation_skill_drill.py` (mock verify if needed)

- [x] After `validate_skill_drill_questions` (+ align check), call verifier with skill title/cefr
- [x] Mark `task_brief["verified"]=True` on verified-pass items
- [x] Ensure yield still uses `max(2, count//2)` floor on final list

### Task 3: Spec status + smoke

- [x] Set spec status to Implemented (partial) when tests green
- [x] Run: `pytest tests/test_skill_drill_verifier.py tests/test_skill_drill_validate.py tests/test_quiz_generation_skill_drill.py -q`
