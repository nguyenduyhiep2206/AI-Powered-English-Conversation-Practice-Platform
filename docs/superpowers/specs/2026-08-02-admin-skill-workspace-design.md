# Thiết kế: Admin Skill Workspace (Lesson + Drill một chỗ)

**Ngày:** 2026-08-02  
**Trạng thái:** Accepted  
**Plan:** `docs/superpowers/plans/2026-08-02-admin-skill-workspace.md`  
**Phạm vi:** Admin FE workspace theo skill; soft-redirect/legacy links; harden nhẹ gen quiz + copy lỗi; endpoint status gộp (tối thiểu)  
**Phụ thuộc:** Skill-aligned Learn/Practice (`2026-08-02-skill-aligned-learn-practice-design.md`), admin lessons/quiz APIs hiện có  
**Ngoài phạm vi:** One-click pipeline publish→gen, bulk multi-skill, auto-archive TOEIC cũ, listening/speaking, đổi attach sách  

---

## 1. Vấn đề

Admin đang tách:

| Việc | Chỗ |
|------|-----|
| Gen / publish lesson | `/admin/lessons` |
| Gen / publish quiz (drill / writing / TOEIC) | `/admin/quiz` (book → unit → skill) |

Làm **một skill** phải nhảy trang, không thấy checklist Lesson → Drill trên cùng màn. Thêm: grammar `skill_drill` cần lesson `published` nhưng UI không gate — dễ 400; draft list thiếu `mode` / `item_kind`.

---

## 2. Mục tiêu / Không làm

### Mục tiêu

- **Một workspace theo skill:** Lesson → Skill drill → Writing (optional) trên cùng trang.
- **Gate UI:** Disable “Generate drill” khi grammar chưa có lesson published; hiện lý do 1 dòng.
- **Review draft đủ tín hiệu:** `question_type` · `item_kind` · `mode`.
- **Harden gen quiz nhẹ:** Message lỗi rõ (alignment / thiếu lesson / validation); retry đã có giữ nguyên hoặc bổ sung copy.
- **Legacy êm:** Sidebar ưu tiên Skills; `/admin/lessons` và `/admin/quiz` soft-redirect hoặc banner “Open in skill workspace”.

### Không làm

- Xóa API TOEIC / Writing
- One-click “publish lesson rồi gen drill”
- Bulk gen nhiều skill
- Đổi learner Practice / mastery rules
- Xóa hẳn trang Books attach

---

## 3. Quyết định đã chốt

| Chủ đề | Quyết định |
|--------|------------|
| Hình dạng | **A** — màn theo skill |
| Scope | **C** — UI workspace + harden gen + soft-redirect legacy |
| Stepper | `1. Lesson` → `2. Skill drill` → `3. Writing (optional)` |
| TOEIC | Thu gọn dưới “Advanced: TOEIC mode” trên workspace (hoặc link sang quiz book nếu nặng) — không cạnh nút drill chính |
| API | Tái sử dụng generate/publish lesson & quiz hiện có; thêm **GET status gộp** cho 1 skill (lesson + draft/published counts + book source) |
| List skills | Filter CEFR + search title (client hoặc query hiện có) |
| Books attach | Giữ `/admin/books` + sync trên `/admin/quiz` hoặc books; workspace chỉ **consume** primary source đã attach |

---

## 4. Luồng UX

```text
/admin/skills                    → danh sách skill (CEFR, type, badge lesson/drill)
/admin/skills/[skillId]          → workspace

Workspace:
  Header: title · type · CEFR · book/unit primary (nếu có) hoặc “Chưa attach — mở Books”

  Step 1 Lesson
    status badge none|draft|published
    [Generate] [View] [Publish]
    hint: grammar cần Publish trước khi drill

  Step 2 Skill drill
    enabled iff (not grammar) OR lesson published
    [Generate drill] count mặc định 6–8, mode=skill_drill
    Draft list (skill này): checkbox · type · item_kind · mode · stem
    [Select all] [Publish selected]
    Advanced (collapsed): Generate TOEIC (mode=toeic)

  Step 3 Writing (optional)
    [Generate Writing] [publish qua cùng draft list hoặc filter writing]
```

