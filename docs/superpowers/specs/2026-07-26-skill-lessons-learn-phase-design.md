# Design: Skill lessons — Slide Learn (text + ảnh) trước Practice

**Date:** 2026-07-26  
**Updated:** 2026-07-29  
**Status:** **SUPERSEDED** by `docs/superpowers/specs/2026-07-29-skill-lesson-mini-unit-design.md` (mini-unit D: read → notice → check → write → feedback). Slide + image Learn discarded.  
**Plan:** `docs/superpowers/plans/2026-07-26-skill-lessons-learn-phase.md` (also superseded)  
**Scope:** `backend` (models + offline lesson/image pipeline + APIs), `frontend/my-app` (slide Learn → Practice)  
**Depends on:** Skill graph + ZPD roadmap (`2026-07-20-skill-graph-zpd-roadmap-design.md`), quiz per skill  
**Supersedes:** `2026-07-21-roadmap-learning-content-design.md`  
**Research:** Exa — GRR / micro-lessons, bite-size Learn→Practice; A1 meta VI + examples EN  

---

## 1. Problem

Learner vào skill từ roadmap hiện **chỉ làm quiz**. Không có bước dạy (giải thích, ví dụ, minh họa). `learning_skills` chỉ metadata; sách chỉ là nguồn qua `book_skill_sources`.

Mục tiêu: mỗi skill có **một bài dạy dạng slide** (text + ảnh minh họa), gen **offline**; phiên học = **Learn (slides) → Practice (quiz)**; mastery ≥ 0.7 vẫn là gate hoàn thành tuần.

---

## 2. Goals / Non-goals

### Goals

- 1 published lesson / skill — **slide deck** (text + `image_url` minh họa)
- Cùng khung GRR cho mọi `skill_type` (nội dung khác, schema giống)
- FE: Learn rồi Practice trên `/dashboard/practice/[skillId]`
- Learn bắt buộc lần đầu; skip khi đã complete Learn **hoặc** mastery ≥ 0.7
- Track skip bằng `user_lesson_progress`
- Content **offline**: LLM (text) + image model (ảnh) khi **tạo** lesson — serve chỉ đọc
- **Ship Learn cho learner chỉ khi** pipeline text+ảnh offline đã chạy và có lesson `published` đủ chất lượng
- Ngôn ngữ: ví dụ / key phrases **EN**; giải thích meta **VI**
- Complete week **không đổi**: chỉ mastery ≥ 0.7

### Non-goals

- Gen text/ảnh **realtime** khi user mở bài
- Nhiều lesson / skill + random
- Admin editor WYSIWYG phức tạp (MVP: job + review status tối thiểu)
- Đổi ZPD assemble / skill graph / quiz generation
- Spaced repetition; nối scenario vào Learn
- Complete week phụ thuộc “đã Learn”
- Ship Learn text-only / fallback Learn nửa vời cho user (xem §3 ship gate)

---

## 3. Decisions (locked)


| Chủ đề | Quyết định |
|--------|------------|
| Presentation | **Slides** (một slide ≈ một bước GRR), không cuộn dài một trang |
| Ảnh | **LLM/image gen offline** khi tạo lesson; lưu asset/`image_url` |
| Ship gate (**C**) | **Không bật Learn** cho learner đến khi pipeline text + ảnh offline sẵn và lesson publish được |
| Trước khi ship Learn | Practice **giữ quiz-only** như hiện tại |
| Cardinality | 1 lesson / skill |
| Learn gate | Bắt buộc lần đầu; rồi skip (DB progress hoặc mastery ≥ 0.7) |
| Missing published lesson (sau khi feature on) | Vào **thẳng Practice** (không fallback Learn tối thiểu) |
| Language | EN examples/key points; VI meta |
| Complete week | Chỉ mastery ≥ 0.7 |
| Template theo type | 1 schema slide chung; nội dung theo `skill_type` |


---

## 4. Architecture

