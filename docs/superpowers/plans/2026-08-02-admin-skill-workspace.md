# Plan triển khai: Admin Skill Workspace

> **Status:** Implemented — drill min committed with Task 2; Task 5 soft-redirect covered by ops-flow Attach UI + Workspace links.

> **For agentic workers:** REQUIRED SUB-SKILL: Dùng `superpowers:subagent-driven-development` (khuyến nghị) hoặc `superpowers:executing-plans`. Checkbox (`- [ ]`) để theo dõi.

**Goal:** Gom Lesson + Skill drill (+ Writing optional) vào một admin workspace theo skill; soft-link legacy; harden nhẹ gen quiz/gate UI.

**Architecture:** Trang `/admin/skills` + `/admin/skills/[skillId]`; API `GET .../workspace` gộp status; tái sử dụng generate/publish hiện có; sidebar Skills primary.

**Tech stack:** FastAPI, Next.js admin (`BookQuizPanel` patterns), pytest, Playwright smoke tùy chọn.

**Spec:** `docs/superpowers/specs/2026-08-02-admin-skill-workspace-design.md`

## Global constraints

- Không xóa TOEIC/Writing API; TOEIC chỉ Advanced collapsed
- Grammar skill_drill cần lesson published (giữ rule backend)
- Không one-click pipeline / bulk multi-skill
- Copy admin English hoặc ngắn gọn như UI hiện tại; lỗi gen hiện rõ
- Commit chỉ khi user yêu cầu

---

## File map

| File | Responsibility |
|------|----------------|
| `backend/app/api/admin_skills.py` (mới) hoặc mở rộng `admin_lessons.py` | `GET /skills/{id}/workspace` |
| `backend/app/services/admin_skill_workspace.py` (mới) | Build payload status |
| `backend/tests/test_admin_skill_workspace.py` | Unit/API can_generate rules |
| `frontend/.../admin/skills/page.tsx` | Skill list |
| `frontend/.../admin/skills/[skillId]/page.tsx` | Workspace page |
| `frontend/.../components/admin/SkillWorkspace.tsx` | Stepper UI |
| `frontend/.../lib/admin-skills.ts` | Client API |
| `frontend/.../components/admin/AdminSidebar.tsx` | Nav |
| `frontend/.../src/app/admin/lessons/page.tsx` | Banner → workspace |
| `frontend/.../src/app/admin/quiz/page.tsx` | Banner → workspace |
| `frontend/.../src/app/admin/page.tsx` | Overview card |
| `frontend/.../lib/routes.ts`, `middleware.ts` | Paths |
| `backend/app/services/quiz_generation_service.py` | Message lỗi ổn định (nhẹ) |
| `frontend/.../lib/admin-quiz.ts` | Đã có `mode`; hiện meta draft |

---

### Task 1: Backend workspace status

**Files:**  
- Tạo: `backend/app/services/admin_skill_workspace.py`  
- Tạo/sửa: router admin + `main` include  
- Test: `backend/tests/test_admin_skill_workspace.py`

- [x] **Bước 1: Test fail** — `can_generate_skill_drill` false khi grammar + lesson draft/none; true khi published + book source.

```python
def test_grammar_blocks_without_published_lesson():
    # pure helper or async with mocks
    assert compute_quiz_gate(skill_type="grammar", lesson_status="draft", has_book_source=True).can_generate is False
    assert compute_quiz_gate(skill_type="grammar", lesson_status="published", has_book_source=True).can_generate is True
```

- [x] **Bước 2: Implement** `get_skill_workspace(db, skill_id)` + `GET` permission `book:manage`.

- [x] **Bước 3: Pytest PASS**

- [x] **Bước 4: Commit nếu được yêu cầu**

---

### Task 2: Harden quiz gen errors (nhẹ)

**Files:** `backend/app/services/quiz_generation_service.py`, test hiện có skill_drill

