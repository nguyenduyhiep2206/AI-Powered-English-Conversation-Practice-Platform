# Thiết kế: Placement TOEIC R+W + quiz Reading TOEIC (bank thống nhất)

**Ngày:** 2026-07-28  
**Trạng thái:** Implemented (core path) — review FE polish / admin writing generate hook as follow-up  
**Thay thế:** `docs/superpowers/specs/2026-07-23-adaptive-placement-design.md` (path placement)  
**Mở rộng:** AI quiz generation (`quiz_generation_service`) → format Reading TOEIC  
**Rubric Writing:** [ZIM – Tiêu chí chấm TOEIC Writing](https://zim.vn/tieu-chi-cham-diem-toeic-writing)  
**Phụ thuộc:** Survey Busuu-style; skill graph + book ingest; roadmap `current_level` + `placement_score`

**Quyết định bank (đã đổi):** **Không** tách `placement_passages` / `placement_items`. Một bank mở rộng trên `quiz_questions` (+ `quiz_passages`); placement assemble từ **subset published**; luyện skill dùng cùng format Reading.

---

## 1. Vấn đề

1. Placement adaptive (MCQ/cloze ngắn) ≠ TOEIC Reading + Writing.  
2. AI hiện sinh `mcq|cloze|fix_grammar` theo CEFR blueprint — user luyện **không** quen format Part 5/6/7.  
3. Writing chưa có trong bank → không chấm placement Writing theo rubric.

Cần **một schema** phục vụ cả practice lẫn placement, AI generate đúng dạng Reading TOEIC (+ Writing tasks).

---

## 2. Mục tiêu / Ngoài phạm vi

### Mục tiêu

- **Bank thống nhất:** mở rộng `quiz_questions` + bảng `quiz_passages` (passage/email dùng chung nhiều item).  
- **AI generate** draft theo `toeic_part` Reading (`r5`/`r6`/`r7`), vẫn gắn `skill_id` / `book_id` / `unit_id` / CEFR; admin publish như hiện tại.  
- **Writing** (`w1`/`w2`/`w3`) nằm cùng bank (generate riêng hoặc ingest); dùng cho placement (và sau này practice writing nếu muốn).  
- Placement (survey → placement): assemble gần full R+W từ **published** có `toeic_part`; timer; Reading auto-grade; Writing AI + feedback ZIM; map CEFR + `placement_score` 1–10.  
- **Xóa adaptive** trên path placement.  
- Practice trên roadmap: UI/flow làm câu Reading TOEIC theo skill (không còn assume chỉ cloze/mcq cũ).

### Ngoài phạm vi

- Listening / Speaking.  
- Adaptive / CAT.  
- ETS official scoring / pháp lý “điểm TOEIC”.  
- Bắt buộc mọi skill_type đều ra đủ R5+R6+R7 mỗi lần generate (xem §5 — blueprint theo skill/book).  
- Tự generate đủ 100+8 cho placement trong một lần gọi (placement lấy **pool** published toàn hệ thống).

---

## 3. Quyết định đã chốt

| Chủ đề | Quyết định |
|--------|------------|
| Bank | **C:** mở rộng `quiz_questions` + `quiz_passages` — **không** bảng placement_* riêng |
| Practice | Câu AI mới = Reading TOEIC (`r5`/`r6`/`r7`), gắn skill/CEFR |
| Writing | Cùng bank (`w1`/`w2`/`w3`); placement bắt buộc; practice writing = follow-up |
| Placement source | `status=published` AND `toeic_part IS NOT NULL` |
| Assemble | Đủ quota R5/R6/R7/W1/W2/W3 từ pool (cross-skill OK) |
| Legacy items | `toeic_part` null: không vào placement TOEIC; practice có thể ẩn dần hoặc vẫn làm được nếu FE hỗ trợ type cũ |
| Engine cũ | Xóa adaptive |
| Writing chấm | AI theo rubric ZIM |

---

## 4. Schema

### `quiz_passages` (mới)

| Cột | Ý nghĩa |
|-----|---------|
| `id` | PK |
| `book_id` / `unit_id` | nullable hoặc bắt buộc khi sinh từ sách |
| `toeic_part` | `r6` \| `r7` \| `w2` (email) |
| `body` | TEXT |
| `media_url` | nullable |
| `status` | draft / published (hoặc derive từ items) |
| `meta` | JSON |

### `quiz_questions` (mở rộng)

Thêm:

| Cột | Ý nghĩa |
|-----|---------|
| `toeic_part` | `r5`\|`r6`\|`r7`\|`w1`\|`w2`\|`w3` \| null (legacy) |
| `passage_id` | FK `quiz_passages` nullable (bắt buộc r6/r7; khuyến nghị w2) |
| `prompt_words` | JSON — W1 hai từ gợi ý |
| `media_url` | W1 ảnh (hoặc trên passage) |
| `task_brief` | JSON — W2/W3 constraints (ask 2 questions, min words…) |

`question_type` mở rộng:

- Giữ `mcq` cho Reading (R5/R6/R7).  
- Thêm `writing` (hoặc `toeic_writing`) cho W1–W3; `answer` có thể `""` / null-safe; grading không so string.

Có thể deprecate dần `cloze` / `fix_grammar` trong **generator mới** (không bắt xóa row cũ).

`passage` TEXT cũ: vẫn giữ để tương thích; item mới ưu tiên `passage_id` + join body (R6/R7 không duplicate 4 lần nếu cùng set).

---

## 5. AI generation (Reading TOEIC)

Đổi `quiz_generation_service` + `cefr_descriptors.blueprint_for`:

### Blueprint theo part

| `toeic_part` | Hành vi generate |
|--------------|------------------|
| `r5` | Incomplete sentence; 4 options; **không** cần passage dài (1 câu stem) |
| `r6` | 1 `quiz_passages` + N blanks/items (thường 4) MCQ; passage grounded excerpt |
| `r7` | 1 passage (single/double passage) + M comprehension MCQ |
| `w1`/`w2`/`w3` | Job/generate riêng (ảnh+words / email / opinion) — không nhét cùng batch Reading mặc định |

### Gợi ý mix theo `skill_type` / `book_type`

- `reading` / `reading_practice` book → ưu tiên `r6`+`r7`.  
- `grammar` / `vocabulary` → ưu tiên `r5` (+ ít `r6`).  
- `functional` → `r7` tình huống / email-like trong reading.

Mỗi lần `generate_quiz_for_skill`: trả về set có `toeic_part` + tạo `quiz_passages` khi cần; validate options/answer như hiện tại; grounding passage cho r6/r7.

System prompt: mô tả rõ TOEIC Reading Part 5/6/7; bỏ khuyến khích cloze/fix_grammar cho pipeline mới.

### Writing generate

- Endpoint/admin action riêng hoặc flag `include_writing` / `generate_writing_for_unit`.  
- W1 cần `media_url` (upload hoặc image gen sau — MVP: URL placeholder / admin upload).  
- W2: tạo email `quiz_passages` + `task_brief`.  
- W3: stem đề opinion + `task_brief.min_words` (~300).

---

## 6. Placement assemble & timer

Giống quyết định trước (gần full):

| Part | Quota | Timer |
|------|-------|-------|
| R5 | 30 | |
| R6 | 16 | Reading **75 phút** tổng |
| R7 | 54 | |
| W1 | 5 | |
| W2 | 2 | Writing **58 phút** tổng |
| W3 | 1 | |

Assembler: chỉ `published` + `toeic_part` set; R6/R7 lấy **cả nhóm** cùng `passage_id`; thiếu quota → `503` bank not ready.

Thứ tự: Reading → Writing. Adaptive **bỏ**.

Attempt: `form_snapshot`, `section`, `section_ends_at`, reading/writing scales (xem plan). Answers trỏ `quiz_questions.id`; Writing thêm `score` / `ai_scores` / `ai_feedback`.

---

## 7. Writing AI chấm (ZIM)

| Part | Điểm | Tiêu chí |
|------|------|----------|
| W1 | 0–3 | grammar, relevance to picture |
| W2 | 0–4 | quality/variety of sentences, vocabulary, organization |
| W3 | 0–5 | reasons/examples, grammar, vocabulary, organization |

`chat_json` → score + feedback; empty text → 0. Map raw (max 28) → writing scale 0–200; blend với reading scale → CEFR (min-of-two) + `placement_score` 1–10 (bảng trong code, unit test).

---

## 8. Practice (user học)

- FE practice/quiz skill: render theo `toeic_part` (R5 list; R6/R7 passage + items).  
- Chấm Reading như MCQ hiện có.  
- Writing trong practice: **phase 2** (placement dùng trước).  
- Lesson flow không bắt buộc đổi trong spec này trừ chỗ hiển thị câu hỏi.

---

## 9. API (placement)

| Method | Path |
|--------|------|
| POST | `/onboarding/placement/sessions` |
| GET | `/onboarding/placement/sessions/current` |
| POST | `.../reading-answers` |
| POST | `.../writing-answers` |
| POST | `.../advance-section` |
| POST | `.../complete` |
| GET | `/onboarding/placement/access-status` |

Adaptive `.../answers` → 410.

Generate: giữ admin `generate_quiz_for_skill` nhưng contract JSON mới (`toeic_part`, `passage_group`…).

---

## 10. Rủi ro

| Rủi ro | Giảm nhẹ |
|--------|----------|
| Pool published chưa đủ 100+8 | Gate start; seed + generate nhiều skill/level |
| Legacy cloze còn trong DB | Placement bỏ qua `toeic_part` null; FE practice dual-render tạm |
| W1 thiếu ảnh | Admin upload bắt buộc trước publish W1 |
| Generate R6/R7 lệch số item/passage | Validate: cùng group đúng N items |

---

## 11. Tiêu chí xong

- [ ] Không còn bảng placement_items/passages riêng  
- [ ] `quiz_passages` + cột TOEIC trên `quiz_questions`  
- [ ] Generator mặc định ra R5/R6/R7 (không cloze/fix_grammar mới)  
- [ ] Có path tạo W1–W3 vào cùng bank  
- [ ] Placement assemble từ published; adaptive removed  
- [ ] Writing grade + feedback ZIM  
- [ ] Profile CEFR + sublevel; FE placement R→W  
- [ ] Practice đọc được item Reading TOEIC mới  

---

## 12. So với bản draft trước

| Trước | Nay (C) |
|-------|---------|
| `placement_passages` / `placement_items` | **Bỏ** — dùng `quiz_passages` / `quiz_questions` |
| Placement bank tách | Placement = filter published + `toeic_part` |
| AI quiz giữ mcq/cloze | AI quiz → Reading TOEIC |
| Writing chỉ placement table | Writing cùng quiz bank |
