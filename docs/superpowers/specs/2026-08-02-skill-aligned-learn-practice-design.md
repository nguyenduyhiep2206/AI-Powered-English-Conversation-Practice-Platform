# Thiết kế: Learn + Practice bám skill (micro-steps lesson + quiz drill)

**Ngày:** 2026-08-02  
**Trạng thái:** Accepted   
**Plan:** `docs/superpowers/plans/2026-08-02-skill-aligned-learn-practice.md`  
**Phạm vi:** `backend` (schema/validate/gen lesson, blueprint/gen/validate quiz, cổng publish), `frontend/my-app` (bước `LessonMiniUnit`, render practice cho các loại drill)  
**Phụ thuộc:** Skill lesson mini-unit (`2026-07-29-skill-lesson-mini-unit-design.md`), skill graph + roadmap ZPD, quiz bank hiện có  
**Mở rộng:** Schema content Learn mini-unit; sinh quiz Practice trên roadmap (không gồm listening/speaking)  
**Ngoài phạm vi increment này:** listening, speaking/phát âm, sản phẩm spaced-repetition, gom Unit trên FE, attach nhiều skill / unit  

---

## 1. Vấn đề

Mỗi week trên roadmap = một skill catalog. Learn mini-unit và Practice quiz đã có, nhưng chất lượng học liệu yếu so với app ESL:

1. **Lệch skill** — Practice hay sinh TOEIC R6/R7 từ excerpt sách, không kiểm tra skill vừa học (ví dụ *Verb to be* → đọc hiểu Hudson’s Bay).
2. **Learn mỏng** — Một passage dài + chip target + 1–2 check + writing, thiếu bước **Form** rõ ràng như app dùng cho grammar.
3. **Practice hẹp** — Gen ưu tiên TOEIC mcq và từ chối `cloze` / `fix_grammar` dù enum đã có.

Listening/speaking để sau. Spec này củng cố **Learn chữ + Practice chữ** để dạy và kiểm tra **cùng một skill**.

---

## 2. Mục tiêu / Không làm

### Mục tiêu

- **Hợp đồng nội dung:** Lesson targets (và pattern trong `form` nếu có) là nguồn sự thật cho những gì Practice phải luyện.
- **Learn micro-steps:** Hook → Notice → Form → Meaning → Check có kiểm soát → Viết có hướng dẫn → Feedback (→ Practice).
- **Practice drills:** Trộn các dạng ngắn bám skill (chọn form, cloze, sửa lỗi, contrast, paraphrase nhẹ); tối đa ≤2 câu reading ngắn và chỉ khi vẫn dùng target của lesson.
- **Cổng publish:** Không publish lesson/quiz fail alignment / schema; admin thấy lỗi rõ.
- **Tương thích ngược:** Lesson cũ không có `form` vẫn mở được (bỏ qua bước Form). Câu TOEIC cũ vẫn render.
- Giữ: `LEARN_UNIT_ENABLED`, learn-before-practice, mastery ≥ 0.7 mới complete week, copy English→English.

### Không làm

- Audio / speaking / phát âm
- Đổi ZPD assembler, skill graph, hoặc attach 1 unit → 1 skill
- Xóa hẳn chế độ TOEIC (có thể giữ làm path admin theo sách)
- Regen toàn bộ content lịch sử trong migration (regen = việc admin/ops)
- Engine spaced repetition

---

## 3. Quyết định (đã chốt)