- [x] **Bước 1:** Chuẩn hóa message:
  - `Grammar skill_drill requires a published lesson with targets/form.`
  - `Skill-drill alignment too low (...)`
  - `Skill doesn't have book source — sync book first.`
- [x] **Bước 2:** Đảm bảo admin API trả 400 `detail` đúng string (không 500).
- [x] **Bước 3:** Test assert substring message khi mock thiếu lesson.

---

### Task 3: FE lib + skill list

**Files:**  
- `frontend/my-app/lib/admin-skills.ts`  
- `frontend/my-app/src/app/admin/skills/page.tsx`  
- routes / middleware / sidebar

- [x] **Bước 1:** `fetchSkillWorkspace(skillId)`, reuse `listAdminLessonSkills` cho list.
- [x] **Bước 2:** Page list: CEFR filter (reuse query), click → `/admin/skills/[id]`.
- [x] **Bước 3:** Sidebar **Skills**; Overview card trỏ Skills.
- [x] **Bước 4:** Thủ công: login admin → thấy Skills.

---

### Task 4: SkillWorkspace UI (Lesson + Drill + Writing)

**Files:**  
- `components/admin/SkillWorkspace.tsx`  
- `src/app/admin/skills/[skillId]/page.tsx`

- [x] **Bước 1:** Load workspace; render 3 steps + badges.
- [x] **Bước 2:** Lesson actions = `generateAdminLesson` / `publishAdminLesson` / `getAdminLesson` + `LessonContentPreview`.
- [x] **Bước 3:** Drill: disable nếu `!can_generate_skill_drill` + hiện `block_reason`; else `generateSkillQuiz(id, count, "skill_drill")`.
- [x] **Bước 4:** List drafts **filter skillId** (từ `listBookQuestions(bookId)` nếu có book, hoặc endpoint list-by-skill nếu cần thêm — ưu tiên: nếu chưa có list-by-skill, thêm `GET /admin/quiz/skills/{id}/questions?status_filter=draft` tối thiểu trong task này).
- [x] **Bước 5:** Draft row hiện `task_brief.mode` / `item_kind`.
- [x] **Bước 6:** Publish selected qua `publishQuestions`.
- [x] **Bước 7:** Writing optional + Advanced TOEIC collapsed.

**Nếu thiếu list questions theo skill:** thêm API nhỏ:

`GET /api/v1/admin/quiz/skills/{skill_id}/questions?status_filter=draft|published`

---

### Task 5: Soft-redirect legacy Lessons & Quiz

> Note: `/admin/lessons` removed by ops-flow; Attach page + BookQuizPanel Workspace links satisfy soft-redirect.

**Files:** `admin/lessons/page.tsx`, `admin/quiz/page.tsx`

- [x] **Bước 1:** Banner đầu trang: “Preferred: Skill workspace” + link `/admin/skills`.
- [x] **Bước 2:** Lessons row: nút “Open workspace” → `/admin/skills/{id}`.
- [x] **Bước 3:** Quiz: giữ attach/sync; trên mỗi skill row link “Workspace”.

---

### Task 6: Verify

- [x] **Bước 1:** Pytest workspace + quiz gate.
- [x] **Bước 2:** Playwright (admin): Skills → skill grammar → nếu lesson draft thì drill disabled → Publish lesson → Generate drill → thấy draft `skill_drill` → Publish.
- [x] **Bước 3:** Cập nhật status spec → Accepted khi user sign-off.
- [x] **Bước 4:** README admin flow 5 dòng (Skills workspace).

---

## Spec coverage

| Spec | Task |
|------|------|
| Workspace theo skill | 3–4 |
| Gate UI grammar | 1, 4 |
| Draft meta mode/item_kind | 4 |
| Soft-redirect | 5 |
| Harden errors | 2 |
| GET workspace | 1 |
| Writing / TOEIC advanced | 4 |

## Placeholder scan

Không TBD. One-click / bulk / archive TOEIC = ngoài scope (ghi trong spec).
