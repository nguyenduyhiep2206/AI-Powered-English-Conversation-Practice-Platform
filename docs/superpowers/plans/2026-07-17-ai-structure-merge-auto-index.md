# Kế hoạch triển khai: Heuristic detect-all + AI merge → gate → auto-index

> **Dành cho agent/kỹ sư thực hiện:** BẮT BUỘC dùng skill `superpowers:subagent-driven-development` (khuyên dùng) hoặc `superpowers:executing-plans` để làm từng task. Các bước dùng checkbox (`- [ ]`) để theo dõi tiến độ.

**Mục tiêu:** Giữ Toc + Regex + Font, nhưng **không early-return một detector**. Thu thập mọi candidate → **AI merge** (kết hợp candidates + skim text sách) → **gate verify** (chống báo láo) → **pass thì auto chunk+embed** (không bắt admin Confirm). Fail gate → `failed` hoặc `needs_review` + Retry.

**Kiến trúc:**

```text
Upload
  → Background: detect_all(Toc, Regex, Font)
  → AI merge (gpt-4o-mini / OPENAI_MODEL) → 1 DetectionResult method=ai_merge
  → structure_gate (title∈page, pages hợp lệ, coverage/sanity)
  → PASS: lưu preview + status=processing + BackgroundTasks index_book
  → FAIL: không index; status=failed|needs_review; admin Retry detect
           (Confirm & index vẫn giữ làm lối thoát thủ công nếu còn units)
```

**Công nghệ:** FastAPI `BackgroundTasks`, detectors hiện có, `chat_json` (`llm_client`), pdfplumber skim, Next.js admin labels.

**Không làm trong plan này:** Bỏ hẳn Toc/Regex/Font; edit unit trên UI; AI vision từng trang scan; Celery/ARQ; auto-publish quiz.

**Phụ thuộc / liên quan:** Plan ingest UX `2026-07-16-book-ingest-market-pipeline.md` (poll upload, Retry detect). Plan này **đổi ý nghĩa** `needs_review`: không còn bước Confirm bắt buộc trên happy path.

---

## Quyết định đã chốt

| Chủ đề | Quyết định |
|--------|------------|
| Detectors | Giữ 3 cái; thêm `detect_all()` — chạy hết, không early-exit |
| AI role | Merge/trọng tài từ candidates + skim; không invent unit không ground được |
| Gate | Fail-closed: fail → không index |
| Review người | Không bắt buộc khi gate pass |
| Confirm API | Giữ; dùng khi gate fail nhưng vẫn có units / sách cũ |
| Model | `settings.OPENAI_MODEL` (default `gpt-4o-mini`) |
| Flag | `STRUCTURE_AI_MERGE_ENABLED=true` (default on khi có `OPENAI_API_KEY`; off → behavior cũ: chain first-hit + `needs_review`) |

---

## Target UX

```text
Admin Upload PDF
  → “Detecting & merging structure…”
  → PASS: “Indexing…” → Ready (có units trong preview read-only)
  → FAIL: badge Failed / Needs review + Retry detect
           (optional Confirm nếu còn units hợp lệ thủ công)
```

---

## Bản đồ file

| File | Vai trò |
|------|---------|
| `backend/app/services/book_structure/detector_chain.py` | Thêm `detect_all` |
| `backend/app/services/book_structure/structure_gate.py` | **Tạo** — pure validate |
| `backend/app/services/book_structure/ai_merge_service.py` | **Tạo** — skim + LLM merge |
| `backend/app/services/book_structure_service.py` | Wire detect_all → merge → gate → auto-index |
| `backend/app/core/config.py` | Flag + optional skim limits |
| `backend/app/api/admin_books.py` | Job detect xong có thể schedule `index_book` |
| `backend/tests/test_detector_chain.py` | `detect_all` trả nhiều kết quả |
| `backend/tests/test_structure_gate.py` | **Tạo** |
| `backend/tests/test_ai_merge_service.py` | **Tạo** — mock `chat_json` |
| `backend/tests/test_book_structure_auto_index.py` | **Tạo** — status sau gate pass/fail |
| `frontend/my-app/lib/admin-books.ts` | Labels status |
| `frontend/my-app/src/app/admin/books/page.tsx` | Copy UX: Confirm không còn primary trên happy path |

---

### Task 1: `detect_all` — thu thập mọi candidate (TDD)

**Files:**
- Sửa: `backend/app/services/book_structure/detector_chain.py`
- Sửa: `backend/tests/test_detector_chain.py`

- [ ] **Bước 1: Viết test**