| Chủ đề | Quyết định |
|--------|------------|
| Hình dạng plan | **Một** plan triển khai (Tasks 1–9 trong file plan) |
| Nguồn alignment | Lesson published: `targets[].surface` (+ `form.rows[].pattern`). Grammar **bắt buộc** có lesson trước khi skill_drill. Vocab/functional/reading có thể heuristic (`alignment=heuristic`) nếu chưa có lesson |
| Schema Learn | Thêm field JSON **additive**; không phá key cũ |
| Bước Form | Bắt buộc với `skill_type=grammar` khi **gen/publish mới**; tùy chọn với vocabulary/functional/reading |
| Mode gen Practice | Mặc định roadmap: blueprint **`skill_drill`** (không TOEIC-first). TOEIC R5–R7 chỉ khi admin gọi rõ `mode=toeic`. |
| Loại câu | Bật lại `cloze` và `fix_grammar` cho `skill_drill`; giữ `mcq`. Phân loại finer qua `item_kind` (string), chưa thêm enum DB. |
| Sentence build | **Hoãn** (cần FE kéo thả). Spec cho phép `item_kind=sentence_build` sau; không có trong blueprint MVP. |
| Reading trong Practice | Tối đa 2 item / batch; mỗi item phải **token-match** ≥1 target surface (cùng luật §5.3) |
| Ngưỡng align | ≥80% item Practice sau gen phải qua validator; không đạt → fail gen (retry 1 lần) hoặc từ chối publish |
| Cách đo align | Không dùng substring thô (tránh false positive: `is` trong `history`). Dùng **token / word-boundary** (regex `\b` sau normalize), và surface dài ≥2 ký tự; ưu tiên match trong `answer` hoặc blank-stem. Chi tiết §5.3 |
| Chấm bài Practice | Giữ `grade_mcq` (trim + lower) cho mcq/cloze/fix_grammar — so khớp **một** chuỗi `answer`. Không hỗ trợ nhiều đáp án đúng trong increment này |
| Nguồn sách khi gen drill | `quiz_questions.book_id` / `unit_id` vẫn **bắt buộc** như hiện tại: skill_drill lấy primary `book_skill_source` (excerpt optional grounding). Không tạo câu “không sách” |
| Gen khi chưa có lesson | Grammar: **từ chối** `skill_drill` nếu chưa có lesson published (bắt admin gen lesson trước). Vocab/functional/reading: cho phép heuristic yếu hơn (`alignment=heuristic`) |
| Đổi default mode | `GenerateQuizRequest.mode` mặc định `skill_drill` — **breaking** với admin quen TOEIC; document rõ và UI/admin nên hiện mode |
| Writing feedback | API giữ nguyên; nudge prompt: giữ nghĩa learner; nhắc `must_use` thiếu |
| Listen/speak | Để phase sau |

---

## 4. Kiến trúc

```text
Admin offline
  generate lesson  → normalize (micro-steps + targets) → draft
  publish lesson   → assert_publishable (+ bắt buộc form nếu grammar)

  generate quiz    → mode=skill_drill (mặc định)
                   → blueprint từ skill_type + lesson targets
                   → LLM JSON → validate align ≥80% → draft
  publish quiz     → assert từng item align hoặc reject

Learner online
  Learn: FE đi từng step (bỏ qua block optional thiếu)
  Practice: API quiz hiện có; FE render mcq | cloze | fix_grammar
```

---

## 5. Hợp đồng dữ liệu

### 5.1 Lesson `content` (mở rộng)

```json
{
  "hook": "optional short EN can-do; default to objective if absent",
  "passage": {
    "text": "EN paragraph ~40–100 words at skill CEFR (prefer shorter at A1)",
    "gloss": "optional EN tip"
  },
  "form": {
    "title": "EN label e.g. Verb to be (present)",
    "rows": [
      { "label": "I", "pattern": "am", "example": "I am a student." }
    ]
  },
  "targets": [
    { "surface": "am", "gloss": "EN definition", "note": "optional" }
  ],
  "checks": [
    { "type": "mcq|cloze", "prompt": "EN", "options": ["..."], "answer": "..." }
  ],
  "writing": {
    "prompt": "EN",
    "min_words": 12,
    "must_use": ["am", "is"]
  },
  "exit_check": {
    "type": "mcq",
    "prompt": "EN",
    "options": ["..."],
    "answer": "..."
  }
}
```

Luật:

- `targets`: số lượng theo setting `LEARN_LESSON_MIN_TARGETS`–`LEARN_LESSON_MAX_TARGETS` (đã có).
- Mỗi `targets[].surface` phải xuất hiện trong `passage.text` (không phân biệt hoa thường).
- `form.rows`: 2–8 dòng khi có `form`; `pattern` không rỗng.
- `checks`: 1–2 (như hiện tại).
- `exit_check`: tùy chọn; nếu có thì cùng shape một check.
- Publish grammar: bắt buộc `form` với ≥2 rows.
- Lesson cũ thiếu `hook` / `form` / `exit_check` → FE bỏ qua các bước đó.

### 5.2 Metadata quiz drill

Dùng cột JSON nullable sẵn có `quiz_questions.task_brief` (không thêm cột Alembic):

```json
{
  "item_kind": "form_choose",
  "alignment": "lesson_targets",
  "surfaces": ["is", "are"],
  "mode": "skill_drill"
}
```

Giá trị `item_kind` cho blueprint MVP:

| item_kind | question_type | FE |
|-----------|---------------|-----|
| `form_choose` | `mcq` | options |
| `cloze_form` | `cloze` | input hoặc options nếu có |
| `fix_grammar` | `fix_grammar` | hiện câu sai; answer = câu đúng |
| `contrast` | `mcq` | options |
| `paraphrase` | `mcq` | options |
| `reading_target` | `mcq` | passage + stem (≤2 / batch) |

### 5.3 Validator alignment (pure)

```text
align_score(item, surfaces: set[str]) -> bool
```

**Không** dùng `surface in haystack` substring thô.

Chuẩn hóa: lowercase; tách token theo word-boundary (`\b` trên chuỗi alphanumeric).  
True nếu **ít nhất một** surface (length ≥ 2) xuất hiện như token trong gộp `stem + passage + answer + options`.

Gợi ý chặt hơn (khuyến nghị implement): True nếu surface là token trong `answer` **hoặc** (có trong stem/passage **và** có trong options khi mcq).

Batch: `aligned_count / len(items) >= 0.8`.

### 5.4 Namespace `task_brief`

Item writing (`question_type=writing`) đã dùng `task_brief` cho brief viết. Drill **phải** set `task_brief.mode = "skill_drill"` và không đè field writing (`min_words`, …). Publish/align chỉ áp dụng khi `mode == "skill_drill"`.

---

## 6. Generation

### 6.1 Đổi prompt lesson

- Ưu tiên passage **40–100** từ theo CEFR (A1 nghiêng ngắn hơn).
- Grammar luôn emit `form`.
- Emit `hook` (có thể trùng objective).
- `exit_check` tùy chọn.
- Giữ luật English→English.

### 6.2 Blueprint quiz `skill_drill` (ví dụ count=6)

Theo `skill_type`:

**grammar:** 2× `form_choose`, 1× `cloze_form`, 1× `fix_grammar`, 1× `contrast`, 1× `paraphrase`  
**vocabulary:** 2× `form_choose` (nghĩa), 2× `cloze_form`, 1× `paraphrase`, 1× `reading_target`  
**functional / reading:** mix tương tự; `reading_target` ≤2

System prompt: viết drill ESL cho **một skill**; dùng list lesson targets; excerpt sách chỉ grounding tùy chọn; **không** viết TOEIC R6/R7 trừ khi `item_kind=reading_target`.

Retry: 1 lần kèm lỗi validate. Fail rõ cho admin.

**Grammar:** nếu không có lesson published → không gọi LLM; `ValueError` hướng dẫn gen/publish lesson trước.

### 6.3 Path TOEIC

Giữ generator TOEIC hiện tại qua `mode="toeic"` (admin). Learner Practice vẫn chỉ lấy câu `published`. Ops nên publish **skill_drill** cho skill catalog trên path learner.

Admin gen quiz vẫn gắn `book_id`/`unit_id` từ primary source như pipeline hiện tại (kể cả skill_drill).

---

## 7. Frontend

### 7.1 Các bước `LessonMiniUnit`

Thứ tự:

1. `hook` (nếu có hook hoặc objective)  
2. `notice` (passage)  
3. `form` (nếu có `content.form`)  
4. `meaning` (targets)  
5. `check` (vòng lặp hiện có)  
6. `write` → `feedback`  
7. `exit` (nếu có `exit_check`) rồi `onFinished`

