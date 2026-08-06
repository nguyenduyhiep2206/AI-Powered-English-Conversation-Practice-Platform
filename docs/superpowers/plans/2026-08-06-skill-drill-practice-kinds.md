# Kế hoạch triển khai: Mở rộng loại câu skill-drill Practice

> **Dành cho agent:** BẮT BUỘC dùng skill `superpowers:subagent-driven-development` (khuyến nghị) hoặc `superpowers:executing-plans` để làm từng task. Các bước dùng checkbox (`- [ ]`) để theo dõi.

**Mục tiêu:** Mở rộng gen `skill_drill` và Practice learner để ngân hàng có thể sinh / phục vụ / chấm các dạng drill chữ Category A ngoài `mcq` / `cloze` / `fix_grammar`, cập nhật mastery — **không** làm audio / speaking / TTS trong plan này.

**Kiến trúc:** Giữ `task_brief.item_kind` làm nhãn sư phạm; mở rộng Postgres `quiz_question_type_enum` cho type lưu trữ mới; chuẩn hóa đáp án phía server; lọc Writing khỏi API Practice; bổ sung UI trong `QuizCard`. Listening / speaking / writing-lane để phase sau (xem spec).

**Công nghệ:** FastAPI, SQLAlchemy/Alembic, pipeline LLM quiz hiện có, Next.js Practice `QuizCard`.

**Spec:** `docs/superpowers/specs/2026-08-06-skill-drill-practice-kinds-design.md`

## Ràng buộc chung

- Không làm listening / speaking / TTS / ASR trong plan này
- Không trả `question_type=writing` hoặc `toeic_part=w1|w2|w3` cho danh sách Practice learner
- Giữ công thức mastery `apply_answer`; chỉ đổi cách tính `correct` theo từng type
- Migration mang tính cộng thêm; không phá câu published sẵn (`mcq` / `cloze` / `fix_grammar`)
- **Không** git commit trừ khi user yêu cầu rõ
- Alignment: luật token target lesson từ 2026-08-02 (≥80% batch)

## Bản đồ file

| File | Trách nhiệm |
|------|-------------|
| Tạo Alembic migration | Thêm enum `sentence_build`, `matching`, `multi_select` |
| Sửa `backend/app/models/enums.py` | Đồng bộ enum Python |
| Sửa `backend/app/services/skill_drill_blueprint.py` | Template blueprint mới |
| Sửa `backend/app/services/quiz_generation_service.py` | Schema prompt + validate kind mới |
| Sửa `backend/app/services/mastery_service.py` (hoặc tạo `quiz_grade.py`) | `grade_answer` |
| Sửa `backend/app/api/quiz.py` | Lọc list; gọi `grade_answer`; trả `item_kind` |
| Sửa `frontend/my-app/lib/quiz.ts` | Kiểu TypeScript |
| Sửa `frontend/my-app/components/practice/QuizCard.tsx` | UI dạng mới |
| Test trong `backend/tests/` | Blueprint, grade, lọc list |

---

### Task 1: Loại Writing khỏi feed Practice learner

**Files:**
- Sửa: `backend/app/api/quiz.py`
- Test: `backend/tests/test_quiz_practice_list.py` (tạo nếu chưa có)

**Vì sao làm trước:** Gỡ ngay lỗi UX Practice (câu email W2).

- [ ] **Bước 1: Lọc query**

Trong `list_published_questions`, sau filter `status`:

```python
from app.models.enums import QuizQuestionTypeEnum, ToeicPartEnum

q = q.where(QuizQuestionDB.question_type != QuizQuestionTypeEnum.writing)
# Đồng thời loại toeic writing parts khi có cột:
q = q.where(
    (QuizQuestionDB.toeic_part.is_(None))
    | (QuizQuestionDB.toeic_part.notin_([
        ToeicPartEnum.w1, ToeicPartEnum.w2, ToeicPartEnum.w3
    ]))
)
```

Ưu tiên `skill_drill` khi đủ số câu (tuỳ chọn ở task này; bắt buộc ở Task 5 nếu chưa làm):

