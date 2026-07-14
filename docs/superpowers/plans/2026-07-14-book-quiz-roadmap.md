# Kế hoạch triển khai: Ngân hàng quiz đa sách & Lộ trình theo CEFR level

> **Dành cho agent/kỹ sư thực hiện:** BẮT BUỘC dùng skill `superpowers:subagent-driven-development` (khuyên dùng) hoặc `superpowers:executing-plans` để làm từng task. Các bước dùng checkbox (`- [ ]`) để theo dõi tiến độ.

**Mục tiêu:** Ingest **nhiều sách** vào hệ thống, chuẩn hóa thành **đồ thị kỹ năng theo CEFR level** (không gắn lộ trình vào một cuốn sách). Sinh ngân hàng câu hỏi từ mọi nguồn đã index; đo mastery theo **skill chuẩn**; lắp lộ trình học viên theo `current_level` + survey + gap mastery — câu hỏi/scenario lấy từ **toàn bộ corpus** cùng level.

**Kiến trúc tối ưu (level-first, research-backed):**
1. **Ingest nhiều sách** → chunk/embed như hiện tại (nguồn thô).
2. **Canonical skill graph theo CEFR** (giống CEFR-J Grammar Profile / LearnGraph): mỗi skill có `slug` ổn định (`present_perfect`, `conditionals_type2`, …) + `cefr_level`.
3. **Map nhiều unit sách → cùng skill** (dedupe): Murphy U7 và Empower B1 grammar “present perfect” cùng trỏ `present_perfect@B1`.
4. **Quiz bank gắn `skill_id`** (provenance vẫn giữ `book_id`/`unit_id` để audit), không phải “quiz của sách X”.
5. **Mastery theo `skill_id`** (toàn cục cho HV), không theo từng sách.
6. **Assemble lộ trình theo level:** `POST /roadmap/assemble` chỉ cần level (mặc định `profile.current_level`) — **không** truyền `book_id`.

**Công nghệ:** FastAPI, SQLAlchemy/Postgres, Alembic, MongoDB (`book_chunks`), Voyage, `langchain-openai`, pytest, Next.js admin.

**Nguồn nghiên cứu (Exa):** CEFR-J Grammar Profile + knowledge map (ICCE) — lộ trình grammar theo level, bỏ knowledge đã master; Scientific Reports English KG — resource→knowledge mapping nhiều nguồn; LearnGraph/Jali — skill graph tách khỏi delivery; PathBuilder — diagnostic theo curriculum tags; tránh PPO/DKT ở MVP.

---

## 0. Quyết định kiến trúc: vì sao không lộ trình theo 1 sách

| Cách | Vấn đề với EnglishFlow |
|---|---|
| Lộ trình = tuần tự 1 cuốn Murphy | 145 unit; HV B1 không cần hết; trùng chủ đề nếu thêm Empower |
| Lộ trình = chọn 1 `book_id` | Admin phải chọn sách; không tận dụng corpus đã ingest |
| **Lộ trình = skill @ CEFR level** (chọn) | Đúng Spec (`current_level`); mọi sách cùng level góp quiz; dedupe chủ đề |

**Nguyên tắc:** Sách = *nguồn nội dung*. Level + skill = *đơn vị học & đánh giá*.

```text
[Nhiều sách ready]
    → sync mỗi sách: unit → normalize → skill slug @ cefr
    → merge: cùng slug+cefr = 1 skill, nhiều book_skill_sources
    → generate quiz theo skill (lấy context từ 1 source unit ưu tiên)
    → HV diagnostic/quiz cập nhật mastery[skill]
    → assemble roadmap(level=B1): top skill yếu @ B1 + scenario(goal)
```

---

## 1. Bối cảnh sản phẩm & phạm vi

### 1.1 Đã có trong repo

| Thành phần | Trạng thái | Ghi chú |
|---|---|---|
| Upload PDF + Supabase | Có | Nhiều sách, mỗi cuốn có `cefr_level`, `book_type` |
| Detect structure | Có | `book_structure_preview` theo sách |
| Confirm & index → Mongo | WIP | `book_chunks` theo `book_id`+`unit_id` |
| Survey + `current_level` | Có | Đầu vào lộ trình theo level |
| `scenarios` / `roadmap_steps` / `user_progress` | Có schema | Assembler sẽ gắn skill, không gắn 1 book |

### 1.2 Plan này xây

- Context chunk theo unit (nguồn).
- **Canonical `learning_skills` + `book_skill_sources`** (nhiều sách → 1 skill).
- Chuẩn hóa / dedupe skill (rule + LLM nhẹ).
- Quiz bank theo `skill_id` (+ provenance sách).
- Mastery theo `skill_id`.
- Assembler lộ trình **theo CEFR level** (không `book_id`).

### 1.3 YAGNI (chưa làm)

- Full DKT / PPO path planner.
- Vector search topic tự do (có thể dùng sau để gợi ý source unit).
- Auto-generate quiz cho mọi skill mọi sách ngay lúc sync (generate lazy theo skill ưu tiên / khi vào roadmap).
- UI lives/streak đầy đủ Spec §8.

### 1.4 Điều kiện tiên quyết

1. Indexing chạy được; ≥1 sách `ready` (lý tưởng ≥2 sách cùng level để chứng minh merge).
2. `MONGODB_URL`, `VOYAGE_API_KEY`, sau đó `OPENAI_API_KEY`.
3. Có seed `scenarios` theo category + level.

---

## 2. Ví dụ xuyên suốt: đa sách → 1 level B1

### 2.1 Corpus admin đã ingest

| Sách | CEFR | Vai trò |
|---|---|---|
| Cambridge Grammar in Use (Murphy) | B1–B2 | Nguồn grammar chi tiết (nhiều unit) |
| Cambridge Empower B1 | B1 | Nguồn thematic + functional language |
| (tuỳ chọn) Vocabulary in Use Pre-int | B1 | Nguồn vocab skill |

### 2.2 Sau sync + normalize

```text
learning_skills @ B1:
  present_perfect          ← Murphy U7,U8 + Empower U? grammar
  conditionals_type2       ← Murphy U38–39
  polite_requests_modals   ← Murphy U37 + Empower functional
  workplace_small_talk     ← Empower communication unit
  …

book_skill_sources:
  (present_perfect, murphy, unit_7)
  (present_perfect, murphy, unit_8)
  (present_perfect, empower, unit_3)   # nếu tag trùng
```

### 2.3 Học viên Minh (B1, job_interview, weak=grammar)

Diagnostic / quiz trên **skill B1** (câu lấy từ bất kỳ sách nào đã publish cho skill đó):

| Skill | Mastery | Roadmap |
|---|---|---|
| present_simple_vs_continuous | 0.85 | skip |
| present_perfect | 0.30 | Week 1 quiz (câu từ Murphy hoặc Empower) + scenario interview experience |
| polite_requests_modals | 0.40 | Week 2 |
| conditionals_type2 | 0.25 | Week 3 |
| … | | tối đa 8–12 tuần **trong level B1** |

Khi unlock B2 (Spec: hoàn thành 80% B1): assemble lại với `level=B2`, skill lấy từ sách B2 đã ingest.

### 2.4 Ràng buộc thiết kế

1. Unit sách = *source*, không = node lộ trình cuối cùng.
2. Skill canonical = đơn vị mastery + lộ trình.
3. Lộ trình cap 8–12 bước **trong một level**.
4. Exclude Key/Study Guide khỏi source mapping.
5. Generate quiz theo skill: chọn 1 primary source unit (ưu tiên `grammar_textbook` nếu skill grammar) để lấy context chunk.
6. Runtime quiz: `WHERE skill_id=? AND status=published` — **không** filter bắt buộc `book_id`.

---

## 3. Luồng dữ liệu end-to-end

```text
[Admin — ingest hết sách]
  Book1, Book2, … → detect → index → ready

[Admin — chuẩn hóa corpus]
  Với mỗi book ready:
    sync sources → normalize title → upsert learning_skills(slug, cefr)
    gắn book_skill_sources(skill, book, unit)
  (Idempotent: chạy lại không nhân đôi skill)

[Admin — ngân hàng câu hỏi]
  generate_quiz(skill_id):
    chọn primary source unit → get_unit_context → LLM batch → draft
  publish → available cho mọi HV cùng level

[Học viên]
  diagnostic / quiz theo skill @ level
  mastery[skill] cập nhật

[Lộ trình]
  POST /roadmap/assemble { "level": "B1" }   # optional; default profile.current_level
  → skills where cefr_level=B1, not excluded
  → bỏ mastery≥0.7; lấy top yếu ≤12
  → gắn scenario(goal, level)
  → user_progress
```

**Cấm:** `assemble(book_id=…)` làm API chính. Book chỉ là filter admin khi duyệt câu hỏi.

## 4. Bản đồ file sẽ tạo/sửa (mô hình level-first)