```python
def test_detect_all_returns_every_non_none_result(junk_toc_with_numbered_caps_pdf):
    chain = StructureDetectorChain()
    results = chain.detect_all(str(junk_toc_with_numbered_caps_pdf))
    methods = {r.method for r in results}
    # Toc rejects junk → None; Regex finds numbered caps
    assert "regex" in methods
    assert all(r.units for r in results)


def test_detect_still_early_returns_for_backward_compat(toc_pdf):
    result = StructureDetectorChain().detect(str(toc_pdf))
    assert result is not None
    assert result.method == "toc"
```

- [ ] **Bước 2: Chạy — FAIL** (chưa có `detect_all`)

```bash
cd backend && .venv/bin/python -m pytest tests/test_detector_chain.py -v
```

- [ ] **Bước 3: Implement**

```python
def detect_all(self, pdf_path: str) -> list[DetectionResult]:
    results: list[DetectionResult] = []
    for detector in self.detectors:
        result = detector.detect(pdf_path)
        if result is not None and result.units:
            results.append(result)
    return results
```

Giữ `detect()` như cũ (early-return) cho test/legacy.

- [ ] **Bước 4: PASS + commit**

```bash
git add backend/app/services/book_structure/detector_chain.py backend/tests/test_detector_chain.py
git commit -m "$(cat <<'EOF'
feat: collect all structure detector candidates via detect_all

EOF
)"
```

---

### Task 2: Structure gate (pure, không LLM)

**Files:**
- Tạo: `backend/app/services/book_structure/structure_gate.py`
- Tạo: `backend/tests/test_structure_gate.py`

**Rules (MVP):**

1. `2 ≤ len(units) ≤ 80`
2. Mỗi unit: `1 ≤ page_start ≤ page_end ≤ total_pages`
3. Sau sort theo `page_start`: không overlap nghiêm trọng (`next.start < prev.end` chỉ cho phép overlap 0 trang — tức `next.start >= prev.end` hoặc `== prev.end+1` tùy chọn; MVP: `page_start` tăng nghiêm ngặt, `page_end` của unit i = `page_start(i+1)-1` có thể **chuẩn hóa** trước gate hoặc reject overlap `start_b <= end_a` với `start_b < start_a` không xảy ra)
4. **Grounding:** với `page_texts[page_start-1]`, title (normalize) phải là substring hoặc fuzzy ratio ≥ 0.6 trên **đầu trang** (500 ký tự đầu) — trừ số trang footer
5. Reject nếu ≥ 50% title match junk outline keywords (reuse pattern tương tự `JUNK_OUTLINE_RE` trong toc_detector — import shared hoặc copy tối thiểu)

- [ ] **Bước 1: Test**

```python
def test_gate_rejects_empty():
    ok, reasons = validate_structure([], total_pages=10, page_texts=[""] * 10)
    assert ok is False

def test_gate_accepts_grounded_units():
    pages = ["1\nTHE OLD MAN WAITS\nbody", "more body", "3\nMAX THE CAT\nbody"]
    units = [
        DetectedUnit("1. THE OLD MAN WAITS", 1, 2),
        DetectedUnit("3. MAX THE CAT", 3, 3),
    ]
    ok, reasons = validate_structure(units, total_pages=3, page_texts=pages)
    assert ok is True
    assert reasons == []

def test_gate_rejects_ungrounded_title():
    pages = ["hello world only", "page two"]
    units = [
        DetectedUnit("Chapter 99 Not Real", 1, 1),
        DetectedUnit("Also Fake", 2, 2),
    ]
    ok, _ = validate_structure(units, total_pages=2, page_texts=pages)
    assert ok is False
```

- [ ] **Bước 2: FAIL rồi implement `validate_structure(...) -> tuple[bool, list[str]]`**

- [ ] **Bước 3: PASS + commit**

```bash
git commit -m "$(cat <<'EOF'
feat: add structure gate to reject ungrounded AI/heuristic units

EOF
)"
```

---

### Task 3: AI merge service (mock LLM trong test)

**Files:**
- Tạo: `backend/app/services/book_structure/ai_merge_service.py`
- Tạo: `backend/tests/test_ai_merge_service.py`
- Sửa: `backend/app/core/config.py` — flags

**Config mới:**

```python
STRUCTURE_AI_MERGE_ENABLED: bool = True
STRUCTURE_SKIM_LINES_PER_PAGE: int = 12
STRUCTURE_SKIM_MAX_PAGES: int = 400
```

**API:**

```python
def skim_pdf_headings(pdf_path: str, *, lines_per_page: int, max_pages: int) -> list[str]:
    """Return page_texts truncated to first N non-empty lines (for LLM + gate)."""

def merge_structure_with_ai(
    pdf_path: str,
    candidates: list[DetectionResult],
    *,
    total_pages: int,
) -> DetectionResult:
    """
    Build user prompt with JSON candidates + skim.
    chat_json → parse units → DetectionResult(method='ai_merge', confidence=0.85).
    Raise ValueError if LLM/JSON invalid.
    """
```