```python
# Pseudo: if count(skill_drill published) >= limit → filter task_brief['mode'] == 'skill_drill'
```

Trả thêm `item_kind` khi `task_brief` là dict:

```python
"item_kind": (r.task_brief or {}).get("item_kind") if isinstance(r.task_brief, dict) else None,
```

- [ ] **Bước 2: Test**

Assert không bao giờ trả hàng `writing`. Chạy:

`cd backend && pytest tests/test_quiz_practice_list.py -q`

---

### Task 2: Alembic + enum cho question type mới

**Files:**
- Tạo: `backend/alembic/versions/<rev>_add_skill_drill_question_types.py`
- Sửa: `backend/app/models/enums.py`

- [ ] **Bước 1: Mở rộng enum Python**

```python
class QuizQuestionTypeEnum(str, enum.Enum):
    mcq = "mcq"
    cloze = "cloze"
    fix_grammar = "fix_grammar"
    writing = "writing"
    sentence_build = "sentence_build"
    matching = "matching"
    multi_select = "multi_select"
```

- [ ] **Bước 2: Migration (Postgres)**

Dùng `ALTER TYPE quiz_question_type_enum ADD VALUE IF NOT EXISTS 'sentence_build'` (và `matching`, `multi_select`). Bám pattern migration enum sẵn có trong repo.

- [ ] **Bước 3: Upgrade DB local/docker**

`alembic upgrade head` (ghi chú; agent chạy nếu môi trường sẵn)

---

### Task 3: Helper `grade_answer`

**Files:**
- Ưu tiên tạo: `backend/app/services/quiz_grade.py`
- Sửa: `backend/app/api/quiz.py` để gọi helper
- Test: `backend/tests/test_quiz_grade.py`

**Interfaces:**

```python
def normalize_space_lower(s: str) -> str: ...

def grade_answer(question_type: str, expected: str, given: str) -> bool: ...

def canonicalize_matching_answer(raw: str) -> str:
    """Parse 'a=>b;c=>d' hoặc dòng 'a|b' → 'a=>b;c=>d' đã sort."""

def canonicalize_multi_select(raw: str) -> set[str]:
    """Tách theo | hoặc ; → set đã trim + lower."""

def canonicalize_sentence_build(raw: str) -> str:
    """Gộp whitespace, lower."""
```

- [ ] **Bước 1: TDD — viết test fail trước cho matching / multi_select / sentence_build / parity mcq**

- [ ] **Bước 2: Implement đến khi test xanh**

- [ ] **Bước 3: Nối `submit_answer` sang `grade_answer(...)`**

---

### Task 4: Template blueprint

**Files:**
- Sửa: `backend/app/services/skill_drill_blueprint.py`
- Test: `backend/tests/test_skill_drill_blueprint.py` (tạo/mở rộng)

- [ ] **Bước 1: Đổi template theo spec §5**

List grammar / vocab / default phải emit kind mới với trần:

- `reading_target` ≤ 2  
- `matching` ≤ 1  
- `sentence_build` ≤ 2  

- [ ] **Bước 2: Assert `blueprint_for_skill_drill("grammar", 6)` có `spot_error` và `sentence_build`**

---

### Task 5: Prompt gen + validation

**Files:**
- Sửa: `backend/app/services/quiz_generation_service.py` (prompt skill_drill + `validate_skill_drill_questions`)
- Test: unit test validator với fixture JSON giả LLM

- [ ] **Bước 1: Mô tả JSON shape trong system prompt cho `sentence_build`, `matching`, `multi_select`, `spot_error`, `dialogue_complete`**

- [ ] **Bước 2: Validate cặp kind ↔ type**

| item_kind | type bắt buộc | min options | thêm |
|-----------|---------------|-------------|------|
| sentence_build | sentence_build | ≥3 token | token đáp án ⊆ options (cho phép bằng) |
| matching | matching | ≥2 `L\|R` | cặp answer khớp |
| multi_select | multi_select | ≥3 options | ≥2 đúng trong tập answer |
| spot_error | mcq | ≥2 | — |
| dialogue_complete | mcq | ≥2 | — |