| Đường dẫn | Nhiệm vụ |
|---|---|
| `backend/app/models/enums.py` | Enum loại câu, status, skill type |
| `backend/app/models/learning_skill.py` | **`learning_skills`** + **`skill_edges`** (canonical theo CEFR) |
| `backend/app/models/book_skill_source.py` | **`book_skill_sources`**: map unit sách → skill |
| `backend/app/models/quiz_question.py` | Bank gắn **`skill_id`** (+ `book_id`/`unit_id` provenance) |
| `backend/app/models/user_skill_mastery.py` | Mastery theo **`skill_id`** (không theo sách) |
| `backend/app/models/roadmap_step_skill.py` | Nối roadmap step ↔ skill |
| `backend/alembic/versions/g7h8i9j0k1l2_add_level_skill_quiz_tables.py` | Migration |
| `backend/app/services/book_chunk_service.py` | Context theo unit (nguồn) |
| `backend/app/services/skill_normalize_service.py` | Title unit → slug chuẩn (rule + LLM) |
| `backend/app/services/skill_graph_service.py` | Sync sách → upsert skills + sources (dedupe) |
| `backend/app/services/llm_client.py` | Chat JSON |
| `backend/app/services/quiz_generation_service.py` | Generate theo **skill_id** |
| `backend/app/services/mastery_service.py` | Mastery theo skill |
| `backend/app/services/roadmap_assembler_service.py` | Assemble theo **cefr level** |
| `backend/app/api/admin_quiz.py` | Sync/generate/publish (theo skill) |
| `backend/app/api/quiz.py` | Learner quiz theo skill |
| `backend/app/api/roadmap.py` | `assemble` theo level |
| `backend/app/core/config.py` | OPENAI_*, QUIZ_CONTEXT_MAX_CHARS |
| `backend/tests/test_skill_*.py` / `test_roadmap_assembler_service.py` | Unit tests |
| `frontend/my-app/lib/admin-quiz.ts` | Sync + generate |
| `frontend/my-app/src/app/admin/books/page.tsx` | UI hooks |

### 4.1 Schema cốt lõi (thay cho “book_concepts”)

```text
learning_skills
  id, slug (unique với cefr_level), title, cefr_level, skill_type,
  is_active, created_at
  UNIQUE(slug, cefr_level)

skill_edges
  from_skill_id, to_skill_id, relation=prerequisite

book_skill_sources
  id, skill_id, book_id, unit_id, unit_title, is_excluded, is_primary
  UNIQUE(book_id, unit_id)   # mỗi unit map đúng 1 skill
  INDEX(skill_id)

quiz_questions
  skill_id (FK), book_id, unit_id (provenance), stem, options, answer, status, …

user_skill_mastery
  user_id, skill_id, mastery, attempts, correct
  UNIQUE(user_id, skill_id)

roadmap_step_skills
  roadmap_step_id, skill_id, role=quiz
```

**Không** dùng `book_concepts` làm node lộ trình. Nếu đã viết code theo `book_concepts` trong bản plan cũ: đổi tên / migrate sang mô hình trên.

### 4.2 Chiến lược dedupe / normalize (tối ưu MVP)

1. Rule normalize: lower, bỏ số unit, bỏ ngoặc `(I have done)`, map synonym phổ biến (`present perfect 1` → `present_perfect`).
2. Bảng alias tĩnh (seed): `{"present perfect continuous": "present_perfect_continuous", ...}`.
3. Nếu không match alias: LLM trả `{slug, title, cefr_level}` với enum slug snake_case; cache kết quả theo `normalized_title`.
4. Upsert `learning_skills` theo `(slug, cefr_level)` lấy từ **book.cefr_level** (hoặc LLM nếu book null).
5. Nhiều unit → cùng skill = nhiều `book_skill_sources`; chọn `is_primary=True` cho source tốt nhất (`grammar_textbook` ưu tiên hơn `freeform` khi skill_type=grammar).

Research: CEFR-J gắn quiz↔grammar item; English KG map resource→knowledge point; multi-course KG fusion để phát hiện overlap — MVP dùng slug+cefr thay vì contrastive GNN.

## 5. Biến môi trường cần thêm

```bash
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o-mini
# OPENAI_BASE_URL=https://...   # optional
QUIZ_CONTEXT_MAX_CHARS=5000
```

Bắt buộc cho context: `MONGODB_URL`, `MONGODB_DB_NAME`.

---

## 3bis. Chi tiết: Unit được xác định thế nào & chunk dựa trên gì

> Đây là phần kỹ thuật cốt lõi trước khi sinh quiz. **Chunk không tự “đoán” unit** — unit có trước (detect structure), rồi text trong khoảng trang của unit mới bị cắt thành chunk.

### A. Hai khái niệm tách bạch

| Khái niệm | Nghĩa | Ai tạo |
|---|---|---|
| **Unit** | Một đoạn sách có tiêu đề + `page_start`–`page_end` (vd. “Unit 7 Present perfect 1”) | `StructureDetectorChain` → `book_structure_preview` |
| **Chunk** | Mảnh text nhỏ hơn **bên trong một unit**, dùng embed/RAG/sinh quiz | `chunk_unit_text` trong `book_indexing_service` |

```text
PDF
 → Detector chọn danh sách Unit (bao nhiêu unit? = số heading hợp lệ)
 → Admin confirm
 → Với mỗi unit: extract text [page_start..page_end]
 → Cắt text đó thành 1..N chunk (theo book_type)
 → Embed từng chunk → Mongo
```

**Không** có công thức “mỗi X trang = 1 unit”. Số unit = số heading detector chấp nhận.

---

### B. Chain chọn “đây là unit” (thứ tự ưu tiên)

Code: `StructureDetectorChain` — lần lượt thử, **lấy kết quả đầu tiên có `confidence >= 0.5`**, không thì lấy best dưới ngưỡng.

| Thứ tự | Detector | Confidence | Dựa trên gì để coi là unit |
|---|---|---|---|
| 1 | `TocDetector` | 0.95 | PDF outline/bookmarks |
| 2 | `RegexDetector` | 0.60 | Dòng text khớp `Unit/Chapter/PASSAGE/Test…` |
| 3 | `FontStyleDetector` | 0.40 | Font size ≥ 1.3× body (heading) |

#### B1. TocDetector — khi nào outline depth được chọn làm “unit level”

Từ outline phẳng `(title, page, depth)`:

1. **Ưu tiên depth** có ≥2 title kiểu nội dung:
   - `^\d+\.\d+\s` (1.1 …)
   - `^(Chapter|Unit|Section|Part)\s+\d+`
   - `^(Chương|Bài|Phần)\s+\d+`
2. **Fallback:** depth có ≥3 mục, **avg page span** ∈ **[2, 80]** trang/unit, ít front-matter (Contents, Preface, Index…).
3. Prefer avg span gần ~10 trang (penalty `|avg−10|`).
4. Lọc front-matter; nếu đủ content titles thì chỉ giữ content.
5. `page_end` unit i = trang trước unit i+1 (unit cuối → hết sách).

**Đánh giá “bao nhiêu là unit” (TOC):** số bookmark ở depth đã chọn (sau lọc).  
Cambridge Murphy với outline tốt ≈ 145 unit (mỗi “Unit N …” một bookmark).

#### B2. RegexDetector — khi không có outline

Quét từng trang; dòng đầu/trong trang khớp:

| Pattern | Nhãn | Priority |
|---|---|---|
| `PASSAGE N` | passage | 100 |
| `TEST/Test N` | test | 80 |
| `Unit/Chapter/Section/Part N` | section | 60 |
| `Bài/Chương/Phần N` | section_vi | 60 |

Lọc nhiễu:
- Trang có ≥2 heading **cùng loại** → coi TOC/overview → **bỏ** (không tạo unit từ trang đó).
- Trang mixed (TEST+PASSAGE) → giữ source priority cao hơn.

Chọn **một** source “thắng” (nhiều match nhất / priority), mỗi match = 1 unit với `page_start` = trang heading, `page_end` = trước heading kế.

**Đánh giá số unit (regex):** số heading hợp lệ của source thắng.

#### B3. FontStyleDetector — fallback yếu

Body size = mode font size; heading nếu `size >= 1.3 * body` (và thường bold). Mỗi heading → unit. Confidence 0.4 → thường chỉ thắng nếu TOC+regex thất bại.

---

### C. Admin “đánh giá” unit trước khi chunk

Sau detect, UI hiện preview. Admin quyết định:

| Tín hiệu | Ý nghĩa |
|---|---|
| `detection_method` | toc / regex / font_style |
| `confidence` | ≥0.5 tin dùng; thấp → review kỹ |
| Số unit | Murphy ~100+ ổn; 3–5 unit cả sách grammar → quá thô; 300+ unit → có thể lẫn heading nhỏ |
| Độ dài trang/unit | Grammar in Use ~2 trang/unit lý tưởng; avg >80 trang → depth sai (đang lấy Part thay vì Unit) |
| Title | Có “Key to Exercises”, “Study guide” → sau này `is_excluded` / không map skill |

**Quy tắc thực dụng chấp nhận preview:**

