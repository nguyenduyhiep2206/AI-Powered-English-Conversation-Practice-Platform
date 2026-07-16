# Kế hoạch triển khai: Pipeline ingest sách kiểu thị trường (auto-detect → review → index ngầm)

> **Dành cho agent/kỹ sư thực hiện:** BẮT BUỘC dùng skill `superpowers:subagent-driven-development` (khuyên dùng) hoặc `superpowers:executing-plans` để làm từng task. Các bước dùng checkbox (`- [ ]`) để theo dõi tiến độ.

**Mục tiêu:** Đổi UX/admin flow từ “bấm từng bước Detect → Preview → Confirm” sang pipeline hay gặp trên thị trường: **Upload → Detect chạy ngầm → dừng ở Review structure → Confirm một lần → Chunk + Embed chạy ngầm → Ready**. Vẫn **không** chunk trước khi admin Confirm (giữ chất lượng unit).

**Kiến trúc:**
1. `POST /upload` lưu PDF rồi `BackgroundTasks` gọi detect (session riêng qua `AsyncSessionLocal`, giống `index_book`).
2. Detect xong → luôn `needs_review` (kể cả confidence cao) để bắt buộc một cửa review trước chunk.
3. `POST /confirm-and-index` giữ như hiện tại: set `processing` + background `index_book` (chunk rồi embed).
4. FE: upload xong poll status/preview; CTA chính theo status; nút Detect chỉ còn **Retry detect**.

**Công nghệ:** FastAPI `BackgroundTasks`, SQLAlchemy async, Next.js admin books UI (poll nhẹ).

**Không làm trong plan này:** Celery/ARQ; status enum mới `detecting`; auto-confirm khi confidence cao (để follow-up); sửa unit title/pages trên UI (chỉ review + confirm).

---

## Target UX (sau khi xong)

```text
Admin Upload PDF
  → status: uploaded (đang detect ngầm; có thể chưa có units)
  → Detect xong: needs_review + có structure preview
  → Admin mở preview, bấm Confirm & index (1 lần)
  → status: processing → (chunk + embed ngầm) → ready
```

Click thủ công còn lại: **Upload**, **Confirm & index** (và Retry detect nếu fail).

---

## Bản đồ file

| File | Vai trò |
|------|---------|
| `backend/app/services/book_structure_service.py` | Detect luôn → `needs_review`; wrapper `detect_book_structure_job(book_id)` cho background |
| `backend/app/api/admin_books.py` | Upload schedule detect; giữ endpoint detect thủ công (retry) |
| `backend/tests/test_book_structure_status.py` | Unit: sau detect thành công status = `needs_review` |
| `frontend/my-app/lib/admin-books.ts` | Labels status rõ hơn; optional helper poll |
| `frontend/my-app/src/app/admin/books/page.tsx` | Auto-open preview khi `needs_review`; poll sau upload; Detect → Retry |

---

### Task 1: Detect thành công luôn `needs_review` (TDD)

**Files:**
- Tạo: `backend/tests/test_book_structure_status.py`
- Sửa: `backend/app/services/book_structure_service.py`

Hiện tại confidence ≥ 0.7 set `uploaded` — gây khó hiểu (“đã upload lại?”) và không ép review. Đổi thành **luôn `needs_review`** khi có units.

- [ ] **Bước 1: Viết test thuần cho rule status**

Tách helper nhỏ (dễ test không PDF):

```python
# backend/app/services/book_structure_service.py  (thêm gần CONFIDENCE_REVIEW_THRESHOLD)

def status_after_successful_detect(confidence: float) -> BookStatusEnum:
    """After units are saved, always require human review before chunking."""
    return BookStatusEnum.needs_review
```

```python
# backend/tests/test_book_structure_status.py
from app.models.enums import BookStatusEnum
from app.services.book_structure_service import status_after_successful_detect


def test_successful_detect_always_needs_review_even_high_confidence():
    assert status_after_successful_detect(0.95) == BookStatusEnum.needs_review
    assert status_after_successful_detect(0.5) == BookStatusEnum.needs_review
```

- [ ] **Bước 2: Chạy — kỳ vọng FAIL** (helper chưa có hoặc vẫn nhánh uploaded)

```bash
cd backend && .venv/bin/python -m pytest tests/test_book_structure_status.py -v
```

- [ ] **Bước 3: Implement + dùng helper trong `detect_book_structure`**

Đổi đoạn set status sau khi lưu units:

```python
book.detection_method = detection.method
book.status = status_after_successful_detect(detection.confidence)
```

Giữ `CONFIDENCE_REVIEW_THRESHOLD` để FE/badge “low confidence” sau (optional); không dùng để set `uploaded` nữa.