- [ ] **Bước 3: Persist `question_type` từ item đã validate; set `task_brief.mode=skill_drill`, `item_kind`, `surfaces`**

- [ ] **Bước 4: Ưu tiên skill_drill ở list endpoint nếu chưa làm ở Task 1**

---

### Task 6: Frontend types + QuizCard — `sentence_build`

**Files:**
- Sửa: `frontend/my-app/lib/quiz.ts`
- Sửa: `frontend/my-app/components/practice/QuizCard.tsx`

- [ ] **Bước 1: Mở rộng type**

```ts
question_type: string; // gồm sentence_build | matching | multi_select
item_kind?: string | null;
```

- [ ] **Bước 2: UI**

- Ngân hàng token bấm được từ `options`
- Chip câu đang dựng + hoàn tác
- Submit `answer = builtTokens.join(" ")`
- Nhãn: “Build the sentence” (hoặc “Sắp xếp thành câu”)

- [ ] **Bước 3: Verify tay trên câu seeded/published (hoặc mock)**

---

### Task 7: Frontend — `matching` + `multi_select`

**Files:**
- Sửa: `QuizCard.tsx`

- [ ] **Bước 1: matching**

Parse `options` dạng `"left|right"`. Cột trái + cột phải đã xáo; bấm trái rồi bấm phải để ghép. Serialize submit dạng chuẩn `left=>right;...` (sort theo left) — **ưu tiên FE gửi đúng form canonical như server**.

- [ ] **Bước 2: multi_select**

Toggle nhiều option; submit `selected.sort().join(" | ")` (lower tuỳ chọn — server canonicalize).

- [ ] **Bước 3: Nhãn trong `quizTypeLabel`**

```ts
case "sentence_build": return "Build the sentence";
case "matching": return "Match";
case "multi_select": return "Choose all that apply";
```

`spot_error` / `dialogue_complete` vẫn hiện dưới Multiple choice; có thể thêm eyebrow từ `item_kind`.

---

### Task 8: Nghiệm thu end-to-end

- [ ] **Bước 1: API** — List Practice skill từng trả W2 → không còn writing
- [ ] **Bước 2: Admin gen** — `skill_drill` count=6 skill grammar → draft có kind mới (hoặc blueprint smoke)
- [ ] **Bước 3: FE** — làm lần lượt mcq, cloze, fix_grammar, sentence_build, matching, multi_select; mastery đổi
- [ ] **Bước 4: Xác nhận không thêm dependency audio/TTS**

---

## Tự rà (plan ↔ spec)

| Spec | Task |
|------|------|
| Lọc writing khỏi Practice | Task 1 |
| Enum type mới | Task 2 |
| Chấm điểm | Task 3 |
| Mix blueprint | Task 4 |
| Gen + validate | Task 5 |
| FE sentence_build | Task 6 |
| FE matching + multi_select | Task 7 |
| spot_error / dialogue_complete | Gen dạng mcq (Task 4–5); FE tái dùng mcq |
| Nghiệm thu | Task 8 |
| Audio/speak sau | Chỉ ghi trong spec |

---

## Handoff thực thi

Đã lưu:

- Spec: `docs/superpowers/specs/2026-08-06-skill-drill-practice-kinds-design.md`
- Plan: `docs/superpowers/plans/2026-08-06-skill-drill-practice-kinds.md`

**V1 kinds (đã chốt):** giữ 6 kind hiện có + thêm `sentence_build`, `matching`, `spot_error`, `multi_select`, `dialogue_complete` (`true_false` = biến thể mcq). Audio / speaking / TTS = Phase L/S sau.

**Hai cách chạy:**

1. **Subagent-Driven (khuyến nghị)** — mỗi task một subagent  
2. **Inline Execution** — làm trong session, checkpoint sau Task 1, 5, 7