1. Với `grammar_textbook`: kỳ vọng avg span **1–6 trang**/unit (Murphy ~2).
2. Với `reading_practice` / passage: avg **1–4 trang**/passage.
3. Với coursebook (Empower): unit thematic có thể **8–20 trang** — vẫn OK nếu title là “Unit 1 Communicating”.
4. Nếu avg span > 40 và title là “Part 1 / Section A” → **detect lại / sửa** — chunk sẽ quá lớn, quiz lẫn nhiều topic.

Chỉ khi admin **Confirm & index** mới chunk.

---

### D. Chunk bên trong unit dựa trên gì

Sau khi có unit cố định:

1. `extract_pages_text(pdf, page_start, page_end)` — **chỉ** trang của unit.
2. `RecursiveCharacterTextSplitter` với size theo **`book_type`** (không theo số trang):

| `book_type` | `chunk_size` (ký tự) | `overlap` | Lý do |
|---|---|---|---|
| `grammar_textbook` | 1200 | 100 | Giải thích rule dài hơn |
| `reading_practice` | 800 | 80 | Đoạn đọc vừa |
| `test_bank` | 800 | 80 | Section đề |
| `freeform` | 600 | 100 | Tài liệu lẫn |

Separators ưu tiên: `\n\n` → `\n` → `. ` → ` `.

3. Unit ngắn hơn `chunk_size` → **đúng 1 chunk** (không cắt).
4. Overlap **không** vượt biên unit (không dính Unit 8 vào Unit 7).
5. Embed text = `[unit_title]\n` + chunk body.

**Ví dụ Murphy Unit 7 (~2 trang, ~1500–2500 ký tự text):**
- Thường 1–3 chunk grammar (1200).
- `get_unit_context(max_chars=5000)` gần như lấy **hết unit** khi sinh quiz — đúng ý “một điểm ngữ pháp”.

**Ví dụ Empower Unit 1 (~15 trang):**
- Nhiều chunk hơn; khi generate quiz dùng `prefix` hoặc `stride` trong budget 5000 chars — không nhét cả unit nếu quá dài.

---

### E. Checklist “unit/chunk đã ổn chưa?” trước sync skill

- [ ] Preview: số unit hợp lý với loại sách (không 5 unit cho Murphy).
- [ ] Spot-check 3 unit: title đúng, page range không chồng sai.
- [ ] Không lấy Answer Key làm unit học (hoặc đánh excluded sau).
- [ ] Index xong: `chunk_count` > 0; sample Mongo có `unit_id`, `chunk_index` tuần tự từ 0.
- [ ] Unit 2 trang grammar: thường ≤3 chunk; unit 15 trang: nhiều chunk hơn — bình thường.

### F. Liên hệ skill graph (level-first)

- **1 unit detect** → 1 `book_skill_source` (sau normalize có thể nhiều unit → cùng `learning_skill`).
- Chunk chỉ phục vụ **nguồn** generate/retrieve; lộ trình đếm **skill @ CEFR**, không đếm số chunk hay số unit toàn sách.

# Phase A — Context unit + skill graph đa sách (canonical theo CEFR)

> **Lưu ý đổi mô hình:** Các task bên dưới dùng `learning_skills` + `book_skill_sources` (mục §4.1). Không implement `book_concepts` làm node lộ trình. Task 1 vẫn lấy chunk theo **unit nguồn** (đúng). Task 3 đổi thành sync skill graph + normalize.

## Task 1: Lấy chunk theo unit nguồn và đóng gói context

**Mục đích:** Text đủ ngắn để LLM sinh quiz, chỉ từ **một unit**, bỏ field `embedding`.

**Files:**
- Sửa: `backend/app/core/config.py`
- Sửa: `backend/app/services/book_chunk_service.py`
- Tạo: `backend/tests/test_book_chunk_context.py`

**Tiêu chí chấp nhận:**
- `mode=prefix`: lấy theo `chunk_index` đến gần đầy `max_chars`.
- `mode=stride`: ưu tiên đầu + giữa + cuối.
- Không trả embedding. Unit trống → `text=""`.

- [ ] **Bước 1: Viết test sẽ fail**

```python
# backend/tests/test_book_chunk_context.py
from app.services.book_chunk_service import pack_unit_context


def test_pack_unit_context_prefix_dung_khi_het_budget():
    chunks = [
        {"chunk_index": 0, "text": "A" * 100, "_id": "c0"},
        {"chunk_index": 1, "text": "B" * 100, "_id": "c1"},
        {"chunk_index": 2, "text": "C" * 100, "_id": "c2"},
    ]
    text, ids = pack_unit_context(chunks, max_chars=150, mode="prefix")
    assert "A" * 100 in text
    assert set(ids).issubset({"c0", "c1", "c2"})
    assert all(cid in {"c0", "c1"} for cid in ids)


def test_pack_unit_context_stride_lay_dau_giua_cuoi():
    chunks = [
        {"chunk_index": i, "text": f"chunk-{i}-" + ("x" * 20), "_id": f"id{i}"}
        for i in range(10)
    ]
    text, ids = pack_unit_context(chunks, max_chars=5000, mode="stride")
    assert "chunk-0-" in text
    assert "chunk-9-" in text
    assert ("chunk-5-" in text) or ("chunk-4-" in text)


def test_pack_unit_context_rong():
    text, ids = pack_unit_context([], max_chars=5000, mode="prefix")
    assert text == ""
    assert ids == []
```

- [ ] **Bước 2: Chạy test — phải FAIL**

```bash
cd backend && pytest tests/test_book_chunk_context.py -v
```

Kỳ vọng: `ImportError` hoặc hàm chưa tồn tại.

- [ ] **Bước 3: Thêm config vào `Settings`**

```python
QUIZ_CONTEXT_MAX_CHARS: int = 5000
OPENAI_API_KEY: str | None = None
OPENAI_MODEL: str = "gpt-4o-mini"
OPENAI_BASE_URL: str | None = None
```

- [ ] **Bước 4: Implement trong `book_chunk_service.py`**

```python
from typing import Any, Literal

PackMode = Literal["prefix", "stride"]


def pack_unit_context(
    chunks: list[dict[str, Any]],
    max_chars: int = 5000,
    mode: PackMode = "prefix",
) -> tuple[str, list[str]]:
    """Ghép text các chunk trong một unit, giới hạn max_chars. Không đọc PDF."""
    if not chunks:
        return "", []

    ordered = sorted(chunks, key=lambda c: int(c.get("chunk_index", 0)))

    if mode == "stride" and len(ordered) > 3:
        mid = len(ordered) // 2
        priority_indexes = {0, mid, len(ordered) - 1}
        prioritized = [ordered[i] for i in sorted(priority_indexes)]
        rest = [c for i, c in enumerate(ordered) if i not in priority_indexes]
        ordered = prioritized + rest

    parts: list[str] = []
    ids: list[str] = []
    total = 0
    for c in ordered:
        text = (c.get("text") or "").strip()
        if not text:
            continue
        sep = 2 if parts else 0
        if parts and total + sep + len(text) > max_chars:
            break
        if not parts and len(text) > max_chars:
            text = text[:max_chars]
        parts.append(text)
        ids.append(str(c.get("_id", c.get("chunk_index"))))
        total += sep + len(text)
    return "\n\n".join(parts), ids


def get_unit_chunks(book_id: int, unit_id: int) -> list[dict[str, Any]]:
    if not settings.MONGODB_URL:
        raise RuntimeError("MONGODB_URL is not configured")
    client, collection = _sync_collection()
    try:
        cursor = collection.find(
            {"book_id": int(book_id), "unit_id": int(unit_id)},
            {"text": 1, "chunk_index": 1, "unit_title": 1, "page_start": 1, "page_end": 1},
        ).sort("chunk_index", 1)
        return list(cursor)
    finally:
        client.close()


def get_unit_context(
    book_id: int,
    unit_id: int,
    max_chars: int | None = None,
    mode: PackMode = "prefix",
) -> dict[str, Any]:
    budget = max_chars if max_chars is not None else settings.QUIZ_CONTEXT_MAX_CHARS
    chunks = get_unit_chunks(book_id, unit_id)
    text, chunk_ids = pack_unit_context(chunks, max_chars=budget, mode=mode)
    unit_title = chunks[0].get("unit_title") if chunks else None
    return {
        "book_id": book_id,
        "unit_id": unit_id,
        "unit_title": unit_title,
        "text": text,
        "chunk_ids": chunk_ids,
        "chunk_count": len(chunks),
    }
```

- [ ] **Bước 5: Test PASS**

```bash
cd backend && pytest tests/test_book_chunk_context.py -v
```

- [ ] **Bước 6: Commit**

```bash
git add backend/app/services/book_chunk_service.py backend/app/core/config.py backend/tests/test_book_chunk_context.py
git commit -m "$(cat <<'EOF'
feat: đóng gói context chunk theo unit cho sinh quiz

EOF
)"
```

---

## Task 2: Enum + migration + model Postgres

