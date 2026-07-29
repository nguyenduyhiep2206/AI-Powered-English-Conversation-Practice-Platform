# Design: Thêm phần "Học" (lesson) vào roadmap — không chỉ quiz

**Date:** 2026-07-21
**Status:** **SUPERSEDED** by `docs/superpowers/specs/2026-07-29-skill-lesson-mini-unit-design.md` (and previously by 2026-07-26 slide Learn, also discarded)
**Scope:** `backend` (model + service + API mới), `frontend/my-app` (practice → lesson flow)
**Depends on:** `2026-07-20-skill-graph-zpd-roadmap-design.md` (skill graph + ZPD assemble), `2026-07-21-roadmap-assembly-fixes-design.md` (assemble fixes)
**Research:** Exa — Duolingo Method whitepaper, ArthurAI 6-step lesson, Gradual Release of Responsibility (Fisher & Frey / NSW / Smekens), Tiny Lesson

---

## 1. Problem

Hiện tại mỗi tuần trong roadmap chỉ có **luyện quiz**: bấm "Practice skill" → `/dashboard/practice/{skillId}` → tải câu hỏi (`GET /quiz/skills/{id}/questions`) → trả lời → mastery. **Không có bước "dạy/học"** trước khi làm bài:

- User bị ném thẳng vào câu hỏi, không được **giải thích khái niệm, xem ví dụ mẫu, từ vựng trọng tâm** của skill.
- Nếu skill chưa có quiz publish → trang chỉ báo "No published questions" — user không học được gì.
- `learning_skills` **không có trường nội dung** (chỉ `slug`, `title`, `skill_type`, `difficulty_in_level`); nội dung sách nằm ở `book_skill_sources` (provenance) nhưng chưa được dùng để hiển thị bài học.

Mục tiêu: mỗi bước roadmap trở thành một **micro-lesson**: *học → luyện → phản hồi → đạt mastery*, thay vì chỉ quiz.

---

## 2. Nền tảng nghiên cứu (Exa)