**System prompt (ý chính):**
- Bạn là trọng tài cấu trúc sách ESL/PDF.
- Input: nhiều đề xuất detector + text đầu mỗi trang.
- Output JSON: `{ "units": [ {"title", "page_start", "page_end"} ] }`.
- Ưu tiên chọn/sửa từ candidates; chỉ thêm unit khi heading xuất hiện trong skim.
- Bỏ accessibility / contents junk.
- `page_end` của unit cuối = `total_pages`; các unit trước = `next.page_start - 1`.

- [ ] **Bước 1: Test với monkeypatch `chat_json`**

```python
def test_merge_builds_result_from_llm(monkeypatch, numbered_caps_passage_pdf):
    from app.services.book_structure import ai_merge_service as mod

    def fake_chat_json(system, user):
        return {
            "units": [
                {"title": "1. THE OLD MAN WAITS AT THE POST OFFICE", "page_start": 1, "page_end": 1},
                {"title": "2. DON’T WEAR HEADPHONES WHILE DRIVING", "page_start": 2, "page_end": 2},
                {"title": "3. MAX THE CAT", "page_start": 3, "page_end": 3},
            ]
        }

    monkeypatch.setattr(mod, "chat_json", fake_chat_json)
    candidates = StructureDetectorChain().detect_all(str(numbered_caps_passage_pdf))
    result = merge_structure_with_ai(str(numbered_caps_passage_pdf), candidates, total_pages=3)
    assert result.method == "ai_merge"
    assert len(result.units) == 3
```

- [ ] **Bước 2: Implement skim + merge**

Dùng `pdfplumber` giống regex_detector. Temperature thấp: gọi `chat_json` hiện tại (0.3) chấp nhận được; optional follow-up hạ temperature riêng sau.

- [ ] **Bước 3: PASS + commit**

```bash
git commit -m "$(cat <<'EOF'
feat: AI merge service to reconcile structure detector candidates

EOF
)"
```

---

### Task 4: Wire pipeline — detect → merge → gate → auto-index

**Files:**
- Sửa: `backend/app/services/book_structure_service.py`
- Sửa: `backend/app/api/admin_books.py` (nếu schedule index từ API layer)
- Tạo: `backend/tests/test_book_structure_auto_index.py`

**Logic `detect_book_structure` (happy path mới):**

```text
candidates = detect_all(pdf)
if not candidates and no OPENAI: 422 như cũ

if STRUCTURE_AI_MERGE_ENABLED and OPENAI_API_KEY:
    try:
        merged = merge_structure_with_ai(...)
    except Exception:
        # fallback: pick best candidate by (len(units), confidence) như chain cũ
        merged = pick_best_candidate(candidates)
else:
    merged = pick_best_candidate(candidates)  # hoặc StructureDetectorChain.detect()

page_texts = skim full lines for gate (có thể reuse skim hoặc extract_text đầy đủ hơn cho grounding)
ok, reasons = validate_structure(merged.units, total_pages, page_texts)

lưu preview rows (method=merged.method)

if ok:
    book.status = processing
    # caller schedules index_book
    return summary, should_index=True
else:
    book.status = needs_review   # còn units để admin Confirm thủ công
    # hoặc failed nếu units rỗng sau gate — MVP: needs_review + log reasons
    return summary, should_index=False
```

**Đổi `status_after_successful_detect`:** không còn luôn `needs_review`. Thay bằng helper:

```python
def status_after_structure_decision(*, gate_ok: bool) -> BookStatusEnum:
    return BookStatusEnum.processing if gate_ok else BookStatusEnum.needs_review
```

Cập nhật / thay `tests/test_book_structure_status.py` cho khớp.

**Background job:**

```python
async def detect_book_structure_job(book_id: int) -> None:
    async with AsyncSessionLocal() as db:
        summary, should_index = await detect_book_structure(db, book_id)  # đổi return
    if should_index:
        await index_book(book_id)  # đã là async background-style entry
```

Hoặc API upload giữ `BackgroundTasks`: detect job tự gọi `index_book` bên trong khi pass (giống pattern hiện tại `index_book` mở session riêng) — **khuyến nghị** để upload route không cần biết gate.

- [ ] **Bước 1: Test** mock merge + gate

```python
@pytest.mark.asyncio
async def test_gate_pass_sets_processing_and_flags_index(monkeypatch):
    ...
    assert should_index is True
    assert book.status == BookStatusEnum.processing

@pytest.mark.asyncio
async def test_gate_fail_sets_needs_review_no_index(monkeypatch):
    ...
    assert should_index is False
    assert book.status == BookStatusEnum.needs_review
```