**Mục đích:** Lưu concept, câu hỏi, mastery, liên kết lộ trình↔concept.

**Files:** enums, `book_concept.py`, `quiz_question.py`, `user_concept_mastery.py`, `roadmap_step_concept.py`, `__init__.py`, Alembic migration.

**Lưu ý:** Chạy `cd backend && alembic heads` rồi đặt `down_revision` đúng head hiện tại.

- [ ] **Bước 1: Thêm enum**

```python
class QuizQuestionTypeEnum(str, enum.Enum):
    mcq = "mcq"
    cloze = "cloze"
    fix_grammar = "fix_grammar"


class QuizQuestionStatusEnum(str, enum.Enum):
    draft = "draft"
    published = "published"
    rejected = "rejected"


class ConceptSkillEnum(str, enum.Enum):
    grammar = "grammar"
    vocabulary = "vocabulary"
    reading = "reading"
    functional = "functional"


quiz_question_type_enum = SAEnum(QuizQuestionTypeEnum, name="quiz_question_type_enum", create_type=True)
quiz_question_status_enum = SAEnum(QuizQuestionStatusEnum, name="quiz_question_status_enum", create_type=True)
concept_skill_enum = SAEnum(ConceptSkillEnum, name="concept_skill_enum", create_type=True)
```

- [ ] **Bước 2: Tạo `backend/app/models/book_concept.py`**

```python
from sqlalchemy import (
    BigInteger, Boolean, Column, ForeignKey, Integer, String,
    TIMESTAMP, UniqueConstraint, func,
)
from app.core.database import Base
from app.models.enums import concept_skill_enum


class BookConceptDB(Base):
    __tablename__ = "book_concepts"
    __table_args__ = (
        UniqueConstraint("book_id", "unit_id", name="uq_book_concept_unit"),
    )

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    book_id = Column(BigInteger, ForeignKey("books.id", ondelete="CASCADE"), nullable=False, index=True)
    unit_id = Column(
        BigInteger,
        ForeignKey("book_structure_preview.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    unit_index = Column(Integer, nullable=False)
    title = Column(String(500), nullable=False)
    section_title = Column(String(255), nullable=True)  # vd. "Present perfect and past"
    skill = Column(concept_skill_enum, nullable=False, server_default="grammar")
    scenario_hint = Column(String(255), nullable=True)  # vd. work_experience
    is_excluded = Column(Boolean, nullable=False, server_default="false")
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())


class BookConceptEdgeDB(Base):
    __tablename__ = "book_concept_edges"
    __table_args__ = (
        UniqueConstraint("from_concept_id", "to_concept_id", name="uq_concept_edge"),
    )

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    book_id = Column(BigInteger, ForeignKey("books.id", ondelete="CASCADE"), nullable=False, index=True)
    from_concept_id = Column(BigInteger, ForeignKey("book_concepts.id", ondelete="CASCADE"), nullable=False)
    to_concept_id = Column(BigInteger, ForeignKey("book_concepts.id", ondelete="CASCADE"), nullable=False)
    relation = Column(String(50), nullable=False, server_default="prerequisite")
```

- [ ] **Bước 3: Tạo `backend/app/models/quiz_question.py`**

```python
from sqlalchemy import (
    BigInteger, Column, ForeignKey, String, TEXT, TIMESTAMP, JSON, func,
)
from app.core.database import Base
from app.models.enums import (
    quiz_question_type_enum,
    quiz_question_status_enum,
    cefr_level_enum,
)


class QuizQuestionDB(Base):
    __tablename__ = "quiz_questions"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    book_id = Column(BigInteger, ForeignKey("books.id", ondelete="CASCADE"), nullable=False, index=True)
    concept_id = Column(BigInteger, ForeignKey("book_concepts.id", ondelete="CASCADE"), nullable=False, index=True)
    unit_id = Column(BigInteger, ForeignKey("book_structure_preview.id", ondelete="CASCADE"), nullable=False)
    question_type = Column(quiz_question_type_enum, nullable=False)
    stem = Column(TEXT, nullable=False)
    options = Column(JSON, nullable=True)  # mcq: 4 phần tử
    answer = Column(String(500), nullable=False)
    explanation = Column(TEXT, nullable=True)
    skill = Column(String(50), nullable=False)
    cefr_level = Column(cefr_level_enum, nullable=True)
    difficulty = Column(String(20), nullable=False, server_default="medium")
    status = Column(quiz_question_status_enum, nullable=False, server_default="draft")
    generation_batch_id = Column(String(64), nullable=True, index=True)
    source_chunk_ids = Column(JSON, nullable=True)
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(
        TIMESTAMP(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )
```

- [ ] **Bước 4: Tạo mastery + roadmap_step_concept**

```python
# backend/app/models/user_concept_mastery.py
from sqlalchemy import (
    BigInteger, Column, Float, ForeignKey, Integer, TIMESTAMP, UniqueConstraint, func,
)
from app.core.database import Base


class UserConceptMasteryDB(Base):
    __tablename__ = "user_concept_mastery"
    __table_args__ = (
        UniqueConstraint("user_id", "concept_id", name="uq_user_concept_mastery"),
    )

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    concept_id = Column(BigInteger, ForeignKey("book_concepts.id", ondelete="CASCADE"), nullable=False, index=True)
    mastery = Column(Float, nullable=False, server_default="0")
    attempts = Column(Integer, nullable=False, server_default="0")
    correct = Column(Integer, nullable=False, server_default="0")
    updated_at = Column(
        TIMESTAMP(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )
```

```python
# backend/app/models/roadmap_step_concept.py
from sqlalchemy import BigInteger, Column, ForeignKey, String, UniqueConstraint
from app.core.database import Base


class RoadmapStepConceptDB(Base):
    __tablename__ = "roadmap_step_concepts"
    __table_args__ = (
        UniqueConstraint("roadmap_step_id", "concept_id", name="uq_step_concept"),
    )

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    roadmap_step_id = Column(
        BigInteger, ForeignKey("roadmap_steps.id", ondelete="CASCADE"), nullable=False, index=True
    )
    concept_id = Column(
        BigInteger, ForeignKey("book_concepts.id", ondelete="CASCADE"), nullable=False, index=True
    )
    role = Column(String(50), nullable=False, server_default="quiz")
```

- [ ] **Bước 5: Export trong `backend/app/models/__init__.py`**

Import các class mới và thêm vào `__all__` theo đúng pattern file hiện có.

- [ ] **Bước 6: Viết Alembic migration + upgrade**

Tạo file `backend/alembic/versions/g7h8i9j0k1l2_add_quiz_roadmap_tables.py`:
- `down_revision` = output của `alembic heads`
- `upgrade()`: tạo 3 enum Postgres + 5 bảng đúng cột ở trên; có FK và UniqueConstraint
- `downgrade()`: drop bảng theo thứ tự ngược (edges/questions/mastery/step_concepts trước, concepts sau), rồi drop enum

```bash
cd backend && alembic upgrade head
```

Kỳ vọng: không lỗi duplicate type / missing FK.

- [ ] **Bước 7: Commit**

```bash
git add backend/app/models backend/alembic/versions/g7h8i9j0k1l2_add_quiz_roadmap_tables.py
git commit -m "$(cat <<'EOF'
feat: thêm bảng concept, quiz bank, mastery và liên kết lộ trình

EOF
)"
```

---

## Task 3: Đồng bộ skill graph từ mọi sách ready (normalize + dedupe)

**Mục đích:** Mỗi preview unit → 1 concept; loại Key/Study guide; edge theo thứ tự unit còn lại.

**Ví dụ Cambridge:** `"Key to Exercises"` → `is_excluded=True`; `"Present perfect 1…"` → false, có thể có `section_title`.

**Files:** `concept_graph_service.py`, `test_concept_graph_service.py`

- [ ] **Bước 1: Test thuần**

```python
from app.services.concept_graph_service import (
    infer_section_title, should_exclude_unit, build_linear_edges,
)

def test_loai_answer_key_va_study_guide():
    assert should_exclude_unit("Key to Exercises") is True
    assert should_exclude_unit("Study guide") is True
    assert should_exclude_unit("Appendix 1 Regular and irregular verbs") is True
    assert should_exclude_unit("Present perfect 1 (I have done)") is False

def test_suy_ra_section_title():
    units = [
        {"title": "Present perfect and past", "depth_or_source": "section", "unit_index": 0},
        {"title": "Present perfect 1 (I have done)", "depth_or_source": "toc", "unit_index": 1},
        {"title": "Present perfect 2 (I have done)", "depth_or_source": "toc", "unit_index": 2},
    ]
    assert infer_section_title(units[1], units) == "Present perfect and past"

def test_edge_bo_qua_unit_excluded():
    concepts = [
        {"id": 1, "unit_index": 1, "is_excluded": False},
        {"id": 2, "unit_index": 2, "is_excluded": True},
        {"id": 3, "unit_index": 3, "is_excluded": False},
    ]
    assert build_linear_edges(concepts) == [(1, 3)]
```

- [ ] **Bước 2: Chạy — phải FAIL**

