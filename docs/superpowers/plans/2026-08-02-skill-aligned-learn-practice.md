# Plan triển khai: Learn + Practice bám skill

> **Cho agent:** REQUIRED SUB-SKILL: Dùng `superpowers:subagent-driven-development` (khuyến nghị) hoặc `superpowers:executing-plans` để làm từng task. Các bước dùng checkbox (`- [x]`) để theo dõi.

**Mục tiêu:** Learn có micro-steps (kèm Form) và Practice quiz luyện đúng cùng skill targets như app ESL, chưa làm listening/speaking.

**Kiến trúc:** Mở rộng JSON lesson (`form`, `hook`, `exit_check`); thêm alignment thuần + blueprint `skill_drill`; gen quiz mặc định `skill_drill` (TOEIC qua `mode=toeic`); FE steps + render cloze/fix_grammar; cổng publish.

**Tech stack:** FastAPI, SQLAlchemy async, `chat_json`, Next.js (`LessonMiniUnit`, trang practice), pytest.

**Spec:** `docs/superpowers/specs/2026-08-02-skill-aligned-learn-practice-design.md`

> **Note (commits):** Tasks 1, 4, 5, 6 landed earlier in `5f38053` (align/blueprint/skill_drill gen + publish gate). Tasks 2–3, 7–9 are separate commits on this branch.

## Ràng buộc toàn cục

- Không listening / speaking / phát âm trong plan này
- Copy lesson/quiz chỉ English→English
- Schema lesson additive; lesson cũ không `form` vẫn serve được
- Dùng `quiz_questions.task_brief` cho meta drill với `mode=skill_drill` (không đè writing brief)
- Chỉ bật `cloze` / `fix_grammar` ở mode `skill_drill`; mode TOEIC vẫn mcq r5–r7
- UI sentence-build hoãn
- Hành vi `LEARN_UNIT_ENABLED` không đổi
- Complete week vẫn chỉ mastery ≥ 0.7
- Ngưỡng alignment batch ≥ 0.8; align theo **token/word-boundary**, không substring thô
- Grammar `skill_drill` **cần lesson published**; vẫn cần primary `book_skill_source`
- Chấm bài: `grade_mcq` (trim/lower) cho mcq/cloze/fix_grammar
- Đổi default `mode=skill_drill` là breaking với admin quen TOEIC — document rõ

---

## Bản đồ file

| File | Trách nhiệm |
|------|-------------|
| `backend/app/services/lesson_content_validate.py` | Normalize/validate content mở rộng + cổng form grammar |
| `backend/app/services/lesson_generation_service.py` | Prompt hook/form/passage ngắn hơn |
| `backend/app/services/skill_drill_align.py` | Pure `align_score` / `batch_align_ratio` |
| `backend/app/services/skill_drill_blueprint.py` | `blueprint_for_skill_drill(skill_type, count)` |
| `backend/app/services/quiz_generation_service.py` | `mode=skill_drill\|toeic`; prompt + validate skill_drill |
| `backend/app/schemas/quiz_schema.py` | `GenerateQuizRequest.mode` |
| `backend/app/api/admin_quiz.py` | Truyền `mode` |
| `frontend/my-app/lib/lesson.ts` | Types form/hook/exit_check |
| `frontend/my-app/components/lesson/LessonMiniUnit.tsx` | Micro-steps |
| `frontend/my-app/src/app/dashboard/practice/[skillId]/page.tsx` | UI cloze + fix_grammar |
| `frontend/my-app/lib/quiz.ts` | Types nếu cần |

---

### Task 1: Helper alignment (pure)

**Files:**
- Tạo: `backend/app/services/skill_drill_align.py`
- Test: `backend/tests/test_skill_drill_align.py`

**Interfaces:**
- Sinh ra: `align_score(item: dict, surfaces: set[str]) -> bool`, `batch_align_ratio(items: list[dict], surfaces: set[str]) -> float`

- [x] **Bước 1: Viết test fail trước**

```python
# backend/tests/test_skill_drill_align.py
from app.services.skill_drill_align import align_score, batch_align_ratio


def test_align_score_finds_surface_in_stem():
    assert align_score({"stem": "Choose: The store ___ big.", "answer": "is", "options": ["am", "is", "are"]}, {"is", "are"})


def test_align_score_false_when_missing():
    assert not align_score(
        {"stem": "What year was HBC founded?", "answer": "1670", "options": [], "passage": "A long story"},
        {"am", "is", "are"},
    )


def test_align_score_false_when_surface_inside_longer_word():
    # "is" must not match inside "history"
    assert not align_score(
        {"stem": "Canadian history", "answer": "x", "options": []},
        {"is"},
    )


def test_batch_ratio():
    items = [
        {"stem": "I ___ a student", "answer": "am", "options": ["am", "is"]},
        {"stem": "Unrelated reading trivia", "answer": "x", "options": []},
    ]
    assert batch_align_ratio(items, {"am"}) == 0.5
```