Nhãn tiến độ: `Learn · form` v.v. (đã có tên step).

### 7.2 Trang Practice

- Render `cloze` và `fix_grammar` (stem = câu lỗi; answer gõ một dòng).
- Giữ mcq như hiện tại.
- Submit vẫn qua `POST /quiz/answer` + `grade_mcq` (đã trim/lower) — đủ cho exact-match cloze/fix_grammar.
- Checklist Learn → Practice → Complete (đã bắt đầu) giữ nguyên.
- Copy khi chưa có quiz published — giữ cảnh báo admin.

### 7.3 WeekNode

Copy đã hướng mini-unit; không bắt buộc đổi thêm trong design này.

---

## 8. Cổng publish / admin

| Hành động | Cổng |
|-----------|------|
| Publish lesson | `normalize_content` + grammar⇒form + targets nằm trong passage |
| Generate quiz skill_drill | Cần skill + (grammar⇒lesson published); load targets; align ≥80% sau validate; vẫn cần primary book source |
| Publish quiz | Mỗi item `question_type` hợp lệ; nếu `task_brief.mode=skill_drill` và có surfaces → phải qua `align_score` |

Không tự regen draft TOEIC cũ.

---

## 9. Kiểm thử

- Unit: `normalize_content` nhận form / từ chối grammar thiếu form khi publish.
- Unit: `align_score` và ngưỡng batch.
- Unit: `blueprint_for_skill_drill(skill_type, count)` đúng length và kinds.
- Unit: validate quiz chấp nhận cloze/fix_grammar ở skill_drill; mode TOEIC vẫn từ chối chúng.
- FE: test nhẹ tùy chọn hoặc checklist tay (thứ tự step, skip legacy).

---

## 10. Rollout

1. Ship schema + validators + gen (draft).  
2. Ops regen + publish lesson/quiz cho skill trên path A1.  
3. FE micro-steps + render drill.  
4. Verify learner trên một skill (ví dụ `be_present`).  

Flag: không cần flag mới nếu `LEARN_UNIT_ENABLED` đã bật; đổi mặc định mode gen quiz chỉ ở backend.

---

## 11. Tiêu chí thành công

- Grammar skill có lesson+quiz published: Practice nhìn thấy rõ đang luyện cùng form/target với Learn (spot-check tay + align ≥80% tự động).
- Learn hiện bước Form với lesson grammar mới.
- Lesson cũ không `form` vẫn hoàn thành được.
- Không có listening/speaking trong increment này.

---

## 12. Điểm mở (đã giải quyết)

| Câu hỏi | Kết luận |
|---------|----------|
| Một vs ba plan | Một plan (Tasks 1–9) |
| Sentence build | Hoãn |
| Lưu meta | `quiz_questions.task_brief` JSON + `mode=skill_drill` namespace |
| TOEIC | Giữ `mode=toeic` tường minh |
| Align substring | Đổi sang token/word-boundary (§5.3) — review 2026-08-02 |
| Gen grammar không lesson | Từ chối skill_drill |
| Chấm cloze/fix | Dùng `grade_mcq` exact trim/lower |

---

## 13. Ghi chú review (2026-08-02)

**Verdict:** Spec **đủ Accept** sau các vá §3 / §5.3 / §5.4 / §6 / §7.2. Hướng khớp app ESL (Form rõ + drill bám skill; listen/speak để sau).

**Đã vá:** align false-positive; namespace `task_brief`; bắt buộc book source; grammar cần lesson trước drill; ghi rõ grading; cảnh báo đổi default mode.

**Không chặn Accept:**

1. Notice→Form→Meaning thiên explicit (Babbel-like); Duolingo nghiêng learn-by-doing — OK cho A1 grammar.
2. Một `answer` duy nhất cho `fix_grammar` — đủ MVP.
3. Ops regen nội dung cũ — đã non-goal.
4. Surface 1 ký tự (`I`, `a`) bị bỏ qua bởi luật len≥2 — chấp nhận được; dùng pattern/`am`/`is` trong targets.