```bash
cd backend && pytest tests/test_concept_graph_service.py -v
```

- [ ] **Bước 3: Implement đầy đủ `concept_graph_service.py`**

```python
# backend/app/services/concept_graph_service.py
from __future__ import annotations

import re
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.book import BookDB
from app.models.book_concept import BookConceptDB, BookConceptEdgeDB
from app.models.book_structure_preview import BookStructurePreviewDB
from app.models.enums import BookStatusEnum, ConceptSkillEnum

EXCLUDE_PATTERNS = re.compile(
    r"(answer\s*key|key to exercises|key to additional|study\s*guide|appendix|index|^contents$)",
    re.I,
)


def should_exclude_unit(title: str) -> bool:
    return bool(EXCLUDE_PATTERNS.search(title or ""))


def infer_section_title(unit: dict[str, Any], all_units: list[dict[str, Any]]) -> str | None:
    if (unit.get("depth_or_source") or "").lower() == "section":
        return unit["title"]
    prev_section = None
    for u in sorted(all_units, key=lambda x: x["unit_index"]):
        if u["unit_index"] > unit["unit_index"]:
            break
        if (u.get("depth_or_source") or "").lower() == "section":
            prev_section = u["title"]
    return prev_section


def build_linear_edges(concepts: list[dict[str, Any]]) -> list[tuple[int, int]]:
    active = [
        c for c in sorted(concepts, key=lambda x: x["unit_index"]) if not c["is_excluded"]
    ]
    return [(active[i]["id"], active[i + 1]["id"]) for i in range(len(active) - 1)]


async def sync_concepts_from_preview(db: AsyncSession, book_id: int) -> list[BookConceptDB]:
    """Xóa concept cũ của sách rồi tạo lại từ preview. Chỉ khi book ready."""
    book = (await db.execute(select(BookDB).where(BookDB.id == book_id))).scalar_one_or_none()
    if book is None:
        raise ValueError(f"Không tìm thấy sách {book_id}")
    if book.status != BookStatusEnum.ready:
        raise ValueError("Sách phải ở trạng thái ready trước khi đồng bộ concept")

    units = list(
        (
            await db.execute(
                select(BookStructurePreviewDB)
                .where(BookStructurePreviewDB.book_id == book_id)
                .order_by(BookStructurePreviewDB.unit_index)
            )
        ).scalars().all()
    )
    if not units:
        raise ValueError("Chưa có structure preview — chạy detect-structure trước")

    unit_dicts = [
        {
            "id": u.id,
            "title": u.title,
            "unit_index": u.unit_index,
            "depth_or_source": u.depth_or_source,
        }
        for u in units
    ]

    await db.execute(delete(BookConceptEdgeDB).where(BookConceptEdgeDB.book_id == book_id))
    await db.execute(delete(BookConceptDB).where(BookConceptDB.book_id == book_id))

    created: list[BookConceptDB] = []
    for u in units:
        row = BookConceptDB(
            book_id=book_id,
            unit_id=u.id,
            unit_index=u.unit_index,
            title=u.title,
            section_title=infer_section_title(
                {
                    "title": u.title,
                    "unit_index": u.unit_index,
                    "depth_or_source": u.depth_or_source,
                },
                unit_dicts,
            ),
            skill=ConceptSkillEnum.grammar,
            scenario_hint=None,
            is_excluded=should_exclude_unit(u.title),
        )
        db.add(row)
        created.append(row)
    await db.flush()

    for frm, to in build_linear_edges(
        [{"id": c.id, "unit_index": c.unit_index, "is_excluded": c.is_excluded} for c in created]
    ):
        db.add(
            BookConceptEdgeDB(
                book_id=book_id,
                from_concept_id=frm,
                to_concept_id=to,
                relation="prerequisite",
            )
        )
    await db.commit()
    for c in created:
        await db.refresh(c)
    return created
```

- [ ] **Bước 4: Test PASS + commit**

```bash
cd backend && pytest tests/test_concept_graph_service.py -v
git add backend/app/services/concept_graph_service.py backend/tests/test_concept_graph_service.py
git commit -m "$(cat <<'EOF'
feat: đồng bộ book concepts từ structure preview, loại key/guide

EOF
)"
```

---

# Phase B — Sinh câu hỏi từ chunk unit

## Task 4: Client LLM JSON

**Mục đích:** Một chỗ gọi model tương thích OpenAI, trả object/array JSON đã parse. Dễ mock trong test Phase B.

**Files:**
- Tạo: `backend/app/services/llm_client.py`
- Tạo: `backend/tests/test_llm_client.py`
- Config `OPENAI_*` (nếu chưa thêm ở Task 1)

- [ ] **Bước 1: Test parse**

```python
from app.services.llm_client import parse_json_content


def test_parse_json_bo_fence_markdown():
    raw = '```json\n{"questions": []}\n```'
    assert parse_json_content(raw) == {"questions": []}


def test_parse_json_thuan():
    assert parse_json_content('{"a": 1}') == {"a": 1}
```

- [ ] **Bước 2: Chạy — FAIL**

```bash
cd backend && pytest tests/test_llm_client.py -v
```

- [ ] **Bước 3: Implement**

```python
# backend/app/services/llm_client.py
from __future__ import annotations

import json
import re
from typing import Any

from app.core.config import settings

_FENCE = re.compile(r"```(?:json)?\s*([\s\S]*?)```", re.I)


def parse_json_content(content: str) -> Any:
    text = content.strip()
    m = _FENCE.search(text)
    if m:
        text = m.group(1).strip()
    return json.loads(text)


def chat_json(system: str, user: str) -> Any:
    if not settings.OPENAI_API_KEY:
        raise RuntimeError("OPENAI_API_KEY chưa được cấu hình")

    from langchain_core.messages import HumanMessage, SystemMessage
    from langchain_openai import ChatOpenAI

    kwargs: dict[str, Any] = {
        "model": settings.OPENAI_MODEL,
        "api_key": settings.OPENAI_API_KEY,
        "temperature": 0.3,
    }
    if settings.OPENAI_BASE_URL:
        kwargs["base_url"] = settings.OPENAI_BASE_URL

    llm = ChatOpenAI(**kwargs)
    result = llm.invoke(
        [SystemMessage(content=system), HumanMessage(content=user)]
    )
    content = result.content if isinstance(result.content, str) else str(result.content)
    return parse_json_content(content)
```

- [ ] **Bước 4: PASS + commit**

```bash
cd backend && pytest tests/test_llm_client.py -v
git add backend/app/services/llm_client.py backend/app/core/config.py backend/tests/test_llm_client.py
git commit -m "$(cat <<'EOF'
feat: thêm LLM client parse JSON cho sinh câu hỏi

EOF
)"
```

---

## Task 5: Service sinh quiz theo skill (context lấy từ primary source unit)

**Mục đích:** 1 lần gọi LLM → N câu (mặc định 8) → validate → lưu từng row `draft` cùng `generation_batch_id`.

**Ràng buộc validate:**
- `type` ∈ {mcq, cloze, fix_grammar}
- mcq: đúng 4 `options`, `answer` phải trùng một option
- `stem` và `answer` không rỗng
- Concept `is_excluded=True` → raise, không gọi LLM

**Files:**
- Tạo: `backend/app/services/quiz_generation_service.py`
- Tạo: `backend/app/schemas/quiz_schema.py`
- Tạo: `backend/tests/test_quiz_generation_service.py`

- [ ] **Bước 1: Test validate + prompt (không gọi API thật)**

```python
from app.services.quiz_generation_service import (
    validate_generated_questions,
    build_generation_prompt,
)


def test_validate_mcq_hop_le():
    raw = [
        {
            "type": "mcq",
            "stem": "Choose the correct form: I ___ here since 2020.",
            "options": ["lived", "have lived", "live", "am living"],
            "answer": "have lived",
            "explanation": "Present perfect with since.",
            "skill": "grammar",
            "difficulty": "medium",
        }
    ]
    ok = validate_generated_questions(raw)
    assert len(ok) == 1
    assert ok[0]["answer"] == "have lived"


def test_validate_mcq_thieu_option_bi_loai():
    raw = [{"type": "mcq", "stem": "x", "options": ["a"], "answer": "a", "skill": "grammar"}]
    assert validate_generated_questions(raw) == []


def test_validate_mcq_answer_khong_nam_trong_options():
    raw = [
        {
            "type": "mcq",
            "stem": "x",
            "options": ["a", "b", "c", "d"],
            "answer": "z",
            "skill": "grammar",
        }
    ]
    assert validate_generated_questions(raw) == []


def test_prompt_co_ten_unit_va_so_cau():
    prompt = build_generation_prompt(
        unit_title="Present perfect 1 (I have done)",
        cefr_level="B1",
        context="We use the present perfect...",
        count=5,
    )
    assert "Present perfect 1" in prompt
    assert "5" in prompt
    assert "We use the present perfect" in prompt
```

- [ ] **Bước 2: FAIL**