- [x] **Bước 2: Chạy test — kỳ vọng FAIL (import error)**

Chạy: `cd backend && PYTHONPATH=. .venv/bin/pytest tests/test_skill_drill_align.py -v`

- [x] **Bước 3: Implement**

```python
# backend/app/services/skill_drill_align.py
from __future__ import annotations

import re
from typing import Any


def _haystack(item: dict[str, Any]) -> str:
    parts = [
        str(item.get("stem") or ""),
        str(item.get("passage") or ""),
        str(item.get("answer") or ""),
    ]
    opts = item.get("options") or []
    if isinstance(opts, list):
        parts.extend(str(o) for o in opts)
    return " ".join(parts).lower()


def align_score(item: dict[str, Any], surfaces: set[str]) -> bool:
    text = _haystack(item)
    for s in surfaces:
        tok = str(s or "").strip().lower()
        if len(tok) < 2:
            continue
        if re.search(rf"(?<![a-z0-9]){re.escape(tok)}(?![a-z0-9])", text):
            return True
    return False


def batch_align_ratio(items: list[dict[str, Any]], surfaces: set[str]) -> float:
    if not items:
        return 0.0
    ok = sum(1 for it in items if align_score(it, surfaces))
    return ok / len(items)
```

- [x] **Bước 4: Chạy test — kỳ vọng PASS**

Chạy: `cd backend && PYTHONPATH=. .venv/bin/pytest tests/test_skill_drill_align.py -v`

- [x] **Bước 5: Commit** (chỉ khi user yêu cầu commit)

```bash
git add backend/app/services/skill_drill_align.py backend/tests/test_skill_drill_align.py
git commit -m "test: add skill-drill alignment helpers"
```

---

### Task 2: Lesson content — form / hook / exit_check

**Files:**
- Sửa: `backend/app/services/lesson_content_validate.py`
- Sửa: `backend/tests/test_lesson_content_validate.py`
- Sửa: `backend/app/services/lesson_generation_service.py` (prompt ở task này hoặc Task 3)

**Interfaces:**
- Dùng: `normalize_content` hiện có
- Sinh ra: content đã normalize có thể gồm `hook`, `form`, `exit_check`; `assert_publishable(content, *, skill_type: str | None = None)`

- [x] **Bước 1: Test fail cho cổng form**

```python
def test_normalize_keeps_form_rows():
    raw = {
        "passage": {"text": "I am happy. She is kind. They are friends."},
        "form": {
            "title": "Verb to be",
            "rows": [
                {"label": "I", "pattern": "am", "example": "I am happy."},
                {"label": "She", "pattern": "is", "example": "She is kind."},
            ],
        },
        "targets": [
            {"surface": "am", "gloss": "form of be for I"},
            {"surface": "is", "gloss": "form of be for he/she"},
            {"surface": "are", "gloss": "form of be for they"},
            {"surface": "happy", "gloss": "feeling good"},
        ],
        "checks": [
            {
                "type": "mcq",
                "prompt": "I ___ happy.",
                "options": ["am", "is", "are"],
                "answer": "am",
            }
        ],
        "writing": {"prompt": "Write two sentences with am/is."},
    }
    out = normalize_content(raw)
    assert out["form"]["rows"][0]["pattern"] == "am"


def test_assert_publishable_grammar_requires_form():
    raw = {
        "passage": {"text": "I am happy. She is kind. They are friends here."},
        "targets": [
            {"surface": "am", "gloss": "be for I"},
            {"surface": "is", "gloss": "be for she"},
            {"surface": "are", "gloss": "be for they"},
            {"surface": "happy", "gloss": "glad"},
        ],
        "checks": [
            {
                "type": "mcq",
                "prompt": "I ___ happy.",
                "options": ["am", "is", "are"],
                "answer": "am",
            }
        ],
        "writing": {"prompt": "Write two sentences with am/is."},
    }
    content = normalize_content(raw)
    with pytest.raises(ValueError, match="form"):
        assert_publishable(content, skill_type="grammar")
```

- [x] **Bước 2: Chạy — FAIL**

Chạy: `cd backend && PYTHONPATH=. .venv/bin/pytest tests/test_lesson_content_validate.py -v`