- [ ] **Bước 4: Chạy test — PASS**

```bash
cd backend && .venv/bin/python -m pytest tests/test_book_structure_status.py -v
```

- [ ] **Bước 5: Commit**

```bash
git add backend/app/services/book_structure_service.py backend/tests/test_book_structure_status.py
git commit -m "$(cat <<'EOF'
fix: always set needs_review after successful structure detect

EOF
)"
```

---

### Task 2: Background detect job + schedule sau upload

**Files:**
- Sửa: `backend/app/services/book_structure_service.py`
- Sửa: `backend/app/api/admin_books.py`

- [ ] **Bước 1: Thêm job dùng session riêng**

```python
# backend/app/services/book_structure_service.py
import logging
from app.core.database import AsyncSessionLocal

logger = logging.getLogger(__name__)


async def detect_book_structure_job(book_id: int) -> None:
    """Background entry: open own DB session (same pattern as index_book)."""
    try:
        async with AsyncSessionLocal() as db:
            await detect_book_structure(db, book_id)
    except Exception:
        logger.exception("Background structure detect failed for book_id=%s", book_id)
        # Best-effort: mark needs_review/failed so UI does not hang on "uploaded"
        try:
            async with AsyncSessionLocal() as db:
                book = await get_book(db, book_id)
                if book.status == BookStatusEnum.uploaded:
                    book.status = BookStatusEnum.needs_review
                    await db.commit()
        except Exception:
            logger.exception("Failed to mark book_id=%s after detect error", book_id)
```

**Lưu ý:** `detect_book_structure` hiện `raise HTTPException` khi không detect được — trong job, catch và log; status đã set `needs_review` trong nhánh fail của service trước khi raise. Đọc lại nhánh fail: đã `needs_review` + raise 422. Job phải **nuốt** HTTPException để BackgroundTasks không spam.

```python
from fastapi import HTTPException

async def detect_book_structure_job(book_id: int) -> None:
    try:
        async with AsyncSessionLocal() as db:
            await detect_book_structure(db, book_id)
    except HTTPException as exc:
        logger.warning(
            "Structure detect rejected for book_id=%s: %s", book_id, exc.detail
        )
    except Exception:
        logger.exception("Background structure detect failed for book_id=%s", book_id)
        ...
```

- [ ] **Bước 2: Upload schedule detect**

```python
# backend/app/api/admin_books.py
from app.services.book_structure_service import (
    detect_book_structure,
    detect_book_structure_job,
    get_structure_preview,
)

@router.post("/upload", ...)
async def admin_upload_book(
    ...,
    background_tasks: BackgroundTasks,
    ...
):
    book = await upload_book(...)
    background_tasks.add_task(detect_book_structure_job, int(book.id))
    return BookResponse(data=_to_admin(book))
```

Endpoint `POST /{book_id}/detect-structure` **giữ** cho Retry (sync trong request cũng OK).

- [ ] **Bước 3: Smoke**

```bash
cd backend && .venv/bin/python -c "from app.services.book_structure_service import detect_book_structure_job, status_after_successful_detect; print('ok')"
```

Hoặc trong container: upload 1 PDF nhỏ → vài giây sau `GET .../structure-preview` có units + status `needs_review`.

- [ ] **Bước 4: Commit**

```bash
git add backend/app/services/book_structure_service.py backend/app/api/admin_books.py
git commit -m "$(cat <<'EOF'
feat: auto-detect book structure in background after upload

EOF
)"
```

---

### Task 3: Admin FE — pipeline UX (poll + CTA theo status)

**Files:**
- Sửa: `frontend/my-app/lib/admin-books.ts`
- Sửa: `frontend/my-app/src/app/admin/books/page.tsx`

- [ ] **Bước 1: Labels rõ nghĩa pipeline**

```typescript
export const BOOK_STATUS_LABELS: Record<BookStatus, string> = {
  uploaded: "Detecting structure…",
  needs_review: "Review structure",
  processing: "Indexing…",
  ready: "Ready",
  failed: "Failed",
};
```

(Nếu book `uploaded` lâu mà đã có units — edge case detect xong nhưng status cũ — poll `structure-preview` vẫn mở được.)

- [ ] **Bước 2: Sau upload — poll nhẹ đến khi không còn `uploaded` hoặc có units**

Trong `handleUpload` sau `uploadAdminBook` + `loadBooks()`:

```typescript
// Pseudo: poll book list / preview up to ~60s every 2s while status === "uploaded"
async function pollUntilDetectSettled(bookId: number) {
  for (let i = 0; i < 30; i++) {
    await new Promise((r) => setTimeout(r, 2000));
    await loadBooks();
    const book = /* find in latest books by id — use functional update or refetch */;
    if (!book) continue;
    if (book.status !== "uploaded") {
      if (book.status === "needs_review") {
        await handleShowPreview(bookId); // open preview for Confirm
      }
      return;
    }
  }
}
```

Implement sạch: `fetchAdminBook(bookId)` đã có trong `admin-books.ts` — poll `fetchAdminBook` thay vì cả list.

```typescript
async function pollUntilDetectSettled(bookId: number) {
  for (let i = 0; i < 30; i++) {
    await new Promise((r) => setTimeout(r, 2000));
    try {
      const book = await fetchAdminBook(bookId);
      setBooks((prev) => prev.map((b) => (b.id === bookId ? book : b)));
      if (book.status !== "uploaded") {
        if (book.status === "needs_review") {
          const preview = await fetchBookStructurePreview(bookId);
          setPreviewBookId(bookId);
          setPreview(preview);
        }
        return;
      }
    } catch {
      /* keep polling */
    }
  }
}
```

Gọi `void pollUntilDetectSettled(book.id)` sau upload (cần `uploadAdminBook` return `Book`).

- [ ] **Bước 3: Đổi nút Detect → Retry detect**

- Title/tooltip: `Retry detect`  
- Vẫn gọi `detectBookStructure`  
- Primary path không bắt admin bấm Detect lần đầu

Khi `needs_review`: hàng bảng highlight / badge “Review structure”; bấm Preview hoặc auto-open sau poll.

Khi `processing`: disable Confirm; copy “Indexing in background…”.

- [ ] **Bước 4: Copy trang**

Header phụ:  
`Upload a PDF — structure is detected automatically. Review units, then confirm to chunk & embed.`

- [ ] **Bước 5: Commit**

```bash
git add frontend/my-app/lib/admin-books.ts frontend/my-app/src/app/admin/books/page.tsx
git commit -m "$(cat <<'EOF'
feat: admin books UX for auto-detect then single confirm index

EOF
)"
```

---

### Task 4: Checklist thủ công + ghi chú plan

- [x] **Bước 1: E2E** (code/static + unit; browser full PDF còn admin tự xác nhận)

| Bước | Pass? | Bằng chứng |
|------|-------|-----------|
| Upload → “Detecting structure…” | Pass (code) | label `uploaded`; upload schedule `detect_book_structure_job` |
| Không bấm Detect; đợi → Review + preview | Pass (code) | poll → `needs_review` mở preview; detect luôn `needs_review` |
| Confirm → Indexing → Ready + chunks | Pass (code đã có) | `confirm-and-index` + `index_book` background (không đổi Task 4) |
| Retry detect trên sách cũ | Pass (code) | nút Retry detect + `POST .../detect-structure` |
| Confirm trước detect xong → 400 | Pass (code đã có) | `confirm_and_start_indexing` yêu cầu có units |

> **Browser còn lại:** Upload 1 PDF thật trên `/admin/books` và xác nhận poll + Confirm → Ready.

- [x] **Bước 2: Unit regression**

```bash
cd backend && .venv/bin/python -m pytest tests/test_book_structure_status.py -v
```

Kết quả (2026-07-16): **1 passed**. Container smoke: upload route + `detect_book_structure_job` import OK.

- [x] **Bước 3:** Checklist ghi vào plan này.
---

## Ngoài scope / follow-up

| Mục | Ghi chú |
|-----|---------|
| Enum `detecting` | Tách rõ uploaded vs đang detect |
| Auto-confirm khi confidence ≥ threshold | Flag config; bỏ qua review |
| Sửa unit trên UI trước Confirm | Edit page_start/title |
| Celery/ARQ | Thay BackgroundTasks khi PDF lớn |
| Toast realtime (SSE/websocket) | Thay poll |

---

## Đối chiếu yêu cầu

| Yêu cầu thị trường / feedback | Task |
|------------------------------|------|
| Không bắt user bấm Detect sau upload | Task 2–3 |
| Vẫn review structure trước chunk | Task 1 + Confirm giữ nguyên |
| Chunk/embed chạy ngầm sau Confirm | Đã có (`index_book`); Task 3 chỉ UX |
| Ít click hơn | Task 3 |

---

## Bàn giao thực thi

Plan lưu tại `docs/superpowers/plans/2026-07-16-book-ingest-market-pipeline.md`.

**Hai cách chạy:**

1. **Subagent-Driven (khuyên dùng)** — mỗi task một subagent, review giữa task  
2. **Inline Execution** — làm tuần tự trong session  

Bạn chọn cách nào?
