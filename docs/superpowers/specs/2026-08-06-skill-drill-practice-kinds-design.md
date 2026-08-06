# Thiết kế: Mở rộng ngân hàng skill-drill Practice (Category A, không audio)

**Ngày:** 2026-08-06  
**Trạng thái:** Implemented (FE kinds mới cần admin regen/publish để thấy trên browser)  
**Plan:** `docs/superpowers/plans/2026-08-06-skill-drill-practice-kinds.md`  
**Phụ thuộc:** Learn + Practice bám skill (`2026-08-02-skill-aligned-learn-practice-design.md`), Practice Promova UI  
**Ngoài phạm vi (để sau):** listening, speaking, TTS/ASR, phát âm, dictation từ audio, chấm peer  

---

## 1. Vấn đề

Gen admin `skill_drill` và Practice learner chủ yếu chỉ lộ **ba** `question_type` (`mcq`, `cloze`, `fix_grammar`). Blueprint đã có thêm `item_kind` như contrast / paraphrase / reading_target, nhưng:

1. Đa dạng vẫn hẹp so với drill Category A của app lớn (scramble, matching, tìm lỗi, multi-select…).
2. Câu **TOEIC Writing** đã publish (`question_type=writing`, `toeic_part=w*`) có thể lọt vào `GET /quiz/skills/{id}/questions` và làm hỏng Practice (ô 1 dòng + `grade_mcq`).
3. Spec 2026-08-02 **hoãn** `sentence_build` vì FE kéo-thả; sản phẩm giờ cần plan mở rộng cụ thể.

**Mục tiêu:** Bank **sinh và phục vụ** nhiều dạng drill **feedback tức thì** (Category A, chỉ chữ), trong khi writing / listening / speaking **không** nằm trên đường Practice cập nhật mastery tuần.

---

## 2. Mục tiêu / Không làm

### Mục tiêu

- Mở rộng **blueprint skill_drill + prompt LLM + validator** để mix thêm kind Category A.
- Mở rộng **FE Practice** để render + submit kind mới với đúng/sai tức thì.
- Giữ cập nhật mastery qua `apply_answer` / đúng-sai nhị phân (như hiện tại).
- **Loại** `writing` và TOEIC `w1|w2|w3` khỏi fetch câu Practice learner (và ưu tiên `task_brief.mode=skill_drill` khi đủ số câu).
- Chốt contract: mỗi kind map sang `question_type` + shape payload nào (ổn định cho FE + gen).

### Không làm

- Audio / TTS / ASR / speaking / dictation-từ-audio (Phase L+ sau).
- Chấm TOEIC Writing / rubric essay trong Practice.
- Thay generator placement / admin TOEIC.
- Đổi thuật toán spaced repetition.
- Thư viện kéo-thả native phức tạp — V1 chỉ tap token trên web.

---

## 3. Quyết định (đã chốt)

| Chủ đề | Quyết định |
|--------|------------|
| V1 kinds | Giữ 6 `item_kind` hiện có; **thêm** `sentence_build`, `matching`, `spot_error`, `multi_select`, `dialogue_complete`. `true_false` chỉ là **biến thể prompt của `form_choose`/`mcq`**, không tạo kind mới. |
| Enum `question_type` | **Alembic cộng thêm:** `sentence_build`, `matching`, `multi_select`. Tái dùng `mcq` cho `spot_error` + `dialogue_complete`. Giữ `writing` cho luồng khác; **không** phục vụ trên Practice. |
| Chấm điểm | Vẫn chuỗi (hoặc chuỗi đã canonicalize) qua `grade_answer()`; multi_select / matching / sentence_build chuẩn hóa trước khi so. |
| Mix blueprint | Theo `skill_type`, chèn kind mới (xem §5). Trần: `reading_target` ≤2; `matching` ≤1; `sentence_build` ≤2 mỗi batch 6–10. |
| Alignment | Cùng luật token-boundary target lesson 2026-08-02; áp trên stem/passage/answer/options + khóa matching đã serialize. |
| Tương tác FE | V1: tap-to-build (bấm token theo thứ tự), không lib kéo thả; matching = bấm trái rồi phải; multi_select = toggle chip. |
| Ship theo pha | Backend gen+API có thể ra draft trước FE; **đường learner không được lộ kind FE chưa render** — gate list API hoặc FE skip type lạ cho tới khi FE xong. |

