# Kế hoạch: Thiết kế & sinh câu hỏi theo chuẩn đánh giá CEFR

> **Dành cho agent/kỹ sư thực hiện:** dùng `subagent-driven-development` hoặc `executing-plans`. Checkbox (`- [ ]`) để theo dõi.

**Mục tiêu:** Đổi generate quiz từ “MCQ grammar rời theo excerpt” sang **item CEFR-aware**: can-do theo level, đa dạng type có kiểm soát, **passage/stimulus từ sách** khi phù hợp, validate grounding — phục vụ skill practice + bank placement chất lượng hơn.

**Bối cảnh hiện tại:**
- Type: `mcq` | `cloze` | `fix_grammar` — prompt Prefer mcq → thực tế lệch MCQ
- `cefr_level` copy từ skill/sách; prompt chỉ có dòng `CEFR: Bx` — không can-do
- Không lưu/hiện đoạn văn kèm câu → câu “cùng chủ đề sách” nhưng rời rạc
- Placement vẫn 10 câu / điểm→level (không đổi trong plan này)

**Không làm:** Listening/Speaking/Writing tự do; IRT/adaptive; chứng nhận ALTE chính thức; bỏ placement score table hiện có.

---

## 1. Quyết định thiết kế (chốt)

| Chủ đề | Quyết định |
|--------|------------|
| Khung CEFR | Dùng **can-do rút gọn** (reading / grammar-in-context / vocab-in-context) theo A1–C1 trong code constants — không claim “official exam” |
| Stimulus | Thêm `passage` (nullable TEXT) trên `quiz_questions`; reading & in-context items **bắt buộc** có passage trích từ excerpt |
| Type enum | Giữ 3 type; đa dạng bằng **blueprint mix** + passage, chưa thêm enum mới ở phase 1 |
| Mix theo `book_type` / `skill_type` | Reading book / skill reading → passage MCQ + cloze-in-passage; grammar textbook → grammar MCQ với câu mẫu từ sách + ít cloze/fix |
| CEFR trong prompt | Inject **descriptor + constraints** (độ dài passage, cấu trúc câu, cấm từ quá khó so với level) |
| Validate | Passage phải fuzzy-match trong excerpt; MCQ 4 options; answer ∈ options; reject stem không gắn passage khi blueprint yêu cầu |
| Placement | Vẫn chọn theo `skill.cefr_level`; cải thiện **chất lượng item** trong bank, không đổi công thức 0–10→CEFR |
| Difficulty | Map gợi ý: trong-level `easy/medium/hard` = độ phức tạp tương đối; không thay CEFR label |

### 1.1 Can-do rút gọn (MVP constants)

Lưu trong `backend/app/services/cefr_descriptors.py` (text ngắn, EN):

| Level | Reading (passage Q) | Grammar / vocab in context |
|-------|---------------------|----------------------------|
| A1 | Hiểu câu/ thông báo rất ngắn, quen thuộc | Nhận form cơ bản (be, present simple) trong câu cho sẵn |
| A2 | Hiểu đoạn ngắn về đời sống hàng ngày | Thì phổ biến, từ high-frequency trong đoạn |
| B1 | Hiểu ý chính đoạn narrative/factual rõ | Kéo dài câu, liên từ phổ biến; suy ý đơn giản |
| B2 | Hiểu lập luận/quan điểm trong đoạn vừa | Cấu trúc phức hơn; suy ý, paraphrase |
| C1 | Hiểu ngụ ý, giọng điệu, chi tiết tinh | Sắc thái từ/cấu trúc nâng cao trong ngữ cảnh |

Constraints ví dụ (enforce bằng prompt + soft validate):

| Level | Passage length (chars) | Stem style |
|-------|----------------------|------------|
| A1–A2 | 120–400 | Câu hỏi trực tiếp, 1 ý |
| B1 | 250–700 | Main idea / detail / grammar in context |
| B2–C1 | 400–1200 | Inference / attitude / paraphrase (vẫn MCQ) |

### 1.2 Blueprint mix (mỗi lần generate `count`)

