# Thiết kế: Admin ops flow roles (Books → Attach → Skills)

**Ngày:** 2026-08-02  
**Trạng thái:** Accepted  
**Phụ thuộc:** Admin Skill Workspace (`2026-08-02-admin-skill-workspace-design.md`), skill-aligned Learn/Practice  
**Phạm vi:** P0–P2 — làm rõ role trang admin, demote dual-path gen, badge list, workspace review, enrich UI  
**Ngoài phạm vi:** One-click pipeline, bulk multi-skill, seed CEFR UI, remap editor unmapped, xóa API TOEIC/lessons/quiz generate, Survey/Users product, roadmap admin  

---

## 1. Vấn đề

Sau Skill Workspace, ops vẫn lệch vì:

1. **Ba trang gen song song** — Skills (preferred), Lessons (full), Quiz/Attach (gen drill không gate).
2. **Attach nằm ở Quiz** nhưng copy workspace / Books nói “Books → sync”.
3. **Skills list** thiếu tín hiệu drill / book → không biết skill nào còn việc.
4. Sidebar **Lessons** ngang Skills; Survey/Users “Soon” nhiễu.
5. Workspace chỉ xem **draft**; Writing/drill chung một list khó lọc.
6. `enrich-units` API có, UI không; default generate count 6 vs 8.

---

## 2. Mục tiêu / Không làm

### Mục tiêu

- Một luồng ops chuẩn: **Books → Attach → Skills workspace**.
- Mỗi trang **một việc chính**; gen/publish skill content chỉ ở Skills.
- List skills đủ badge để triage.
- Workspace review được published + filter mode.
- Copy/CTA/nav khớp thực tế (không misleading).

### Không làm

- Gộp attach vào Books hoặc Skills (Approach 3).
- Xóa endpoint generate trên quiz/lessons (chỉ bỏ/giảm UI).
- Remap UI cho unmapped units (chỉ copy + Retry).
- One-click publish-lesson→gen-drill, bulk gen.

---

## 3. Quyết định đã chốt

| Chủ đề | Quyết định |
|--------|------------|
| Approach | **2** — role rõ, không rewrite attach |
| Gen trên Attach (`/admin/quiz`) | **A** — **gỡ hẳn** nút Generate drill / Writing per-skill; giữ Attach/Sync + link Workspace + book-wide draft list/publish |
| Lessons | URL giữ; **bỏ Generate/View/Publish**; chỉ list + Open workspace + banner |
| Nav label | `/admin/quiz` → sidebar **Attach** (path giữ để tránh break bookmark/`?bookId=`) |
| Soon stubs | **Ẩn** Survey/Users khỏi sidebar |
| Generate count | Thống nhất **6** (workspace + mọi client còn sót) |
| List badges | Mở rộng payload list skills (một request), không N+1 workspace |

---

## 4. Luồng UX chuẩn

```text
/admin/books
  Upload → detect → confirm & index → status ready
  CTA: “Open Attach” → /admin/quiz?bookId={id}

/admin/quiz  (Attach)
  Chọn book ready → Attach/Sync catalog (+ optional Re-enrich)
  Mapped skills: link Workspace only (không gen)
  Unmapped: count + hướng dẫn + Retry attach
  Sau sync OK: banner “Continue in Skills” + shortcuts skill đã map
  Optional: book-wide draft list + Publish (drafts tạo từ Skills; publish bulk vẫn tiện ở đây)

/admin/skills → /admin/skills/[id]
  Lesson → Skill drill → Writing → publish
  Draft | Published; filter mode
  Nếu no book_source: CTA “Open Attach” (deep-link book nếu biết; else /admin/quiz)
```

**Lessons admin page:** đã gỡ (`/admin/lessons`); gen/publish lesson chỉ qua Skills workspace (API `/admin/lessons/*` giữ).

---

## 5. Chi tiết theo ưu tiên

### P0 — Flow hygiene

| ID | Thay đổi |
|----|----------|
| P0-1 | `blockReasonLabel` / workspace hint: “Attach a book unit… Open **Attach**” → `/admin/quiz` hoặc `?bookId=` khi có `book_source` thiếu nhưng book id biết từ context (không có id → `/admin/quiz`) |
| P0-2 | Books ready: label CTA **Open Attach** (không “Open quiz”) |
| P0-3 | Attach sau sync success: CTA Continue in Skills + list/link mapped skill ids từ sync response (reuse payload hiện có nếu có; không thì link `/admin/skills` + filter CEFR book) |
| P0-4 | `BookQuizPanel`: remove `handleGenerate` / `handleGenerateWriting` UI; row chỉ Workspace (+ signals attach) |
| P0-5 | Sidebar: Quiz→**Attach**; Lessons secondary hoặc giữ nhưng Overview không “Active” ngang Skills; ẩn Survey/Users |
| P0-6 | `/admin/lessons`: remove Generate/View/Publish buttons |
| P0-7 | Skills list badges: `lesson_status`, `quiz_draft_count`, `quiz_published_count`, `has_book_source` (bool) |
| P0-8 | Default `count=6` trong `admin-quiz` generate helpers / mọi call site FE |

