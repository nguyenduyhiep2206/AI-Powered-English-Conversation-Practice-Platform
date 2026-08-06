# Design: Admin delete published skill questions

**Date:** 2026-08-06  
**Status:** Approved  
**Surface:** `/admin/skills/[skillId]` (`SkillWorkspace`)  
**Depends on:** Existing admin quiz APIs (`admin_quiz.py`, `lib/admin-quiz.ts`)  
**Out of scope:** Draft delete, unpublish/re-draft, lesson pack delete, learner-facing practice UI  

---

## 1. Problem

Admins can generate and publish skill-drill / writing questions in the skill workspace, but cannot remove bad published items. Incorrect or obsolete published questions stay in the practice bank until manual DB cleanup.

---

## 2. Goals / Non-goals

### Goals

1. Hard-delete selected **published** quiz questions from Admin Skill workspace.
2. Support both **Skill drill** and **Writing** Published tabs.
3. Bulk select UX mirroring existing Publish flow (checkbox + Select all + action button).
4. Confirm before destructive delete; refresh counts/list after success.

### Non-goals

- Soft-delete / archive / unpublish.
- Per-row delete-only UX (no bulk).
- Deleting drafts from this feature (may add later independently).
- Orphan passage cleanup beyond a simple “delete if no remaining questions reference it” optional nicety — passages shared across questions must stay.

---

## 3. Decisions (locked)

| Topic | Decision |
|-------|----------|
| Semantics | Hard delete rows in `quiz_questions` |
| Scope | Published tab only (drill + writing) |
| UX | Checkbox selection + `Delete (N)` + browser `confirm` |
| API shape | Bulk `POST /api/v1/admin/quiz/questions/delete` with `{ question_ids }` (mirrors publish) |
| Auth | Same as publish: `book:manage` |
| Status guard | Only delete when `status == published`; skip others and report counts |
| Placement FKs | Rely on existing DB: answers `ON DELETE CASCADE`, `current_question_id` `ON DELETE SET NULL` |
| Passages | Do not delete `quiz_passages` in v1 (avoid breaking multi-question passages) |

---

## 4. Backend

### Endpoint

`POST /api/v1/admin/quiz/questions/delete`  
Permission: `book:manage`  
Body: `{ "question_ids": number[] }` (reuse or mirror `PublishQuizRequest` shape)

### Behavior

1. Load questions by id.
2. For each row with `status == published`: hard-delete.
3. Skip missing ids and non-published rows.
4. Commit once.
5. Response: `{ data: { deleted: number, skipped: number } }`

### Errors

- Empty `question_ids` → `{ deleted: 0, skipped: 0 }` (same style as publish empty).
- Unauthorized → existing permission dep (403).

---

## 5. Frontend

### `lib/admin-quiz.ts`

Add `deleteQuestions(questionIds: number[]): Promise<{ deleted: number; skipped: number }>`.

### `SkillWorkspace.tsx`

On **Published** tab for drill and writing:

- Show checkboxes (same as Draft).
- Show **Select all** when list non-empty.
- Show **Delete (N)** when selection non-empty; disable while `busy`.
- On click: `confirm(\`Delete ${n} published question(s)? This cannot be undone.\`)` then call API, set status toast, `refresh()`.

Draft tab behavior unchanged (Publish only).

---

## 6. Testing

- Backend: delete published ids → gone from list; draft ids skipped; mixed batch counts correct; permission required.
- Frontend: manual smoke on skill workspace Published tabs (drill + writing).

---

## 7. Implementation notes

- Prefer one bulk endpoint over N `DELETE /questions/{id}` calls.
- Keep UI chrome consistent with existing ghost / size=`sm` buttons; use a clear destructive label (`Delete`) without introducing a new design system pattern.