---

## 4. Phân loại (V1)

| item_kind | question_type | UI learner | Hợp đồng `answer` (lưu DB) |
|-----------|---------------|------------|---------------------------|
| `form_choose` | `mcq` | nút option | text option đúng |
| `contrast` | `mcq` | nút option | text option đúng |
| `paraphrase` | `mcq` | nút option | text option đúng |
| `reading_target` | `mcq` | passage + options | text option đúng |
| `dialogue_complete` | `mcq` | thoại + options | text option đúng |
| `spot_error` | `mcq` | stem = câu; options = từ/cụm ứng viên | từ/cụm sai |
| `cloze_form` | `cloze` | ô trống hoặc options | chuỗi điền |
| `fix_grammar` | `fix_grammar` | hiện câu sai; gõ câu đúng | câu đã sửa |
| `sentence_build` | `sentence_build` | tap token (`options` = token xáo) | token nối bằng dấu cách |
| `matching` | `matching` | cặp: `options` dạng `["L\|R", …]` hoặc JSON `task_brief.pairs` | `left=>right;…` sort theo left |
| `multi_select` | `multi_select` | chọn nhiều | các option đúng sort, nối bằng ` \| ` |

**Để sau (không V1):** categorize/buckets, dịch, paraphrase viết tự do, dictation, `listen_*`, `speak_*`, task writing W1–W3 trên Practice.

---

## 5. Template blueprint (count≈6)

### grammar
`form_choose`, `cloze_form`, `fix_grammar`, `spot_error`, `sentence_build`, `contrast`

### vocabulary
`form_choose`, `form_choose`, `cloze_form`, `matching`, `sentence_build`, `reading_target`

### functional / reading
`dialogue_complete`, `form_choose`, `cloze_form`, `multi_select`, `paraphrase`, `reading_target`

Template vẫn cycle/cắt như hiện tại qua `blueprint_for_skill_drill`.

---

## 6. Hợp đồng payload

### 6.1 `sentence_build`

```json
{
  "type": "sentence_build",
  "item_kind": "sentence_build",
  "stem": "Build a correct sentence.",
  "options": ["student", "a", "am", "I"],
  "answer": "I am a student",
  "explanation": "…"
}
```

- `options` = túi token (V1 có thể ≤2 distractor; ưu tiên đúng multiset token của đáp án).
- FE submit chuỗi nối bằng dấu cách; chấm sau normalize unicode + gộp space + lower.

### 6.2 `matching`

```json
{
  "type": "matching",
  "item_kind": "matching",
  "stem": "Match each word to its meaning.",
  "options": ["because|reason", "so|result", "but|contrast"],
  "answer": "because=>reason;but=>contrast;so=>result"
}
```

- Ưu tiên dạng pipe trong `options` cho LLM đơn giản; server chuẩn hóa answer thành `left=>right` đã sort, nối bằng `;`.
- FE có thể đọc thêm `task_brief.pairs` nếu có (override tùy chọn).

### 6.3 `multi_select`

```json
{
  "type": "multi_select",
  "item_kind": "multi_select",
  "stem": "Which words are connectors?",
  "options": ["because", "happy", "so", "apple"],
  "answer": "because | so"
}
```

- Chấm: so set sau khi tách `|` / trim / lower.

### 6.4 `spot_error` / `dialogue_complete`