`book_type=reading_practice` hoặc `skill_type=reading`:

| Tỷ lệ | Dạng |
|-------|------|
| ~50% | `mcq` + `passage` — main idea / detail / inference (theo level) |
| ~25% | `cloze` + `passage` ngắn (1–2 câu thiếu chỗ trống) |
| ~25% | `mcq` + `passage` — vocab-in-context |

`book_type=grammar_textbook` hoặc `skill_type=grammar`:

| Tỷ lệ | Dạng |
|-------|------|
| ~50% | `mcq` + `passage` 1–3 câu từ sách (exemplar) |
| ~25% | `cloze` trong câu từ sách |
| ~25% | `fix_grammar` (câu lỗi lấy cảm hứng từ excerpt; stem gồm câu nguồn rút gọn) |

`test_bank` / `freeform`: mặc định như grammar; có thể refine sau.

### 1.3 JSON LLM (mở rộng)

```json
{
  "questions": [
    {
      "type": "mcq",
      "passage": "Exact or lightly trimmed excerpt sentences...",
      "stem": "According to the text, ...?",
      "options": ["A", "B", "C", "D"],
      "answer": "B",
      "explanation": "...",
      "skill": "reading",
      "difficulty": "medium",
      "cefr_focus": "main_idea"
    }
  ]
}
```

`passage` bắt buộc với blueprint reading/in-context; được phép `null` chỉ nếu sau này mở type thuần meta (phase 1: **không** cho null với mix trên).

---

## 2. Kiến trúc thay đổi

```text
get_unit_context (prefix|stride, budget theo CEFR)
  → build_cefr_generation_prompt(level, skill_type, book_type, blueprint, excerpt)
  → chat_json
  → validate_generated_questions (+ passage grounded)
  → save quiz_questions including passage
  → Admin/Learner UI render passage + stem
```

**Files chính:**

| File | Việc |
|------|------|
| `backend/app/services/cefr_descriptors.py` | **Tạo** — descriptors + length hints + blueprint mix |
| `backend/app/models/quiz_question.py` | Thêm `passage` |
| `backend/alembic/versions/..._add_quiz_passage.py` | Migration |
| `backend/app/schemas/quiz_schema.py` + onboarding schema | Expose `passage` |
| `backend/app/services/quiz_generation_service.py` | Prompt CEFR + validate + save |
| `backend/tests/test_quiz_generation_service.py` | Mở rộng |
| `backend/tests/test_cefr_descriptors.py` | **Tạo** |
| `frontend/.../BookQuizPanel.tsx` | Hiện passage trong draft list |
| `frontend/.../onboarding/placement/page.tsx` | Hiện passage trước stem |
| `frontend/my-app/lib/admin-quiz.ts` | Type `passage` |

---

## 3. Tasks triển khai

### Task 1: CEFR descriptors + blueprint helpers (TDD)

**Files:** `cefr_descriptors.py`, `tests/test_cefr_descriptors.py`

- [x] `get_can_do(level, skill_type) -> str`
- [x] `passage_length_range(level) -> tuple[int,int]`
- [x] `blueprint_for(book_type, skill_type, count) -> list[{type, requires_passage, cefr_focus}]`

```bash
cd backend && .venv/bin/python -m pytest tests/test_cefr_descriptors.py -v
```

Commit message gợi ý: `feat: add CEFR can-do descriptors and quiz blueprints`

---

### Task 2: Schema `passage` + API schemas

- [x] Column `passage = Column(TEXT, nullable=True)` trên `quiz_questions`
- [x] Alembic migration
- [x] `QuizQuestionOut` / admin list / onboarding question DTO có `passage: str | null`
- [x] Learner GET **không** trả `answer`; **có** trả `passage`

Commit: `feat: store optional passage stimulus on quiz questions`

---

### Task 3: Validate CEFR items (TDD)

Mở rộng `validate_generated_questions(items, *, excerpt, blueprint)`:

- [ ] Giữ rule MCQ cũ
- [ ] Nếu `requires_passage`: `passage` non-empty và `_passage_grounded(passage, excerpt)` (normalize + substring hoặc ratio ≥ 0.55 trên cửa sổ)
- [ ] Soft check độ dài passage theo level (warn log hoặc reject nếu quá lệch — MVP: reject nếu < min/2 hoặc > max*2)
- [ ] Reject item thiếu passage khi blueprint yêu cầu

Tests trong `test_quiz_generation_service.py`.

Commit: `feat: validate CEFR quiz items against excerpt grounding`

---

### Task 4: Rewrite generation prompt + wire service

- [ ] `SYSTEM_PROMPT` CEFR item writer: bám can-do, cấm câu grammar trừu tượng không passage, cấm bịa fact ngoài excerpt
- [ ] `build_generation_prompt(...)` nhận descriptors + blueprint JSON (số câu từng loại)
- [ ] `generate_quiz_for_skill`: load book `book_type`, skill `skill_type` / `cefr_level`; chọn context budget theo level; gọi validate mới; lưu `passage`
- [ ] Context mode: reading → ưu tiên `stride` hoặc prefix lớn hơn (`QUIZ_CONTEXT_MAX_CHARS` có thể tăng theo level, cap 8k)

Commit: `feat: CEFR-aware quiz generation with passage stimuli`

---

### Task 5: FE — hiện passage

- [ ] `BookQuizPanel`: mỗi draft hiện khối passage (muted) trên stem
- [ ] Placement page: hiện passage trước câu hỏi (typography rõ, không card-spam)
- [ ] Types TS cập nhật

Commit: `feat: show quiz passage stimulus in admin and placement UI`

---

### Task 6: Checklist thủ công

| Case | Kỳ vọng |
|------|---------|
| Generate skill reading / sách reading | Đa số câu có passage từ unit; ít MCQ “trời ơi” |
| Generate grammar textbook | Câu có exemplar từ sách; mix cloze/fix |
| A1 vs B2 cùng pipeline | Passage ngắn hơn / stem đơn hơn ở A1 (spot-check) |
| Placement | GET có `passage`; làm bài bình thường |
| Câu cũ (passage null) | UI vẫn ổn (chỉ hiện stem) |

```bash
cd backend && .venv/bin/python -m pytest \
  tests/test_cefr_descriptors.py \
  tests/test_quiz_generation_service.py -q
```

---

## 4. Ngoài scope / follow-up

| Mục | Ghi chú |
|-----|---------|
| Enum type `reading_mcq` riêng | Có thể không cần nếu dùng passage + mcq |
| CEFR vocab list (NGSL/CEFR-J) filter | Phase 2 quality gate |
| Human review rubric UI | Điểm can-do / bias |
| Listening items | Cần audio pipeline |
| Đổi công thức placement sang skill profile | Spec riêng |
| Auto-publish sau generate + gate | Plan riêng (đã bàn) |

---

## 5. Đối chiếu vấn đề đã nêu

| Vấn đề | Xử lý trong plan |
|--------|------------------|
| Câu rời, không kèm đoạn văn | `passage` + blueprint bắt buộc + UI |
| Thiếu đa dạng type | Blueprint mix theo book/skill |
| CEFR chỉ là nhãn | Can-do + constraints + validate length/grounding |
| Placement kém chất | Bank item tốt hơn; công thức điểm giữ nguyên |

---

## 6. Self-review plan

| Check | OK? |
|-------|-----|
| Quyết định thiết kế rõ trước code | Có §1 |
| Tasks nhỏ, TDD, file cụ thể | Có §3 |
| Không phá placement contract 10 câu | Có |
| Không over-scope listening/IRT | Có |
| Câu cũ nullable passage | Có |

---

## Bàn giao

Plan: `docs/superpowers/plans/2026-07-17-cefr-aligned-quiz-items.md`

**Hai cách chạy:**

1. **Subagent-Driven** — mỗi task một subagent  
2. **Inline Execution** — làm tuần tự trong session  

Bạn chọn cách nào? (Nhắc nếu muốn **không commit** như lần trước.)
