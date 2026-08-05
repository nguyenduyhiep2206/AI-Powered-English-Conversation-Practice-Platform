# Thiết kế: Restyle AI Tutor chat layout

**Ngày:** 2026-08-04  
**Status:** Implemented  
**Phạm vi:** UI `/ai-tutor/[sessionId]` (Next.js App Router)  
**Không đổi:** Backend tutor start/messages/end, persist `tutor_sessions` / `tutor_messages`

## Vấn đề

Mock FE (TanStack `/chat`) có layout 3 cột rõ scenario + messages + inline feedback. UI AI Tutor hiện tại đủ chức năng SSE/persist nhưng layout chưa khớp mock; correction nằm dưới bubble; Debug RAG chiếm chỗ trên chat roleplay.

## Mục tiêu

1. Restyle `/ai-tutor/[sessionId]` theo layout mock (scenario | chat | feedback).
2. Giữ một cổng chat cho catalog và roadmap Practice speaking (khác chỉ ở payload start session).
3. Persist như hiện tại: session + messages + `meta` (correction/hint/goal_progress).
4. Panel phải hiện feedback từ `meta` thật (không mock-data).
5. **Bỏ Debug RAG** khỏi UI chat này (toggle/panel debug).

## Ngoài phạm vi

- Route `/chat` mới hoặc TanStack Router.
- Trang `/report` mock; End session vẫn dùng summary modal hiện có.
- Đổi RAG backend / tách Ask-book.
- Avatar/profile trên bubble (chỉ persist DB).
- Hint button gọi API riêng (P0: có thể wire nút Hint đọc `meta.hint` gần nhất hoặc disable nếu chưa có).

## Approach (đã chọn)

**A — Restyle in-place trên `/ai-tutor/[sessionId]`**  
Reuse `getTutorSession`, `streamTutorMessage`, `endTutorSession`. Không tạo surface chat thứ hai.

## Layout

```
┌─────────────────────────────────────────────────────────────┐
│ Top: LevelBadge · scenario title · timer · End session      │
├────────────┬──────────────────────────────┬─────────────────┤
│ Scenario   │ Messages (scroll)            │ Inline feedback │
│ (lg+)      │ Composer                     │ (toggle)        │
│ roles/goal │                              │ correction/hint │
│ vocab      │                              │ from meta       │
└────────────┴──────────────────────────────┴─────────────────┘
```

- Mobile: ẩn scenario aside (hoặc sheet nhẹ); feedback drawer/toggle; top bar + chat full width.
- Catalog vs roadmap: cùng layout; data từ session DTO (`ai_role`, `user_role`, `goal_prompt`, `suggested_vocab`, CEFR/level nếu có trên scenario).

## Data wiring

| UI | Nguồn |
|----|--------|
| Title / roles / vocab / goal | Session detail (đã load) |
| Messages | Session messages + SSE append |
| Feedback panel | `meta.correction` / `meta.hint` trên tin `assistant` gần nhất; list các correction trong session |
| End | `endTutorSession` → summary modal |
| User identity | `user_id` trên session (đã auth); không thêm field mới |

## Feedback panel behavior

- Mở mặc định trên `lg+` khi session có ≥1 correction hoặc hint; user đóng/mở được.
- Item: original (gạch), better/corrected, why/note; Pill “Correction” (map từ grammar/vocab mock → một loại “Correction” vì API chưa tách type).
- Không generate feedback giả khi `meta` null.

## Debug RAG

- Gỡ checkbox Debug, panel `TutorDebugInfo`, và không gửi `debug: true` từ trang chat này.
- Backend SSE debug vẫn tồn tại cho lab/script; không expose trên roleplay UI.

## Success criteria

- [x] Layout 3 cột khớp mock trên desktop; mobile dùng được.
- [x] Chat catalog + roadmap vẫn vào `/ai-tutor/{id}`, messages lưu DB.
- [x] Panel phải hiện correction/hint thật sau turn có meta.
- [x] Không còn UI Debug RAG trên trang session.
- [x] End session + summary modal giữ hành vi hiện tại.

## Files dự kiến đụng

- `frontend/my-app/src/app/ai-tutor/[sessionId]/page.tsx` (chính)
- Có thể tách component nhỏ dưới `components/tutor/` nếu file quá dài
- `frontend/my-app/lib/tutor.ts` — chỉ nếu bỏ type/helpers debug phía client không còn dùng

## Changelog

| Ngày | Ghi chú |
|------|---------|
| 2026-08-04 | Draft: restyle A + wire feedback meta + bỏ Debug UI |
| 2026-08-04 | Implemented: 3-column layout, feedback panel, Debug UI removed |