```bash
cd backend && pytest tests/test_quiz_generation_service.py -v
```

- [ ] **Bước 3: Schema Pydantic**

```python
# backend/app/schemas/quiz_schema.py
from typing import Optional
from pydantic import BaseModel, Field
from app.models.enums import QuizQuestionStatusEnum, QuizQuestionTypeEnum


class GenerateQuizRequest(BaseModel):
    count: int = Field(default=8, ge=1, le=15)


class QuizQuestionOut(BaseModel):
    id: int
    book_id: int
    concept_id: int
    unit_id: int
    question_type: QuizQuestionTypeEnum
    stem: str
    options: Optional[list[str]] = None
    answer: str
    explanation: Optional[str] = None
    skill: str
    difficulty: str
    status: QuizQuestionStatusEnum
    generation_batch_id: Optional[str] = None

    model_config = {"from_attributes": True}


class QuizQuestionListResponse(BaseModel):
    data: list[QuizQuestionOut]


class GenerateQuizResponse(BaseModel):
    data: list[QuizQuestionOut]
    message: str = "Đã tạo câu hỏi nháp"


class PublishQuizRequest(BaseModel):
    question_ids: list[int]
```

- [ ] **Bước 4: Implement `quiz_generation_service.py`**

```python
# backend/app/services/quiz_generation_service.py
from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.book import BookDB
from app.models.book_concept import BookConceptDB
from app.models.enums import QuizQuestionStatusEnum, QuizQuestionTypeEnum
from app.models.quiz_question import QuizQuestionDB
from app.services.book_chunk_service import get_unit_context
from app.services.llm_client import chat_json

SYSTEM_PROMPT = """You are an expert English assessment writer for CEFR-aligned courses.
Generate exam questions ONLY from the provided textbook excerpt.
Do not invent rules unsupported by the excerpt.
Do not copy answer keys if present; write new stems.
Return JSON: {"questions":[...]} with fields:
type (mcq|cloze|fix_grammar), stem, options (4 strings for mcq else null),
answer, explanation, skill, difficulty (easy|medium|hard).
For mcq, answer must exactly match one option.
"""


def build_generation_prompt(
    unit_title: str,
    cefr_level: str | None,
    context: str,
    count: int,
) -> str:
    return (
        f"Unit: {unit_title}\n"
        f"CEFR: {cefr_level or 'B1'}\n"
        f"Generate exactly {count} questions.\n"
        f"Prefer mcq; include at most 1 cloze.\n\n"
        f"EXCERPT:\n{context}\n"
    )


def validate_generated_questions(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    valid: list[dict[str, Any]] = []
    for item in items:
        qtype = item.get("type")
        stem = (item.get("stem") or "").strip()
        answer = str(item.get("answer") or "").strip()
        if not stem or not answer or qtype not in {"mcq", "cloze", "fix_grammar"}:
            continue
        options = item.get("options")
        if qtype == "mcq":
            if not isinstance(options, list) or len(options) != 4:
                continue
            if answer not in options:
                continue
        valid.append(
            {
                "type": qtype,
                "stem": stem,
                "options": options if qtype == "mcq" else None,
                "answer": answer,
                "explanation": item.get("explanation"),
                "skill": item.get("skill") or "grammar",
                "difficulty": item.get("difficulty") or "medium",
            }
        )
    return valid


async def generate_quiz_for_skill(
    db: AsyncSession,
    skill_id: int,
    count: int = 8,
) -> list[QuizQuestionDB]:
    """Sinh quiz cho skill chuẩn: primary source unit → context → LLM → draft rows."""
    from app.models.learning_skill import LearningSkillDB
    from app.models.book_skill_source import BookSkillSourceDB
    from app.models.book import BookDB

    skill = (
        await db.execute(select(LearningSkillDB).where(LearningSkillDB.id == skill_id))
    ).scalar_one_or_none()
    if skill is None:
        raise ValueError("Không tìm thấy skill")

    sources = list(
        (
            await db.execute(
                select(BookSkillSourceDB).where(
                    BookSkillSourceDB.skill_id == skill_id,
                    BookSkillSourceDB.is_excluded.is_(False),
                )
            )
        ).scalars().all()
    )
    if not sources:
        raise ValueError("Skill chưa có book source — sync sách trước")

    primary = next((s for s in sources if s.is_primary), sources[0])
    book = (
        await db.execute(select(BookDB).where(BookDB.id == primary.book_id))
    ).scalar_one()
    ctx = get_unit_context(int(primary.book_id), int(primary.unit_id), mode="prefix")
    if not ctx["text"]:
        raise ValueError("Unit nguồn không có text chunk")

    cefr = skill.cefr_level.value if hasattr(skill.cefr_level, "value") else str(skill.cefr_level)
    payload = chat_json(
        SYSTEM_PROMPT,
        build_generation_prompt(skill.title, cefr, ctx["text"], count),
    )
    raw_questions = payload.get("questions") if isinstance(payload, dict) else payload
    if not isinstance(raw_questions, list):
        raise ValueError("LLM không trả về danh sách questions")

    validated = validate_generated_questions(raw_questions)
    if not validated:
        raise ValueError("Không có câu hỏi hợp lệ sau validate")

    batch_id = uuid.uuid4().hex
    rows: list[QuizQuestionDB] = []
    for item in validated:
        row = QuizQuestionDB(
            skill_id=skill.id,
            book_id=primary.book_id,
            unit_id=primary.unit_id,
            question_type=QuizQuestionTypeEnum(item["type"]),
            stem=item["stem"],
            options=item["options"],
            answer=item["answer"],
            explanation=item.get("explanation"),
            skill=item["skill"],
            cefr_level=skill.cefr_level,
            difficulty=item["difficulty"],
            status=QuizQuestionStatusEnum.draft,
            generation_batch_id=batch_id,
            source_chunk_ids=ctx["chunk_ids"],
        )
        db.add(row)
        rows.append(row)
    await db.commit()
    for row in rows:
        await db.refresh(row)
    return rows
```

- [ ] **Bước 5: PASS + commit**

```bash
cd backend && pytest tests/test_quiz_generation_service.py -v
git add backend/app/services/quiz_generation_service.py backend/app/schemas/quiz_schema.py backend/tests/test_quiz_generation_service.py
git commit -m "$(cat <<'EOF'
feat: sinh batch câu hỏi nháp từ context unit sách

EOF
)"
```

---

## Task 6: API admin quiz

**Mục đích:** Admin đồng bộ concept, sinh quiz, liệt kê, publish.

**Files:**
- Tạo: `backend/app/api/admin_quiz.py`
- Sửa: `backend/main.py`

**Quyền:** mọi route `Depends(require_permission("book:manage"))`.

| Method | Path | Việc |
|---|---|---|
| POST | `/api/v1/admin/quiz/books/{book_id}/sync-concepts` | Đồng bộ; trả list concept cho FE |
| POST | `/api/v1/admin/quiz/concepts/{concept_id}/generate` | Body `{count}` → drafts |
| GET | `/api/v1/admin/quiz/books/{book_id}/questions` | Query `status_filter` optional |
| POST | `/api/v1/admin/quiz/questions/publish` | Body `{question_ids}` |

- [ ] **Bước 1: Implement router**

```python
# backend/app/api/admin_quiz.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_permission
from app.core.database import get_db
from app.models.enums import QuizQuestionStatusEnum
from app.models.quiz_question import QuizQuestionDB
from app.schemas.quiz_schema import (
    GenerateQuizRequest,
    GenerateQuizResponse,
    PublishQuizRequest,
    QuizQuestionListResponse,
    QuizQuestionOut,
)
from app.services.concept_graph_service import sync_concepts_from_preview
from app.services.quiz_generation_service import generate_quiz_for_skill

router = APIRouter()


@router.post(
    "/books/{book_id}/sync-concepts",
    dependencies=[Depends(require_permission("book:manage"))],
)
async def admin_sync_concepts(book_id: int, db: AsyncSession = Depends(get_db)):
    try:
        concepts = await sync_concepts_from_preview(db, book_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {
        "data": {
            "book_id": book_id,
            "concept_count": len(concepts),
            "excluded": sum(1 for c in concepts if c.is_excluded),
            "concepts": [
                {
                    "id": c.id,
                    "unit_id": c.unit_id,
                    "title": c.title,
                    "is_excluded": c.is_excluded,
                    "section_title": c.section_title,
                }
                for c in concepts
            ],
        }
    }


@router.post(
    "/skills/{skill_id}/generate",
    response_model=GenerateQuizResponse,
    dependencies=[Depends(require_permission("book:manage"))],
)
async def admin_generate_quiz(
    skill_id: int,
    body: GenerateQuizRequest,
    db: AsyncSession = Depends(get_db),
):
    try:
        rows = await generate_quiz_for_skill(db, skill_id, count=body.count)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return GenerateQuizResponse(data=[QuizQuestionOut.model_validate(r) for r in rows])


@router.get(
    "/books/{book_id}/questions",
    response_model=QuizQuestionListResponse,
    dependencies=[Depends(require_permission("book:manage"))],
)
async def admin_list_questions(
    book_id: int,
    status_filter: QuizQuestionStatusEnum | None = None,
    db: AsyncSession = Depends(get_db),
):
    q = select(QuizQuestionDB).where(QuizQuestionDB.book_id == book_id)
    if status_filter is not None:
        q = q.where(QuizQuestionDB.status == status_filter)
    rows = list((await db.execute(q.order_by(QuizQuestionDB.id.desc()))).scalars().all())
    return QuizQuestionListResponse(data=[QuizQuestionOut.model_validate(r) for r in rows])


@router.post(
    "/questions/publish",
    dependencies=[Depends(require_permission("book:manage"))],
)
async def admin_publish_questions(body: PublishQuizRequest, db: AsyncSession = Depends(get_db)):
    rows = list(
        (
            await db.execute(select(QuizQuestionDB).where(QuizQuestionDB.id.in_(body.question_ids)))
        ).scalars().all()
    )
    for row in rows:
        row.status = QuizQuestionStatusEnum.published
    await db.commit()
    return {"data": {"published": len(rows)}}
```

