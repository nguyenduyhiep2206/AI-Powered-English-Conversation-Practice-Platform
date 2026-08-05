# Admin Ops Flow Roles Implementation Plan

> **Status:** Tasks 1–4 (list-only) + docs landing; Task 5 workspace deferred.

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans`. Checkbox (`- [ ]`) để theo dõi.

**Goal:** Làm rõ Books → Attach → Skills; gỡ gen dual-path; badge list; workspace Draft/Published + filter; Re-enrich.

**Architecture:** Mở rộng `list_skills_with_lesson_status` aggregate; FE demote Lessons/Attach gen; SkillWorkspace tabs/filters; nav label Attach.

**Tech Stack:** FastAPI, SQLAlchemy, Next.js admin, pytest.

**Spec:** `docs/superpowers/specs/2026-08-02-admin-ops-flow-roles-design.md`

## Global Constraints

- Path `/admin/quiz` giữ; label **Attach**
- Gen drill/writing UI gỡ khỏi BookQuizPanel (API giữ)
- Lessons: chỉ Workspace link
- Generate count default **6**
- Không N+1 workspace cho list badges

---

### Task 1: Backend list skills badges (TDD)

**Files:** `lesson_service.py` (or list helper), schemas, `test_admin_lessons` / new test

- [x] **Bước 1:** Test fail — response có `quiz_draft_count`, `quiz_published_count`, `has_book_source`
- [x] **Bước 2:** Aggregate trong `list_skills_with_lesson_status`
- [x] **Bước 3:** Pytest PASS

---

### Task 2: FE nav + Lessons + Books + Overview (P0 copy/roles)

**Files:** `AdminSidebar`, `admin/page`, `admin/lessons`, `admin/books`, `admin/quiz/page`

- [x] Sidebar Attach; ẩn Survey/Users; icon Lessons ≠ Skills
- [x] Lessons: bỏ Generate/View/Publish
- [x] Books: Open Attach
- [x] Overview cards roles
- [x] Quiz page title/banner Attach

---

### Task 3: BookQuizPanel — gỡ gen + post-sync + unmapped + enrich (P0/P1/P2)

**Files:** `BookQuizPanel.tsx`, `admin-books.ts` / `admin-quiz.ts`

- [x] Remove Generate drill/Writing buttons + handlers UI
- [x] Post-sync Continue in Skills CTA
- [x] Unmapped copy
- [x] Re-enrich button
- [x] Draft note optional

---

### Task 4: Skills list badges + count=6 + Attach CTAs (P0)

**Files:** `admin-lessons.ts` types, `admin/skills/page`, `admin-skills.ts` labels, `SkillWorkspace` no-book CTA, `admin-quiz.ts` default count

- [x] List badges + Open Attach CTA when no book; generate count default 6
- [ ] SkillWorkspace no-book CTA — deferred (needs skill-aligned + admin-skill-workspace)

---

### Task 5: SkillWorkspace Draft/Published + mode filter (P1)

**Files:** `SkillWorkspace.tsx`, `admin-quiz.ts` listSkillQuestions

- [ ] Deferred until skill-drill + admin-skill-workspace are committed

---

### Task 6: README + verify spec Accepted + verify

- [x] README Books → Attach → Skills
- [x] Spec status Accepted
- [x] Pytest + smoke sanity
- [x] Note Task 4–5 workspace deferral in plan

---