```text
Offline pipeline (admin/job — không ở serve-time)
  skill + primary book_skill_sources excerpt
    → LLM: slides text (GRR)
    → Image model: 1 ảnh / slide (prompt từ slide)
    → store assets + skill_lessons status=draft
    → human review → status=published

Online (learner)
  GET lesson (published only)
    → FE slide deck → POST lesson/complete
    → Practice quiz → mastery → complete week
```

| Unit | Responsibility |
|------|----------------|
| `skill_lessons` | Slide deck đã duyệt (+ refs ảnh) |
| Object storage / static | File ảnh minh họa |
| `lesson_generation_service` | Offline text + image prompts/calls |
| `user_lesson_progress` | Đã xem xong Learn |
| `lesson_service` | Serve published; mark complete |
| Practice page | Slides Learn \| Practice |

Feature flag gợi ý: `LEARN_SLIDES_ENABLED` (default off đến khi pipeline + vài lesson A1 published).

---

## 5. Data model

### 5.1 `skill_lessons`


| Column | Type | Notes |
|--------|------|--------|
| `id` | BIGINT PK | |
| `skill_id` | BIGINT FK, UNIQUE | 1 lesson / skill |
| `title` | VARCHAR(500) | |
| `objective` | TEXT | can-do |
| `content` | JSON | mảng **slides** có thứ tự |
| `source` | VARCHAR(20) | `llm_reviewed` (chính) \| `human` |
| `status` | VARCHAR(20) | `draft` \| `published` |
| `book_source_id` | BIGINT NULL FK | grounding excerpt |
| `created_at` / `updated_at` | timestamptz | |


### 5.2 `user_lesson_progress`

Giữ như trước: UNIQUE(`user_id`, `skill_id`), `completed_at`.

### 5.3 Slide schema (`content`)

Mỗi phần tử là **một slide**:

```json
{
  "type": "intro|explanation|example|key_points|inline_check|takeaway",
  "title": "optional short heading",
  "text": "string — hoặc dùng items cho key_points",
  "items": ["..."],
  "gloss_vi": "optional",
  "prompt": "inline_check only",
  "options": ["..."],
  "answer": "...",
  "image_url": "https://.../lessons/{skill_id}/slide_02.webp",
  "image_alt": "short EN or VI description"
}
```

| `type` | Text | Ảnh minh họa (offline) | Ngôn ngữ text |
|--------|------|-------------------------|---------------|
| `intro` | Ngữ cảnh + mục tiêu | Cảnh/tình huống | VI |
| `explanation` | Rule | Sơ đồ / highlight cấu trúc | VI |
| `example` | Worked example | Minh họa tình huống câu | EN (+ gloss VI) |
| `key_points` | 3–5 bullets | Icon/cụm từ nổi | EN |
| `inline_check` | 1 câu nhanh, không mastery | Optional | prompt VI; answer EN |
| `takeaway` | Tóm tắt | Optional nhẹ | VI/EN ngắn |

**Publish rule:** slide bắt buộc (`intro`, `explanation`, `example`, `key_points`) phải có `image_url` hợp lệ trước khi `published`. `inline_check` / `takeaway` ảnh optional.

Independent practice = quiz hiện có.

---

## 6. Offline generation pipeline

1. Input: `skill_id`, excerpt từ primary `book_skill_sources` (nếu có), `skill_type`, CEFR.
2. LLM text → JSON slides (validate schema + language rules).
3. Với mỗi slide cần ảnh: build image prompt (từ `type` + `text` + CEFR; **không** nhét PII; style nhất quán — flat illustration, no text-in-image nếu tránh được).
4. Image model → lưu file → ghi `image_url` / `image_alt`.
5. `status=draft` → reviewer publish.
6. Fail một bước → giữ draft / không publish; log; không serve learner.

Không gọi LLM/image khi `GET` lesson.

---

## 7. API

### `GET /api/v1/skills/{skill_id}/lesson`