- [x] **Bước 3: Mở rộng `normalize_content`**

- Parse optional `hook` (string).
- Parse optional `form` với `title` + `rows` (label/pattern/example); bỏ pattern rỗng.
- Parse optional `exit_check` qua `_normalize_check` hiện có.
- Giữ hành vi legacy khi thiếu field.
- Đổi `assert_publishable(content, *, skill_type: str | None = None)`: nếu `skill_type == "grammar"` và thiếu/`form.rows` < 2 → `ValueError("grammar lessons require form with at least 2 rows")`.
- (Khuyến nghị) Nếu có targets: mỗi surface phải nằm trong passage (casefold) — lỗi rõ ràng.

- [x] **Bước 4: Cập nhật caller `publish_lesson`** truyền `skill.skill_type` vào `assert_publishable`.

- [x] **Bước 5: Test PASS + commit nếu được yêu cầu**

---

### Task 3: Prompt gen lesson (micro-steps)

**Files:**
- Sửa: `backend/app/services/lesson_generation_service.py`
- Sửa: `backend/tests/test_lesson_generation_service.py`

- [x] **Bước 1: Cập nhật `BASE_SYSTEM_PROMPT`** — JSON gồm `hook`, `form`, `exit_check` tùy chọn; passage **40–100 từ** theo CEFR; grammar phải có `form` 2–8 rows.

- [x] **Bước 2: Guidance grammar** trong `SKILL_TYPE_GUIDANCE["grammar"]`: passage phải showcase form; `form.rows` giải thích pattern bằng EN đơn giản.

- [x] **Bước 3: Test** `_build_system_prompt(skill_type="grammar")` chứa `"form"` và `"40-100"` hoặc `"40–100"`.

- [x] **Bước 4: Commit nếu được yêu cầu**

---

### Task 4: Blueprint skill-drill

**Files:**
- Tạo: `backend/app/services/skill_drill_blueprint.py`
- Test: `backend/tests/test_skill_drill_blueprint.py`

**Interfaces:**
- Sinh ra: `blueprint_for_skill_drill(skill_type: str, count: int) -> list[dict]` mỗi phần tử có `item_kind`, `question_type`

- [x] **Bước 1: Test fail**

```python
from app.services.skill_drill_blueprint import blueprint_for_skill_drill

def test_grammar_blueprint_length_and_kinds():
    bp = blueprint_for_skill_drill("grammar", 6)
    assert len(bp) == 6
    kinds = [b["item_kind"] for b in bp]
    assert kinds.count("reading_target") <= 2
    assert "form_choose" in kinds
    assert "fix_grammar" in kinds
```

- [x] **Bước 2: Implement** theo spec §6.2 (cắt/đệm đủ `count`).

- [x] **Bước 3: PASS + commit nếu được yêu cầu**

---

### Task 5: Gen quiz `mode=skill_drill`

**Files:**
- Sửa: `backend/app/services/quiz_generation_service.py`
- Sửa: `backend/app/schemas/quiz_schema.py` (`GenerateQuizRequest.mode: Literal["skill_drill","toeic"] = "skill_drill"`)
- Sửa: `backend/app/api/admin_quiz.py` (truyền `mode`)
- Test: `backend/tests/test_quiz_generation_skill_drill.py` (mock `chat_json`)

**Interfaces:**
- Dùng: `blueprint_for_skill_drill`, `batch_align_ratio`, targets lesson published nếu có
- Sinh ra: `generate_quiz_for_skill(..., mode: str = "skill_drill")`

- [x] **Bước 1: Thêm field request**

```python
class GenerateQuizRequest(BaseModel):
    count: int = Field(default=8, ge=1, le=15)
    mode: Literal["skill_drill", "toeic"] = "skill_drill"
```

- [x] **Bước 2: System prompt skill-drill** (constant mới) — viết drill ESL; liệt kê `item_kind` cho phép; bắt buộc targets trong item; không TOEIC R6/R7 trừ `reading_target`.

- [x] **Bước 3: Nhánh validate skill_drill:**
  - Cho phép `question_type` trong `{mcq, cloze, fix_grammar}`
  - Map `item_kind` blueprint → type
  - `toeic_part` nullable / bỏ
  - Lưu `task_brief={item_kind, alignment, surfaces, mode}`

- [x] **Bước 4: Sau validate**, nếu có surfaces và `batch_align_ratio < 0.8` → retry 1 lần rồi `ValueError` kèm ratio.