(Dùng DB test fixture có sẵn trong repo nếu có; nếu nặng thì unit-test helper quyết định status + `should_index` thuần trước, integration mỏng sau.)

- [ ] **Bước 2: Implement wire**

- [ ] **Bước 3: Regression detectors + gate + merge**

```bash
cd backend && .venv/bin/python -m pytest \
  tests/test_detector_chain.py \
  tests/test_structure_gate.py \
  tests/test_ai_merge_service.py \
  tests/test_book_structure_status.py \
  tests/test_book_structure_auto_index.py \
  tests/test_toc_detector.py \
  tests/test_regex_detector.py -q
```

- [ ] **Bước 4: Commit**

```bash
git commit -m "$(cat <<'EOF'
feat: auto-index books after AI-merged structure passes gate

EOF
)"
```

---

### Task 5: Admin FE — labels & primary CTA

**Files:**
- Sửa: `frontend/my-app/lib/admin-books.ts`
- Sửa: `frontend/my-app/src/app/admin/books/page.tsx`

- [ ] **Bước 1: Labels**

| Status | Label gợi ý |
|--------|-------------|
| `uploaded` | Detecting & merging structure… |
| `processing` | Indexing (chunk + embed)… |
| `needs_review` | Structure needs review — Retry or Confirm |
| `ready` | Ready |
| `failed` | Failed |

- [ ] **Bước 2: CTA**

- Happy path: không hiện Confirm là nút chính (book đã `processing`→`ready`).
- Khi `needs_review`: giữ **Retry detect** + **Confirm & index** (lối thoát thủ công).
- Preview units: read-only vẫn hiện khi có data (kể cả lúc indexing/ready).

- [ ] **Bước 3: Header copy**

`Upload a PDF — structure is detected (heuristics + AI), verified, then indexed automatically.`

- [ ] **Bước 4: Commit**

```bash
git commit -m "$(cat <<'EOF'
feat: admin books UX for auto structure merge and index

EOF
)"
```

---

### Task 6: Checklist thủ công + ghi plan

- [ ] **E2E**

| Bước | Kỳ vọng |
|------|---------|
| Upload Daily Departures (hoặc numbered-caps fixture scale) | Không Confirm; → processing → ready |
| `detection_method` | `ai_merge` (hoặc fallback candidate nếu tắt AI) |
| Units | ~20 passages, không accessibility junk |
| Tắt `STRUCTURE_AI_MERGE_ENABLED` / hết API key | Fallback chain/pick_best + behavior gate; không crash |
| Gate fail (PDF rỗng/corrupt text) | `needs_review` hoặc `failed`; không Mongo junk |
| Confirm thủ công khi `needs_review` | Vẫn index được |

```bash
cd backend && .venv/bin/python -m pytest tests/test_structure_gate.py tests/test_ai_merge_service.py tests/test_detector_chain.py tests/test_book_structure_auto_index.py -v
```

- [ ] Ghi kết quả checklist vào cuối plan này khi xong.

---

## Ngoài scope / follow-up

| Mục | Ghi chú |
|-----|---------|
| Edit unit UI khi `needs_review` | Làm preview có nghĩa hơn cho fail path |
| Shared `JUNK_OUTLINE_RE` module | DRY toc + gate |
| Hạ temperature / JSON schema strict | `response_format` nếu provider hỗ trợ |
| Cache skim text | Tránh extract 2 lần (merge + gate) |
| Metrics | Log gate reasons, token usage ước lượng |
| Enum `detecting` / `merging` | Tách khỏi `uploaded` |

---

## Đối chiếu yêu cầu

| Yêu cầu | Task |
|---------|------|
| Giữ Toc + Regex + Font | Task 1 |
| AI kết hợp / so khớp candidates + sách | Task 3–4 |
| Không báo láo → gate | Task 2–4 |
| Upload → auto chunk/embed (không review tay) | Task 4–5 |
| Vẫn có lối thoát khi fail | Task 4–5 (needs_review + Confirm) |

---

## Self-review plan

| Check | Kết quả |
|-------|---------|
| Spec khớp quyết định hybrid + auto-index | Có |
| Tasks nhỏ, TDD, file cụ thể | Có |
| Không nhầm embed-trước-structure | Có — merge trước index |
| Flag fallback khi không có LLM | Có |
| FE/API Confirm không xóa nhầm | Giữ cho fail path |

---

## Bàn giao thực thi

Plan lưu tại `docs/superpowers/plans/2026-07-17-ai-structure-merge-auto-index.md`.

**Hai cách chạy:**

1. **Subagent-Driven (khuyên dùng)** — mỗi task một subagent, review giữa task  
2. **Inline Execution** — làm tuần tự trong session  

Bạn chọn cách nào?
