# Thiết kế: LLM verifier cho skill-drill (giữ validate cấu trúc)

**Ngày:** 2026-08-06  
**Trạng thái:** Implemented (V1: spot_error + fix_grammar; tắt bằng `SKILL_DRILL_LLM_VERIFY=false`)  
**Plan:** `docs/superpowers/plans/2026-08-06-skill-drill-llm-verifier.md`  
**Ngoài phạm vi V1:** bỏ hết rule validate hiện tại; verify TOEIC RC; verify lúc publish hàng loạt cho bank cũ (có thể Phase 2)

---

## 1. Vấn đề

Gen skill-drill bằng LLM hay tạo câu **đúng ngữ pháp** nhưng vẫn gắn đáp án “lỗi” (`spot_error`), hoặc explanation tự mâu thuẫn (`Error: works / Correct: works`). Vá prompt/regex theo từng thì (hiện tại / quá khứ / tương lai…) **không scale**.

**Mục tiêu:** thêm lớp **LLM verifier** sau gen để chặn lỗi chất lượng ngữ pháp/đáp án, trong khi **giữ** validate cấu trúc (schema, options, blank, align targets).

---

## 2. Quyết định đã chốt

| Chủ đề | Quyết định |
|--------|------------|
| Bỏ hết validate hiện tại? | **Không.** Giữ cấu trúc + align; verifier chỉ cho chất lượng ngôn ngữ / đúng-sai đáp án. |
| Model | Cùng `chat_json` / `OPENAI_MODEL` (temperature thấp hơn gen, ideally `0`–`0.2`). |
| Phạm vi V1 | Chỉ **`item_kind=spot_error`** (và tùy chọn `fix_grammar`). Các kind khác V1 chỉ chạy rule hiện tại. |
| Khi nào gọi | Sau `validate_skill_drill_questions` (rule pass), **trước** `_persist_draft_questions`. |
| Batch | **Một call verify cho cả batch** (list câu) để giảm latency/cost; không 1 call/câu trừ khi batch fail parse. |
| Fail verifier | **Loại câu đó** khỏi batch; nếu còn quá ít câu (< `max(2, count//2)`) thì **retry gen** (đã có vòng retry) hoặc raise như hiện tại. |
| Regex habit/now | **Giữ tạm** làm prefilter rẻ; không mở rộng theo thì mới — verifier là lớp chính cho ngữ pháp. |
| Publish bank cũ | V1 **không** bắt buộc re-verify; admin unpublish tay câu xấu. Phase 2: nút “Re-verify drafts”. |

---

## 3. Pipeline

```
LLM gen (skill_drill)
    → validate cấu trúc + align (giữ nguyên)
    → filter kinds cần verify (V1: spot_error [+ fix_grammar])
    → LLM verifier (JSON pass/fail từng id tạm / index)
    → chỉ persist câu pass (các kind không verify đi thẳng)
```

Kinds không thuộc V1 verifier: bỏ qua bước LLM, vẫn lưu nếu rule OK.

---

## 4. Hợp đồng verifier

### Input (user message)

Với mỗi item (sau rule validate):

- `index` (0-based trong batch verify)
- `item_kind`, `question_type`
- `stem`, `options`, `answer`, `explanation` (nếu có)
- `skill_title`, `cefr` (context ngắn)

### System (ý chính)

Bạn là giám khảo ESL. Với `spot_error`: stem phải có **đúng một** lỗi tiếng Anh thật; `answer` phải là phần **sai**; các option còn lại phải **đúng trong ngữ cảnh**; explanation không được nói câu đúng / Error≡Correct. Trả JSON only.

### Output

```json
{
  "results": [
    {
      "index": 0,
      "pass": false,
      "reason": "Sentence is grammatical; works is correct present simple for habit."
    }
  ]
}
```

- Thiếu `results` / index lệch → coi **cả batch verify fail nhẹ**: retry 1 lần verifier; vẫn lỗi thì **fail-open chỉ với kinds không critical** — **V1 chọn fail-closed cho spot_error** (không persist item không có verdict `pass: true`).
- Item không có trong `results` → treat as **fail**.

### Câu hỏi verify theo kind

**spot_error**

1. Stem có đúng một lỗi thật?  
2. `answer` có phải đúng chỗ lỗi không?  
3. Ba option kia có đúng trong câu không?  
4. Explanation có mâu thuẫn (bảo câu đúng / Error=Correct) không?

**fix_grammar** (nếu bật cùng V1)

1. Stem có lỗi?  
2. `answer` có phải bản sửa đúng và tự nhiên không?

---

## 5. Tích hợp code (đề xuất)

- Module mới: `backend/app/services/skill_drill_verifier.py`
  - `VERIFY_SYSTEM_PROMPT`
  - `verify_skill_drill_items(items: list[dict], *, skill_title, cefr) -> list[dict]`  
    (trả lại subset `pass`)
- Gọi từ `_request_skill_drill_items` sau `validate_skill_drill_questions`, trước check `len(best)`.
- Log/metric nhẹ: số rejected + reason (app log), không bắt buộc lưu DB V1.
- Optional `task_brief["verified"] = True` trên item pass (hữu ích admin sau này).

### Config

- Env/flag: `SKILL_DRILL_LLM_VERIFY=1` (default on khi implement) để tắt khi dev offline.
- Không thêm dependency mới.

---

## 6. Test

- Unit: mock `chat_json` — reject câu “works… but today… is staying” / “is drinking… usually works”; accept “My father work … is staying”.
- Unit: item không spot_error không gọi verifier (mock assert).
- Unit: verifier omit index → item bị drop.
- Không bắt buộc E2E LLM thật trong CI.

---

## 7. Chi phí / rủi ro

- **+1 LLM call / lần gen** (batch). Gen 10 câu, ~1–2 spot_error trong blueprint → call vẫn 1 lần cho các câu cần verify.
- Verifier cũng có thể sai (false reject) → giảm yield gen; retry gen đã có giảm thiểu.
- Không dùng verifier thay `align_score` / publish skip alignment.

---

## 8. Phase sau (không làm trong V1)

- Mở rộng verify: `cloze_form`, `multi_select`, `sentence_build`.
- Admin “Re-verify selected drafts”.
- Model riêng / temperature 0 riêng nếu cần.
- Tắt dần regex contrast khi verifier ổn định trên production.

---

## 9. Tiêu chí xong V1

1. Spec được duyệt.  
2. Gen skill_drill: `spot_error` không pass verifier thì không vào draft.  
3. Các kind khác + rule cấu trúc hoạt động như cũ.  
4. Test mock phủ pass/fail/omit.