- Nếu feature off **hoặc** không có `published` → `{ "lesson": null, "learn_available": false }` → FE **không** vào phase Learn (quiz only).
- Nếu có published → slides + `lesson_completed` + `can_skip`.

`can_skip = lesson_completed OR mastery >= 0.7`

### `POST /api/v1/skills/{skill_id}/lesson/complete`

Upsert progress (chỉ meaningful khi learn_available).

### Admin/job (implementation detail in plan)

- `POST .../admin/skills/{id}/lesson:generate` (offline) → draft  
- `POST .../admin/skills/{id}/lesson/publish` sau review  

### Unchanged

Quiz + `POST .../roadmap/steps/{id}/complete` (mastery only).

---

## 8. Frontend

```text
Open /dashboard/practice/[skillId]
  → GET lesson
  → if learn_available && !can_skip:
       phase = learn (slide carousel: ảnh + text, next/prev)
       last slide / "Tiếp tục luyện" → POST complete → practice
  → else:
       phase = practice
       if learn_available: link "Xem lại bài học"
  → Practice = quiz
```

UI: full-bleed-ish slide trong khung practice (minimalist — không dashboard cards chồng); swipe/next; progress dots theo số slide.

---

## 9. Phased delivery


| Phase | Scope | Learner thấy |
|-------|--------|----------------|
| **P0** | Giữ quiz-only (hiện tại) | Chỉ quiz |
| **P1** | Schema `skill_lessons` + progress + storage ảnh + offline text+image job + admin publish | Vẫn quiz-only (flag off) |
| **P2** | FE slide Learn + flag on cho skill đã published | Learn slides → Practice |
| **P3** | Mở rộng cover thêm skill / cải prompt ảnh | Nhiều skill hơn |


**Definition of done để bật flag:** ≥ N lesson A1 published (đề xuất N=3) với đủ ảnh bắt buộc; GET/POST + FE slide ổn định.

---

## 10. Testing

- Validate slide schema; reject publish thiếu `image_url` trên slide bắt buộc
- Pipeline mock: text JSON + fake image URLs → draft → publish
- GET: unpublished / flag off → `learn_available=false`
- POST complete + `can_skip` rules
- Complete week không cần lesson progress
- FE: không hiện Learn khi `!learn_available`

---

## 11. Risks


| Risk | Mitigation |
|------|------------|
| Image gen chậm/đắt | Batch offline; cache; giới hạn slide có ảnh bắt buộc |
| Ảnh có chữ / sai nghĩa | Prompt cấm text-in-image; human review trước publish |
| Learn chậm ship | Chấp nhận (quyết định C); quiz vẫn dùng được |
| Bản quyền sách | Grounding excerpt cho text; ảnh là illustration mới, không scan trang sách |


---

## 12. Files (expected)

- `backend/alembic/versions/*_add_skill_lessons_and_progress.py`
- `backend/app/models/skill_lesson.py`
- `backend/app/services/lesson_service.py`
- `backend/app/services/lesson_generation_service.py` (text + image offline)
- `backend/app/api/...` (learner + admin generate/publish)
- `backend/tests/test_lesson_service.py`, `test_lesson_generation_*.py`
- `frontend/.../practice/[skillId]/page.tsx` + slide UI component
- `frontend/.../lib/lesson.ts`

---

## 13. Self-review checklist

- [x] Ship gate C explicit — no half Learn for users
- [x] Slides + offline image gen locked
- [x] Serve-time no LLM/image
- [x] Quiz / complete-week contracts unchanged
- [x] One template all skill_types; content varies

---

## 14. Summary

Learn = **slide deck** (text GRR + ảnh minh họa). Text và ảnh gen **offline** khi tạo lesson; learner chỉ xem bản `published`. **Không bật Learn** cho user đến khi pipeline sẵn; trước đó Practice vẫn chỉ quiz. Complete week vẫn chỉ mastery ≥ 0.7.