### P1 — Workspace completeness

| ID | Thay đổi |
|----|----------|
| P1-1 | Workspace questions: tabs **Draft** / **Published** (reuse `GET .../questions?status_filter=`) |
| P1-2 | Filter client: All · skill_drill · writing · toeic (theo `task_brief.mode` / type) |
| P1-3 | Unmapped panel copy: “Unit chưa map catalog — Retry attach hoặc kiểm tra CEFR seed / enrichment”; không editor |

### P2 — Ops polish

| ID | Thay đổi |
|----|----------|
| P2-1 | Nút **Re-enrich units** trên Attach (gọi `POST .../books/{id}/enrich-units`); toast kết quả; không bắt buộc trước sync |
| P2-2 | Overview cards: Skills preferred · Books · Attach · Lessons “Legacy” |
| P2-3 | Icon sidebar: Skills ≠ Lessons (đổi một trong hai) |

---

## 6. Backend

### Giữ nguyên (mutations)

- Lesson generate/publish APIs  
- Quiz generate / generate-writing / publish  
- `sync-skills`, books upload/index/enrich  

### Thêm / mở rộng (tối thiểu)

**List skills enrichment** — mở rộng `GET /api/v1/admin/lessons/skills` (hoặc alias dưới `/admin/skills` nếu muốn; ưu tiên **mở rộng response hiện có** để FE list không đổi path):

```json
{
  "id": 1,
  "title": "...",
  "skill_type": "grammar",
  "cefr_level": "A1",
  "lesson_status": "published",
  "quiz_draft_count": 2,
  "quiz_published_count": 10,
  "has_book_source": true
}
```

Implement: aggregate counts + exists primary `book_skill_sources` trong `list_skills_with_lesson_status` (một query/group by, không gọi workspace N lần).

**Workspace GET:** không bắt buộc đổi schema P0; P1 dùng questions endpoint sẵn có.

**Tests:** list payload fields; FE không cần E2E bắt buộc — Playwright smoke optional: Attach không còn nút Generate drill.

---

## 7. Frontend (files dự kiến)

| File | Việc |
|------|------|
| `AdminSidebar.tsx` | Attach label; ẩn Soon; icon |
| `admin/page.tsx` | Cards roles |
| `admin/books/page.tsx` | Open Attach CTA |
| `BookQuizPanel.tsx` | Gỡ gen; enrich; post-sync CTA; unmapped copy |
| `admin/quiz/page.tsx` | Banner/title Attach |
| `admin/lessons/page.tsx` | Workspace-only actions |
| `admin/skills/page.tsx` | Badges từ list mới |
| `SkillWorkspace.tsx` | Attach CTA; Draft/Published; mode filter |
| `lib/admin-skills.ts` | Labels; types list |
| `lib/admin-quiz.ts` | count default 6; enrich helper nếu chưa expose UI |
| `lib/admin-books.ts` | (nếu cần) wire enrich từ panel |
| README backend admin | Luồng Books → Attach → Skills |

---

## 8. Tiêu chí xong

- [ ] Ops làm 1 skill mới: Books → Attach sync → Skills lesson→drill→publish **không** cần bấm Generate trên Attach/Lessons.
- [ ] Attach không còn nút Generate drill / Writing.
- [ ] Lessons không còn Generate/View/Publish.
- [ ] Workspace no-book CTA trỏ Attach (không “Books sync”).
- [ ] Skills list hiện lesson + quiz counts + has_book_source.
- [ ] Workspace xem Published + filter mode.
- [ ] Re-enrich gọi được từ Attach.
- [ ] Survey/Users không còn trên sidebar.
- [ ] Pytest list skills enriched fields; generate count FE = 6.

---

## 9. Rủi ro

| Rủi ro | Giảm |
|--------|------|
| Ops quen gen trên Quiz | Banner + Workspace link rõ; README |
| Bookmark `/admin/quiz` | Giữ path, chỉ đổi label |
| List skills query chậm | Aggregate SQL; index sẵn trên skill_id/status |
| Book-wide publish “lạc” drafts từ Skills | Giữ publish trên Attach như convenience; optional note “drafts from Skills” |

---

## 10. Self-review

- Không TBD có chủ đích; remap/one-click/bulk để ngoài phạm vi.  
- Khớp quyết định user: scope C + Approach 2 + gen Attach = A.  
- Một plan implementation đủ; không tách sub-project trừ khi list aggregate phức tạp bất ngờ.  
- “Open Attach” khi thiếu `book_id`: luôn `/admin/quiz` (không đoán book).  