- **Gradual Release of Responsibility (I do / we do / you do):** khung chuẩn để dạy một skill mới — *focused instruction* (nêu mục tiêu, giải thích, ví dụ mẫu + think-aloud) → *guided practice* (gợi ý, scaffold) → *independent practice* (tự làm) → *mastery check*. Thiết kế "từ đích ngược": viết bài kiểm tra độc lập trước, rồi mới scaffold ([Fisher & Frey](https://keystoliteracy.com/wp-content/uploads/2017/08/frey_douglas_and_nancy_frey-_gradual_release_of_responsibility_intructional_framework.pdf), [NSW scaffolding](https://education.nsw.gov.au/content/dam/main-education/documents/teaching-and-learning/curriculum/explicit-teaching/explicit-teaching-scaffolding-technique-guide.pdf), [Smekens 4-step mini-lesson](https://www.smekenseducation.com/execute-minilessons-in-4-steps0/)).
- **Cấu trúc lesson 6 bước (ArthurAI):** introduction · key concepts · detailed explanation (worked examples) · real-world applications · summary · practice questions — mỗi bước có prompt riêng, "AI generates, educator attests, learner sees" ([ArthurAI](https://www.arthurgrid.ai/how-it-works/lesson-flow/)).
- **Duolingo Method:** bài **bite-sized**, "dive right in", nguyên tắc **i+1** (chỉ 5–7 mục mới mỗi bài, bọc trong nội dung đã quen), **giải thích plain-language + hint theo yêu cầu**, ZPD/"desirable difficulty", spaced repetition, personalized practice theo điểm yếu ([whitepaper](https://duolingo-papers.s3.amazonaws.com/reports/Duolingo_whitepaper_duolingo_method_2023.pdf), [i+1](https://blog.duolingo.com/right-level-of-difficulty/)).
- **Tiny Lesson:** outline → unit → tiny lesson = *nội dung tập trung + practice*, mastery loop "teach → practice → feedback → weak-point review" ([tinylesson.app](https://tinylesson.app/)).

Đúc kết: một lesson tốt cho 1 skill = **mục tiêu ngắn + giải thích + ví dụ mẫu + từ khoá**, rồi mới tới **guided/independent practice** (quiz hiện có) và **mastery check**; giữ bite-sized; scaffold nhiều lúc đầu rồi fade dần.

---

## 3. Goals / Non-goals

### Goals
- Mỗi bước roadmap có **learn phase** trước practice: objective → explanation → worked examples → key vocab/points.
- Lesson **bám skill của tuần** (dùng `skill_type` để chọn khuôn), grounded bằng excerpt sách (`book_skill_sources`).
- Nội dung lesson là **content được duyệt** (human hoặc **LLM offline + human review**), lưu sẵn — **không gọi LLM lúc serve**.
- Tận dụng quiz hiện có làm *guided/independent practice*; giữ nguyên vòng mastery ≥ 0.7.
- Có đường thoát an toàn khi thiếu content (fallback), không chặn user như lỗi "No published questions".

### Non-goals
- Không sinh lesson **online** mỗi request (theo pattern offline/online split).
- Không làm lesson editor phức tạp cho admin ở phase đầu (tối thiểu: bảng + seed + API đọc).
- Không đổi thuật toán `select_skills_for_roadmap` / cách chọn scenario (đã có spec riêng).
- Chưa làm spaced-repetition review đầy đủ (ghi là follow-up).

---

## 4. Current state (dữ liệu sẵn có)

| Nguồn | Có gì | Dùng cho lesson |
|---|---|---|
| `learning_skills` | `slug`, `title`, `skill_type`, `difficulty_in_level` | tiêu đề + phân loại khuôn lesson; **không có nội dung** |
| `book_skill_sources` | map unit sách → skill, `unit_title`, `section_title`, `is_primary` | **grounding**: lấy excerpt từ unit primary để soạn/generate lesson |
| `quiz_questions` | stem/options/passage/explanation theo skill | **independent practice** (đang dùng) |
| `scenarios` | role-play chat theo level/category | **real-world application** (transfer) — nối tùy chọn |

⇒ Thiếu: **nơi lưu nội dung bài học theo skill**. Đây là hạng mục mới cần thêm.

---

## 5. Proposed design

### 5.1 Data model mới: `skill_lessons`

Một lesson tập trung cho 1 skill, nội dung có cấu trúc (JSON blocks theo ArthurAI/GRR).

```
skill_lessons
  id            BIGINT PK
  skill_id      BIGINT FK -> learning_skills(id) ON DELETE CASCADE, indexed
  title         VARCHAR(500)         -- "How to introduce yourself"
  objective     TEXT                 -- can-do: "By the end you can..."
  content       JSON                 -- các block có thứ tự (xem 5.2)
  source        VARCHAR(20)          -- 'human' | 'llm_reviewed'
  status        VARCHAR(20)          -- 'draft' | 'published'
  book_source_id BIGINT NULL FK -> book_skill_sources(id)  -- grounding provenance
  created_at / updated_at
  UNIQUE(skill_id)   -- MVP: 1 lesson/skill (có thể nới sau)
```

Ghi chú: chỉ `status='published'` mới hiển thị cho learner (giống pattern "educator attests → learner sees").

### 5.2 Cấu trúc `content` (block-based, map GRR)

Bám khung GRR + 6-step, rút gọn cho bite-sized. `content` là mảng block có thứ tự:

| Block `type` | Ý nghĩa | GRR phase |
|---|---|---|
| `intro` | 1–2 câu ngữ cảnh + mục tiêu | I do (focused) |
| `explanation` | giải thích plain-language, ngắn | I do |
| `example` | ví dụ mẫu (worked example) + (tùy) think-aloud | I do |
| `key_points` | 3–5 điểm/từ vựng trọng tâm (i+1) | I do |
| `inline_check` | 1 câu hỏi nhanh non-graded, feedback ngay | we do (guided) |
| `takeaway` | tóm tắt để review | summary |

Sau các block là **independent practice = quiz hiện có** (skill questions) và **mastery check** (≥ 0.7). `scenario` của tuần (nếu có) = bước **real-world application** tùy chọn.

### 5.3 Luồng học mới của một tuần

```
Roadmap week (skill)
  └─ Lesson (skill_lessons.published)
       1. Learn:   intro → explanation → example → key_points   [I do]
       2. Guided:  inline_check(s) với feedback ngay            [we do]
       3. Practice: quiz skill questions (đang có)              [you do]
       4. Mastery:  mastery ≥ 0.7 → complete week
       (5. Apply:   vào chat scenario của tuần — optional)
```

So với hiện tại: chèn bước 1–2 **trước** bước 3 (quiz) đã tồn tại. Không phá vòng mastery/complete-week.

### 5.4 Nguồn nội dung: LLM offline + human review (khuyến nghị)

Theo pattern đã thống nhất (offline/online split, human-in-the-loop):

1. **Job offline** (không ở serve-time): với mỗi skill `is_active`, lấy excerpt từ `book_skill_sources` (unit `is_primary`) làm grounding → LLM sinh `content` theo khuôn `skill_type` (grammar/vocabulary/…) → lưu `status='draft'`, `source='llm_reviewed'`.
2. **Admin duyệt/sửa** → chuyển `status='published'`.
3. **Serve-time chỉ đọc** `published` (không gọi LLM).

Fallback khi chưa có lesson published: hiển thị `title` + `objective` tối thiểu (sinh từ `title`/`skill_type`) + đi thẳng practice — **không chặn** user.

### 5.5 API

- `GET /api/v1/roadmap/steps/{step_id}/lesson` → trả lesson published của skill gắn với step (kèm `objective`, `content`), hoặc `null` → FE fallback.
- (Admin, phase sau) `POST /api/v1/admin/skills/{skill_id}/lesson:ai-draft` → sinh draft; `PUT .../lesson` duyệt/publish. (Kiểu A đã bàn.)

### 5.6 Frontend

- `dashboard/practice/[skillId]` (hoặc route mới `.../learn`) đổi thành **2 phase**: **Learn** (render blocks từ `content`) → nút "Start practice" → **Practice** (quiz hiện tại, giữ nguyên).
- `WeekNode`: đổi/î thêm nút "Học" (Learn) song song "Practice"; hoặc gộp thành 1 CTA "Bắt đầu tuần" đi qua Learn → Practice.
- Tôn trọng bite-sized: mỗi block ngắn, cuộn mượt; giữ minimalist-ui.

---

## 6. Phased plan

- **P1 — Data + đọc:** thêm bảng `skill_lessons` (migration), model, `GET step lesson` API, seed vài lesson mẫu (human-authored) cho A1 để chạy end-to-end.
- **P2 — FE learn phase:** practice page thành Learn → Practice; fallback khi thiếu lesson.
- **P3 — Pipeline offline:** job LLM-draft grounded bằng book excerpt + admin review/publish (kiểu A).
- **P4 — Enhancements:** inline_check chấm nhẹ, nối scenario (apply), spaced-repetition review, nhiều lesson/skill.

---

## 7. Open questions

1. 1 lesson/skill (MVP) hay nhiều lesson/skill (unit nhỏ)? — đề xuất bắt đầu 1.
2. Learn phase **bắt buộc** trước practice hay cho phép "skip to practice" (user khá)? — GRR fade dần ⇒ cho skip khi mastery đã cao.
3. Có tách route `/learn` riêng hay gộp trong `/practice`? — gộp để đỡ điều hướng.
4. Lesson có cần đa dạng theo `skill_type` tới mức khác template không, hay 1 template chung? — bắt đầu 1 template, dữ liệu khác theo skill.

---

## 8. Files (dự kiến khi implement)

- `backend/alembic/versions/*_add_skill_lessons.py` (mới)
- `backend/app/models/skill_lesson.py` (mới)
- `backend/app/services/lesson_service.py` (mới) + API trong `app/api/roadmap.py`
- `backend/app/seeds/skill_lessons.py` (seed mẫu, mới)
- `frontend/my-app/lib/lesson.ts` (mới), sửa `dashboard/practice/[skillId]/page.tsx`, `components/roadmap/WeekNode.tsx`

---

## 9. Tóm tắt

Biến mỗi tuần roadmap từ "chỉ quiz" thành **micro-lesson theo GRR**: *học (giải thích + ví dụ + từ khoá) → guided check → practice quiz → mastery*, nội dung lưu ở bảng mới `skill_lessons`, grounded bằng excerpt sách và tạo theo **LLM offline + human review** (không sinh lúc serve), có fallback an toàn. Tận dụng tối đa quiz + scenario + mastery đã có.