- [x] **Bước 5: Load surfaces** từ lesson published (`targets` + `form.rows[].pattern`). **Grammar:** không có lesson → `ValueError` (không gọi LLM). Vocab/functional/reading: fallback heuristic + `alignment=heuristic`.

- [x] **Bước 6: Giữ path TOEIC** khi `mode=="toeic"` (hành vi hiện tại).

- [x] **Bước 7: Test mock LLM** — cloze được chấp nhận ở skill_drill; align fail thì raise.

- [x] **Bước 8: Commit nếu được yêu cầu**

---

### Task 6: Cổng publish quiz theo alignment

**Files:**
- Sửa: `backend/app/api/admin_quiz.py` hàm `admin_publish_questions` (hoặc helper trong quiz service)

- [x] **Bước 1:** Khi publish, nếu `task_brief.mode == "skill_drill"` và có `task_brief.surfaces`, bỏ qua item fail `align_score` (đếm `skipped`); có thể trả thêm `skipped_alignment`.

- [x] **Bước 2: Test unit/API** hoặc test service với row giả.

- [x] **Bước 3: Commit nếu được yêu cầu**

---

### Task 7: FE types lesson + micro-steps

**Files:**
- Sửa: `frontend/my-app/lib/lesson.ts`
- Sửa: `frontend/my-app/components/lesson/LessonMiniUnit.tsx`

- [x] **Bước 1: Mở rộng types**

```ts
export type LessonForm = {
  title: string;
  rows: { label: string; pattern: string; example?: string }[];
};

export type LessonContent = {
  hook?: string | null;
  passage: { text: string; gloss?: string | null };
  form?: LessonForm | null;
  targets: LessonTarget[];
  checks: LessonCheck[];
  writing: { prompt: string; min_words: number; must_use: string[] };
  exit_check?: LessonCheck | null;
};
```

- [x] **Bước 2: Union step** `"hook" | "notice" | "form" | "meaning" | "check" | "write" | "feedback" | "exit"`

- [x] **Bước 3: Step ban đầu** = bước đầu có dữ liệu theo thứ tự hook→notice→form→meaning→check…

- [x] **Bước 4: Render Form** dạng bảng/list label / pattern / example.

- [x] **Bước 5: Bước Meaning** = chip targets (tách khỏi notice). Notice chỉ passage.

- [x] **Bước 6: Sau feedback**, nếu có `exit_check` thì `exit`, không thì `onFinished`.

- [x] **Bước 7: Kiểm tra tay** content legacy (không form) — bỏ qua bước form.

---

### Task 8: FE Practice cloze + fix_grammar

**Files:**
- Sửa: `frontend/my-app/src/app/dashboard/practice/[skillId]/page.tsx`
- Sửa: `frontend/my-app/lib/quiz.ts` nếu type chưa có cloze/fix_grammar

- [x] **Bước 1:** `question_type === "cloze"`: hiện stem + input (và nút options nếu `options?.length`).

- [x] **Bước 2:** `fix_grammar`: nhãn “Fix the sentence”, stem = câu sai, input = câu đúng; submit trim + không phân biệt hoa thường (server chấm).

- [x] **Bước 3:** Thủ công: gen skill_drill một skill grammar, publish, mở Practice — trả lời 1 cloze và 1 fix_grammar.

---

### Task 9: Smoke ops + docs

**Files:**
- Sửa: `backend/README.md` (gen quiz mặc định skill_drill; ghi chú `mode=toeic`)
- Tùy chọn: cập nhật Status spec → Sẵn sàng implement

- [x] **Bước 1:** Document flow admin: publish lesson → `POST .../generate` (skill_drill) → publish questions.

- [x] **Bước 2:** Smoke một skill A1 (`be_present` hoặc id biết trước): regen lesson, regen quiz, learner Learn→Practice kiểm tra alignment.

- [x] **Bước 3:** Đánh dấu spec **Accepted** sau khi user sign-off review.

---

## Checklist phủ spec

| Phần spec | Task |
|-----------|------|
| Hợp đồng / validator alignment | 1, 5, 6 |
| Schema lesson form/hook/exit | 2, 3, 7 |
| Grammar bắt buộc form khi publish | 2 |
| Blueprint skill_drill | 4 |
| Mode gen quiz + prompt | 5 |
| Cổng publish | 2, 6 |
| FE micro-steps | 7 |
| FE cloze/fix_grammar | 8 |
| Giữ TOEIC | 5 |
| Không listen/speak | Toàn cục |
| Meta task_brief | 5 |
| Rollout/docs | 9 |

## Quét placeholder

Không cố ý để TBD. Sentence-build đã hoãn rõ trong Ràng buộc toàn cục.