**Soft-redirect**

- Sidebar: thêm **Skills** (primary). Lessons / Quiz đổi label phụ hoặc giữ với banner.
- `/admin/lessons` → banner + CTA “Skill workspace”; optional `?skillId=` deep-link publish/view.
- `/admin/quiz` → banner “Drill theo skill nằm ở Skills”; giữ attach/sync book nếu vẫn cần ops.

---

## 5. Backend

### 5.1 Giữ nguyên

- `POST /admin/lessons/skills/{id}/generate|publish`
- `GET /admin/lessons/skills/{id}`
- `POST /admin/quiz/skills/{id}/generate` (`mode`, `count`)
- `POST /admin/quiz/questions/publish`
- `POST /admin/quiz/skills/{id}/generate-writing`

### 5.2 Thêm (tối thiểu)

`GET /api/v1/admin/skills/{skill_id}/workspace` (hoặc `/admin/lessons/skills/{id}/workspace`):

```json
{
  "skill": { "id", "title", "skill_type", "cefr_level" },
  "lesson": { "status": null|"draft"|"published", "id": null|number, "title": null|string },
  "book_source": null | { "book_id", "unit_id", "unit_title", "is_primary" },
  "quiz": {
    "draft_count": 0,
    "published_count": 0,
    "draft_skill_drill_count": 0,
    "can_generate_skill_drill": true,
    "block_reason": null | "grammar_requires_published_lesson" | "no_book_source"
  }
}
```

`can_generate_skill_drill` mirror rule backend: grammar ⇒ published lesson with surfaces; luôn cần primary book source như gen hiện tại.

### 5.3 Harden gen quiz

- Giữ retry alignment 1 lần.
- Đảm bảo `ValueError` message ổn định, FE map được (`grammar_requires_published_lesson`, `alignment_too_low`, …) — có thể prefix code trong `detail` hoặc giữ string match ngắn.
- Optional: dùng `fold_text` / cùng normalize apostrophe khi so surfaces trong align nếu còn false negative (chỉ nếu reproduce được).

---

## 6. Frontend

| File (dự kiến) | Việc |
|----------------|------|
| `src/app/admin/skills/page.tsx` | List skills |
| `src/app/admin/skills/[skillId]/page.tsx` | Workspace |
| `components/admin/SkillWorkspace.tsx` | Stepper + actions |
| `lib/admin-skills.ts` | fetch workspace + reuse lesson/quiz clients |
| `AdminSidebar.tsx` | Nav Skills |
| `admin/lessons/page.tsx`, `admin/quiz/page.tsx` | Banner / soft link |
| `admin/page.tsx` | Card trỏ Skills |
| `lib/routes.ts` / middleware | Allow `/admin/skills` |

UI theo pattern admin hiện có (border `#EAEAEA`, nút đen, không overbuild dashboard).

---

## 7. Tiêu chí xong

- [ ] Từ sidebar mở Skills → chọn 1 skill → gen lesson → publish → gen drill → publish **không cần** mở trang Lessons/Quiz riêng.
- [ ] Grammar chưa publish lesson: nút drill disabled + lý do; không spam 400.
- [ ] Draft hiện `mode` / `item_kind`.
- [ ] Lessons & Quiz có đường vào workspace.
- [ ] Gen drill fail alignment/lesson: message đọc được trên workspace.
- [ ] Pytest cho workspace payload / can_generate; smoke Playwright optional trên 1 skill.

---

## 8. Rủi ro

| Rủi ro | Giảm |
|--------|------|
| Ops vẫn cần book-first attach | Giữ Books/Quiz sync; workspace hiện “chưa attach” |
| Trùng UI với Lessons cũ | Soft-redirect, không xóa API |
| Scope phình TOEIC UI | Advanced collapsed only |

---

## 9. Self-review

- Không TBD có chủ đích; sentence-build / one-click để phase sau.
- Không mâu thuẫn spec skill_drill (mode mặc định, grammar cần lesson published).
- Scope C đã khóa với user.