Vẫn là hàng `mcq`; prompt hướng dẫn LLM. `spot_error`: stem chứa câu sai; option đúng là từ sai.

---

## 7. API / chấm điểm

### 7.1 List câu Practice

`GET /api/v1/quiz/skills/{skill_id}/questions`:

- Filter `status=published`.
- **Loại** `question_type=writing`.
- **Loại** `toeic_part in (w1,w2,w3)` khi có giá trị.
- Ưu tiên hàng `task_brief.mode == "skill_drill"` khi số câu ≥ `limit`; không đủ thì fallback published không-writing (legacy).
- Chỉ trả type FE hỗ trợ (allowlist trùng bảng V1). Trả `item_kind` từ `task_brief` khi có (giúp label/layout FE).

### 7.2 Submit

Mở rộng helper chấm (giữ `grade_mcq` cho type so chuỗi):

```python
def grade_answer(question_type: str, expected: str, given: str) -> bool: ...
```

- `mcq` / `cloze` / `fix_grammar`: normalize hiện tại.
- `sentence_build`: normalize token/space.
- `matching`: parse hai phía thành tập cặp.
- `multi_select`: so set.

Mastery: không đổi `apply_answer`.

### 7.3 Admin generate

- Cập nhật template `blueprint_for_skill_drill` (§5).
- Cập nhật system/user prompt skill_drill kèm schema kind mới.
- Validate: khớp type/kind, số option (≥2 mcq, ≥3 token sentence_build, ≥2 cặp matching, ≥2 đúng multi_select), alignment ≥80%.
- Persist giá trị enum mới.

---

## 8. Frontend

| Bề mặt | Việc |
|--------|------|
| `QuizCard` | Nhánh render `sentence_build`, `matching`, `multi_select`; giữ mcq/cloze/fix_grammar |
| `lib/quiz.ts` | Types; `item_kind` tùy chọn; submit vẫn `{ question_id, answer: string }` |
| Trang Practice | Không đổi IA; có thể nhãn thân thiện hơn qua `quizTypeLabel` |
| Type lạ | Bỏ qua / ẩn + cảnh báo console nếu lọt API |

Nhãn gợi ý: “Build the sentence”, “Match”, “Choose all that apply”, “Find the mistake”.

---

## 9. Migration / rollout

1. Alembic thêm enum: `sentence_build`, `matching`, `multi_select`.
2. Ship lọc API (writing khỏi Practice) **trước hoặc cùng** FE — gỡ đau skill 259 hiện tại.
3. Ship grading + validator gen.
4. Ship renderer FE.
5. Admin regen `skill_drill` cho skill mục tiêu; publish.

Câu published cũ mcq/cloze/fix_grammar vẫn hợp lệ.

---

## 10. Tiêu chí nghiệm thu

1. Gen skill_drill skill grammar count=6 → blueprint có `sentence_build` và `spot_error` (assert blueprint; tỷ lệ draft LLM mang tính xác suất).
2. Practice learner **không** nhận `writing` / `w2`.
3. FE hoàn thành và chấm đúng ít nhất một item mỗi V1 `question_type`.
4. Mastery vẫn tăng/giảm theo đúng/sai.
5. Không thêm đường code audio/TTS.

---

## 11. Phase sau (ngoài task triển khai plan này)

- **Phase L:** listening MCQ / cloze-kèm-audio / dictation + TTS.  
- **Phase S:** speak / phát âm.  
- **Phase W:** làn Practice Writing (kiểu W2) + rubric AI, tách hoặc mastery nhẹ so với drill.

---

## 12. Liên quan

- `docs/superpowers/specs/2026-08-02-skill-aligned-learn-practice-design.md`  
- `docs/superpowers/plans/2026-08-06-skill-drill-practice-kinds.md`  
- `backend/app/services/skill_drill_blueprint.py`  
- `backend/app/api/quiz.py`  
- `frontend/my-app/components/practice/QuizCard.tsx`