- [ ] **Bước 2: Mount trong `main.py`**

```python
from app.api import admin_quiz
app.include_router(admin_quiz.router, prefix="/api/v1/admin/quiz", tags=["admin-quiz"])
```

- [ ] **Bước 3: Smoke**

```bash
curl -s -X POST "http://localhost:8001/api/v1/admin/quiz/books/1/sync-concepts" \
  -H "Authorization: Bearer $TOKEN" | jq .
curl -s -X POST "http://localhost:8001/api/v1/admin/quiz/concepts/12/generate" \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"count":5}' | jq .
```

- [ ] **Bước 4: Commit**

```bash
git add backend/app/api/admin_quiz.py backend/main.py
git commit -m "$(cat <<'EOF'
feat: API admin đồng bộ concept và sinh/publish quiz

EOF
)"
```

---

# Phase C — Đánh giá học viên (mastery)

## Task 7: Công thức mastery

**Mục đích:** Mỗi lần trả lời cập nhật `mastery ∈ [0,1]`.

```text
Đúng:  m ← m + α(1 − m)     α = 0.25
Sai:   m ← m − β·m           β = 0.20
Clamp [0, 1]
MASTERY_WEAK = 0.4
MASTERY_STRONG = 0.7
DEFAULT_PRIOR (assembler) = 0.35
```

**Files:** `mastery_service.py`, `test_mastery_service.py`

- [ ] **Bước 1: Test**

```python
from app.services.mastery_service import next_mastery, MASTERY_WEAK, MASTERY_STRONG, grade_mcq


def test_tra_loi_dung_tang_mastery():
    assert next_mastery(0.3, correct=True) > 0.3


def test_tra_loi_sai_giam_mastery():
    assert next_mastery(0.6, correct=False) < 0.6


def test_clamp():
    assert 0.0 <= next_mastery(0.99, correct=True) <= 1.0
    assert 0.0 <= next_mastery(0.01, correct=False) <= 1.0


def test_nguong():
    assert MASTERY_WEAK == 0.4
    assert MASTERY_STRONG == 0.7


def test_cham_mcq_khong_phan_biet_hoa():
    assert grade_mcq("Have lived", "have lived") is True
    assert grade_mcq("have lived", "lived") is False
```

- [ ] **Bước 2: Implement**

```python
# backend/app/services/mastery_service.py
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user_concept_mastery import UserConceptMasteryDB

ALPHA = 0.25
BETA = 0.20
MASTERY_WEAK = 0.4
MASTERY_STRONG = 0.7


def next_mastery(current: float, correct: bool) -> float:
    m = max(0.0, min(1.0, current))
    if correct:
        m = m + ALPHA * (1.0 - m)
    else:
        m = m - BETA * m
    return max(0.0, min(1.0, m))


def grade_mcq(question_answer: str, user_answer: str) -> bool:
    return question_answer.strip().lower() == user_answer.strip().lower()


async def apply_answer(
    db: AsyncSession,
    user_id: int,
    concept_id: int,
    correct: bool,
) -> UserConceptMasteryDB:
    row = (
        await db.execute(
            select(UserConceptMasteryDB).where(
                UserConceptMasteryDB.user_id == user_id,
                UserConceptMasteryDB.concept_id == concept_id,
            )
        )
    ).scalar_one_or_none()
    if row is None:
        row = UserConceptMasteryDB(
            user_id=user_id,
            concept_id=concept_id,
            mastery=0.0,
            attempts=0,
            correct=0,
        )
        db.add(row)
        await db.flush()

    row.mastery = next_mastery(float(row.mastery), correct)
    row.attempts = int(row.attempts) + 1
    if correct:
        row.correct = int(row.correct) + 1
    await db.commit()
    await db.refresh(row)
    return row
```

- [ ] **Bước 3: PASS + commit**

```bash
cd backend && pytest tests/test_mastery_service.py -v
git add backend/app/services/mastery_service.py backend/tests/test_mastery_service.py
git commit -m "$(cat <<'EOF'
feat: cập nhật mastery concept sau mỗi câu trả lời

EOF
)"
```

---

## Task 8: API học viên lấy câu & nộp đáp án

**Files:** `backend/app/api/quiz.py`, `main.py`

| Method | Path | Ghi chú |
|---|---|---|
| GET | `/api/v1/quiz/concepts/{concept_id}/questions?limit=5` | Chỉ published; **không** trả answer |
| POST | `/api/v1/quiz/answer` | `{question_id, answer}` → `{correct, mastery, explanation}` |

- [ ] **Bước 1: Implement**

```python
# backend/app/api/quiz.py
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_active_user
from app.core.database import get_db
from app.models.enums import QuizQuestionStatusEnum
from app.models.quiz_question import QuizQuestionDB
from app.models.user import UserDB
from app.services.mastery_service import apply_answer, grade_mcq

router = APIRouter()


class AnswerRequest(BaseModel):
    question_id: int
    answer: str


class AnswerResponse(BaseModel):
    correct: bool
    mastery: float
    explanation: str | None = None


@router.get("/concepts/{concept_id}/questions")
async def list_published_questions(
    concept_id: int,
    limit: int = 5,
    db: AsyncSession = Depends(get_db),
    current_user: UserDB = Depends(get_current_active_user),
):
    q = (
        select(QuizQuestionDB)
        .where(
            QuizQuestionDB.concept_id == concept_id,
            QuizQuestionDB.status == QuizQuestionStatusEnum.published,
        )
        .order_by(func.random())
        .limit(limit)
    )
    rows = list((await db.execute(q)).scalars().all())
    return {
        "data": [
            {
                "id": r.id,
                "concept_id": r.concept_id,
                "question_type": r.question_type,
                "stem": r.stem,
                "options": r.options,
                "difficulty": r.difficulty,
                "skill": r.skill,
            }
            for r in rows
        ]
    }


@router.post("/answer", response_model=AnswerResponse)
async def submit_answer(
    body: AnswerRequest,
    db: AsyncSession = Depends(get_db),
    current_user: UserDB = Depends(get_current_active_user),
):
    question = (
        await db.execute(select(QuizQuestionDB).where(QuizQuestionDB.id == body.question_id))
    ).scalar_one_or_none()
    if question is None or question.status != QuizQuestionStatusEnum.published:
        raise HTTPException(status_code=404, detail="Không tìm thấy câu hỏi")
    correct = grade_mcq(question.answer, body.answer)
    mastery_row = await apply_answer(db, int(current_user.id), int(question.concept_id), correct)
    return AnswerResponse(
        correct=correct,
        mastery=float(mastery_row.mastery),
        explanation=question.explanation,
    )
```

- [ ] **Bước 2: Mount + commit**

```python
from app.api import quiz
app.include_router(quiz.router, prefix="/api/v1/quiz", tags=["quiz"])
```

> **Lưu ý level-first:** đổi path learner sang `/skills/{skill_id}/questions` và `apply_answer(..., skill_id=question.skill_id)` (không dùng `concept_id`).

```bash
git add backend/app/api/quiz.py backend/main.py
git commit -m "$(cat <<'EOF'
feat: API quiz học viên theo skill kèm cập nhật mastery

EOF
)"
```

---

# Phase D — Lắp lộ trình cá nhân THEO LEVEL (không theo sách)

## Task 9: Roadmap assembler theo CEFR level

**Mục đích:** Từ **toàn bộ skill đã sync** ở một CEFR level + mastery + survey → tối đa 8–12 tuần. Câu hỏi runtime lấy từ bank theo `skill_id` (bất kỳ sách nguồn nào).

**Thay đổi so với bản “theo book_id”:**
- API: `POST /roadmap/assemble` body `{ "level": "B1", "max_steps": 10 }` — `level` optional, default `profile.current_level`.
- **Không** có `book_id` trên API chính.
- Query skills: `LearningSkillDB.cefr_level == level AND is_active`.
- Mastery: `UserSkillMasteryDB` theo `skill_id`.
- Mỗi step gắn `roadmap_step_skills.skill_id` (không gắn book).

**Files:**
- Tạo/sửa: `backend/app/services/roadmap_assembler_service.py`
- Tạo: `backend/tests/test_roadmap_assembler_service.py`
- Tạo: `backend/app/api/roadmap.py`
- Sửa: `backend/main.py`

### Thuật toán

```text
1. level = body.level or profile.current_level
2. Load mọi learning_skills where cefr_level=level, is_active
3. Mastery map theo skill_id; thiếu → prior 0.35
4. Bỏ mastery >= 0.7
5. (Optional) boost skill_type khớp weak_point (grammar → ưu tiên grammar skills)
6. Sort mastery tăng; lấy top max_steps (8..12)
7. Map goal → scenario.category; chọn scenario cùng level
8. Xóa UserProgress cũ (MVP rebuild)
9. Tạo RoadmapStep + progress + roadmap_step_skills
10. Return weeks — mỗi week có skill_id, skill_slug, scenario_id
```

### Test bắt buộc

```python
from app.services.roadmap_assembler_service import select_skills_for_roadmap


def test_chi_lay_skill_dung_level_va_cap():
    skills = [
        {"id": 1, "slug": "a", "cefr_level": "B1", "skill_type": "grammar", "is_active": True},
        {"id": 2, "slug": "b", "cefr_level": "B1", "skill_type": "grammar", "is_active": True},
        {"id": 3, "slug": "c", "cefr_level": "B2", "skill_type": "grammar", "is_active": True},
    ]
    # Hàm selector nhận list đã filter theo level từ service
    selected = select_skills_for_roadmap(
        [s for s in skills if s["cefr_level"] == "B1"],
        mastery={1: 0.9, 2: 0.2},
        max_steps=10,
    )
    assert [s["id"] for s in selected] == [2]


def test_khong_vuot_12_trong_level():
    skills = [
        {"id": i, "slug": f"s{i}", "cefr_level": "B1", "skill_type": "grammar", "is_active": True}
        for i in range(1, 40)
    ]
    mastery = {i: 0.1 for i in range(1, 40)}
    assert len(select_skills_for_roadmap(skills, mastery, max_steps=12)) == 12
```

### Implement gợi ý (chữ ký mới)

```python
async def assemble_user_roadmap(
    db: AsyncSession,
    user_id: int,
    level: CEFRLevel | None = None,
    max_steps: int = 10,
) -> list[dict]:
    profile = ...
    target_level = level or profile.current_level
    skills = await load_active_skills(db, target_level)
    mastery = await load_mastery_map(db, user_id)
    selected = select_skills_for_roadmap(skills, mastery, max_steps=max_steps, weak_point=profile.weak_point)
    scenario = await pick_scenario(db, profile.goal, target_level)
    # tạo steps như trước, nhưng gắn skill_id
    ...
```

```python
# API
class AssembleRequest(BaseModel):
    level: CEFRLevel | None = None  # default = profile.current_level
    max_steps: int = Field(default=10, ge=8, le=12)


@router.post("/assemble")
async def assemble_roadmap(...):
    data = await assemble_user_roadmap(db, int(current_user.id), body.level, body.max_steps)
    return {"data": data}
```

**Tiêu chí chấp nhận đa sách:**
- Ingest Murphy + Empower cùng B1 → sync → `present_perfect` chỉ **1** skill, ≥1 sources.
- Assemble không cần `book_id`.
- Quiz GET theo `skill_id` có thể trả câu provenance từ sách khác nhau.
- ≤12 tuần trong level; không list 145 unit Murphy.

- [ ] Test → implement → mount `/api/v1/roadmap` → commit

```bash
git commit -m "$(cat <<'EOF'
feat: lắp lộ trình theo CEFR level từ skill đa sách

EOF
)"
```

---

ests/test_roadmap_assembler_service.py -v
git add backend/app/services/roadmap_assembler_service.py backend/app/api/roadmap.py backend/tests/test_roadmap_assembler_service.py backend/main.py
git commit -m "$(cat <<'EOF'
feat: lắp lộ trình cá nhân giới hạn bước từ mastery và sách

EOF
)"
```

---

# Phase E — Admin UI tối thiểu

## Task 10: Nút trên trang Admin Books

**Mục đích:** Sau `ready`, admin sync concept và generate quiz trên preview unit.

**Files:**
- Tạo: `frontend/my-app/lib/admin-quiz.ts`
- Sửa: `frontend/my-app/src/app/admin/books/page.tsx`

**Bắt buộc** dùng `authFetch` / `extractErrorMessage` giống `admin-books.ts`.

- [ ] **Bước 1: Client đầy đủ**

```typescript
// frontend/my-app/lib/admin-quiz.ts
import { authFetch, extractErrorMessage } from "@/lib/api";

export type ConceptRow = {
  id: number;
  unit_id: number;
  title: string;
  is_excluded: boolean;
  section_title?: string | null;
};

export async function syncBookConcepts(bookId: number): Promise<{
  concept_count: number;
  excluded: number;
  concepts: ConceptRow[];
}> {
  const res = await authFetch(`/api/v1/admin/quiz/books/${bookId}/sync-concepts`, {
    method: "POST",
  });
  if (!res.ok) {
    const error = await res.json().catch(() => ({}));
    throw new Error(extractErrorMessage(error, "Đồng bộ concept thất bại"));
  }
  const body = await res.json();
  return body.data;
}

export async function generateConceptQuiz(conceptId: number, count = 8) {
  const res = await authFetch(`/api/v1/admin/quiz/concepts/${conceptId}/generate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ count }),
  });
  if (!res.ok) {
    const error = await res.json().catch(() => ({}));
    throw new Error(extractErrorMessage(error, "Sinh quiz thất bại"));
  }
  return (await res.json()).data as unknown[];
}
```

- [ ] **Bước 2: Wire UI trên `admin/books/page.tsx`**

1. State: `conceptsByUnitId: Record<number, ConceptRow>`.
2. Khi sách `ready`: nút **Đồng bộ concept** → `syncBookConcepts` → map theo `unit_id`.
3. Trong list preview unit: nếu concept tồn tại và `!is_excluded` → nút **Sinh quiz**.
4. Loading/error giống pattern Detect/Index hiện có.

- [ ] **Bước 3: Commit**

```bash
git add frontend/my-app/lib/admin-quiz.ts frontend/my-app/src/app/admin/books/page.tsx
git commit -m "$(cat <<'EOF'
feat: UI admin đồng bộ concept và sinh quiz theo unit

EOF
)"
```

---

## 6. Checklist kiểm thử end-to-end (đa sách → theo level)

1. Upload **≥2 sách** cùng B1 (vd. Murphy grammar + Empower B1); index đến `ready`.
2. Sync skills cho cả hai sách — skill trùng (present perfect) **merge** cùng `slug`+`B1`; `book_skill_sources` ≥ 2 nếu cả hai cover.
3. Generate quiz cho skill `present_perfect` (primary source = grammar textbook) → draft → publish.
4. Generate thêm từ source khác (optional) — cùng `skill_id`, provenance book khác.
5. Learner GET `/quiz/skills/{skill_id}/questions` — thấy câu; **không** bắt buộc chọn sách.
6. Trả lời → `user_skill_mastery` đổi.
7. `POST /roadmap/assemble` `{"level":"B1","max_steps":10}` — **không** gửi `book_id`; ≤10 tuần; skill thuộc B1.
8. Đổi level assemble `B2` (nếu có sách B2) → tập skill khác.
9. Confirm không tạo lộ trình 145 tuần theo mục lục một sách.

---

## 7. Tự rà soát plan (self-review)

| Yêu cầu thiết kế | Task phủ |
|---|---|
| Context theo unit, không full sách | Task 1 |
| Skill canonical + map đa sách, loại key/guide | Task 3 |
| Sinh batch, lưu từng câu, draft→publish | Task 5–6 |
| Mastery từ trả lời | Task 7–8 |
| Lộ trình theo CEFR level (không book_id), cap 8–12 | Task 9 |
| UI admin tối thiểu | Task 10 |
| Đa sách → 1 level; không 145 tuần / không khóa 1 book | Task 9 + §6 |

**Plan follow-up (file riêng sau):**
1. Quiz session đầy đủ lives/streak (Spec §8).
2. Điều chỉnh lộ trình động Spec §9.3 (chèn Fix the Chat).
3. Atlas Vector Search cho generate theo topic tự do.
4. Diagnostic onboarding lấy câu từ bank thay placement tĩnh.

---

## 8. Bàn giao thực thi

Plan đã lưu tại `docs/superpowers/plans/2026-07-14-book-quiz-roadmap.md` (bản tiếng Việt chi tiết).

**Hai cách chạy:**

1. **Subagent-Driven (khuyên dùng)** — mỗi task một subagent mới, review giữa các task.  
2. **Inline Execution** — làm tuần tự trong session với checkpoint.

Bạn chọn cách nào để bắt đầu triển khai?
