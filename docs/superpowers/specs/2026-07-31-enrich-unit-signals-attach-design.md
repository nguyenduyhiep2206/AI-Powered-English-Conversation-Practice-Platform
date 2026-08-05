# Design: Enrich book unit signals for catalog attach

**Date:** 2026-07-31  
**Status:** Implemented (2026-07-31)  
**Implementation plan:** [`docs/superpowers/plans/2026-07-31-enrich-unit-signals-attach.md`](../plans/2026-07-31-enrich-unit-signals-attach.md)  
**Depends on:** Band ladder attach (`2026-07-30-band-ladder-book-attach-design.md`), book indexing / Mongo chunks  
**Does not change:** Seed-first catalog; attach-only (no invent skills); 1 unit → at most 1 catalog skill  
**Motivating case:** Cambridge English Empower Elementary Workbook (A2) — thematic unit titles (`People`, `Work and study`, …) unmapped against grammar-slug catalog despite correct `cefr_level=A2`

---

## 1. Problem

Attach hiện truyền vào LLM/rule chủ yếu:

- `unit_index`, `title`, `rule_slug` (normalize từ title), đôi khi `depth_or_source`

Với sách **theme-based A2** (Empower, nhiều coursebook):

- Tiêu đề unit = chủ đề (`Unit 1 People`)
- Nội dung A2 thật (grammar focus, vocab set, language focus) nằm **trong** unit / heading phụ
- Catalog seed = điểm grammar/vocab (`present_perfect_basic`, `comparatives_…`)

Hệ quả: nhiều unit **đúng band** nhưng **unmapped** — không phải sai CEFR, không phải thiếu seed topic bắt buộc, mà **thiếu tín hiệu nội dung trên unit record**.

Mở rộng seed theo TOC Empower sẽ kéo catalog theo từng sách → lệch mô hình band-ladder.

Overlap chunking (`RecursiveCharacterTextSplitter`) có thể cắt giữa câu — enrich **không** lấy 1 chunk lẻ làm đơn vị ý nghĩa; luôn **aggregate theo `unit_id`** rồi mới cắt/window.

---

## 2. Goals / Non-goals

### Goals

1. Làm giàu metadata từng structure unit đủ để attach map vào **catalog skill đã seed** (A1/A2).
2. Giảm tỷ lệ unmapped trên sách theme-based **cùng band**, không invent skill.
3. Admin thấy được tín hiệu đã extract (preview) để hiểu vì sao map/unmapped.
4. Re-run enrich + re-sync được trên sách `ready` đã có (Empower A2) mà không bắt buộc re-upload PDF.
5. Nguồn text enrich **ưu tiên Mongo chunks** đã index; PDF skim chỉ fallback.
6. **Cost:** heuristic-first; **LLM enrich chỉ khi cues còn trống/yếu** (lazy / weak-only). Attach **không** nhận full chunk.
7. Giữ invariant: slug ∈ catalog level hoặc null; exclude review/test/…; một unit → tối đa một skill.

### Non-goals

- Thêm hàng loạt skill topic vào `cefr_ladder_a1_a2` chỉ để khớp TOC Empower.
- Multi-attach (1 unit → N skills) trong MVP này.
- Đổi ZPD / assemble / mastery / placement.
- Đổi chiến lược overlap chunking index (follow-up riêng).
- OCR; sửa auto-index ≠ AI merge.
- Enrich bắt buộc ngay sau detect (pre-`ready`).
- LLM enrich mọi unit / nhét raw chunks vào attach prompt.

---

## 3. Decisions (locked for this spec)

| Chủ đề | Quyết định |
|--------|------------|
| Chiến lược | **Enrich unit signals** rồi attach lại vào catalog hiện có |
| Cardinality | Vẫn **1 unit → 0..1 catalog skill** |
| Thời điểm enrich | Sách **`ready`**: đầu **`sync-skills`** (enrich-missing) + `POST .../enrich-units` |
| **Nguồn text (primary)** | Mongo chunks theo `book_id` + `unit_id` (aggregate theo `chunk_index`) |
| **Nguồn text (fallback)** | PDF `extract_pages_text` khi không có / rỗng chunk |
| **Excerpt build** | Prefer window quanh heading `Grammar` / `Language focus` / `Vocabulary` / `Unit goals`; else đầu unit. Cap **`UNIT_ENRICH_MAX_CHARS` = 3000** (mặc định; range 2500–3000) |
| **Heuristic** | **Bắt buộc chạy trước** trên excerpt → `language_focus` / `grammar_cues` / `vocab_cues` |
| **LLM enrich** | **Weak-only:** chỉ gọi khi heuristic **không đủ cues** (xem §6.4). Không gọi nếu đã đủ |
| **Attach payload** | Chỉ `title` + signals ngắn (`language_focus`, `grammar_cues`, `vocab_cues`, `content_summary`) — **cấm** full excerpt/chunks |
| Persist signals | Trên `book_structure_preview`; **không** persist raw excerpt |
| Enrich vs sync | **Best-effort** |
| Seed catalog | Không mở rộng trong spec này |

### Định nghĩa “đủ cues” (heuristic strong)

Heuristic **strong** (bỏ qua LLM) khi **một** trong các điều:

- `grammar_cues` có ≥ 1 phần tử ∈ catalog slugs (cùng `book.cefr_level`), **hoặc**
- `language_focus` non-empty **và** khớp được ≥ 1 catalog slug/title token (cùng rule match heuristic)

Ngược lại = **weak** → đủ điều kiện LLM enrich (nếu flag + API key).

---

## 4. Concept

```text
Detect → Index (overlap chunks) → ready
                │
                ▼
     sync-skills / enrich-units
                │
                ├─ primary: aggregate Mongo chunks by unit_id
                └─ fallback: PDF page range
                │
                ▼
     Build excerpt (prefer Grammar/Language focus window, cap ~3k)
                │
                ▼
     Heuristic → language_focus / grammar_cues / vocab_cues
                │
         ┌──────┴──────┐
         │ strong?     │ weak / empty?
         ▼             ▼
      persist       LLM enrich (short excerpt only)
      done          → merge/overwrite signals → persist
                │
                ▼
     Attach (LLM + rule): title + signals only — NO full chunk
                │
                ├── mapped / excluded / unmapped
```

**Empower example (target):**

| Unit title | Signals (illustrative) | Attach to |
|------------|------------------------|-----------|
| Unit 1 People | cues: present simple, … | best catalog grammar match |
| Unit 4 Food | cues: much/many | `quantifiers_much_many` |
| Unit 8 Fit and healthy | cues: should, advice | `modals_should_must` |

Không tạo skill `vocab_people` trong spec này.

---

## 5. Data model

### `book_structure_preview` — thêm fields

| Field | Type | Ý nghĩa |
|-------|------|---------|
| `language_focus` | `TEXT` nullable | Focus ngắn (vd. `"should / must; advice"`) |
| `grammar_cues` | `JSONB` nullable | `string[]` gợi ý gần catalog — không phải FK |
| `vocab_cues` | `JSONB` nullable | `string[]` topic tags |
| `content_summary` | `TEXT` nullable | 1–3 câu EN; **chủ yếu từ LLM weak-path**; heuristic có thể để null |
| `enrichment_status` | `VARCHAR` | `pending` \| `done` \| `failed` \| `skipped` |
| `enriched_at` | `TIMESTAMPTZ` nullable | |
| `enrichment_source` | `VARCHAR` nullable | `chunks` \| `pdf_skim` |
| `enrichment_method` | `VARCHAR` nullable | `heuristic` \| `heuristic+llm` \| `skipped` — debug/cost |

Không lưu raw excerpt. Dùng `get_unit_chunks` (hoặc tương đương) đã có.

### API preview

`StructureUnitPreview` trả các field trên (kèm `enrichment_method` nếu hữu ích trên UI).

---

## 6. Enrichment pipeline

### 6.1 Trigger

| Trigger | Hành vi |
|---------|---------|
| `POST .../sync-skills` | Require `ready` → enrich-missing (heuristic ± weak LLM) → attach |
| `POST .../enrich-units` | Re-enrich overwrite; `ready` only |
| Sau detect | Không MVP |

### 6.2 Load + build excerpt

```text
raw = join_chunk_texts(book_id, unit_id)   # chunk_index ASC, field `text`
if empty:
    raw = extract_pages_text(pdf, page_start, page_end)
    source = pdf_skim
else:
    source = chunks

excerpt = window_prefer_language_focus(raw)  # Grammar / Language focus / Vocabulary / …
excerpt = truncate(excerpt, UNIT_ENRICH_MAX_CHARS)  # default 3000
```

`window_prefer_language_focus`: nếu tìm thấy heading match, lấy từ heading ± context đến đủ cap; không thì lấy từ đầu `raw`.

Ghi `enrichment_source`.

### 6.3 Heuristic (always)

Trên `excerpt`:

1. Regex/heading blocks: Grammar, Language focus, Vocabulary, Unit goals, …
2. Match catalog slugs/titles (word-ish) → `grammar_cues`
3. Topic-ish tokens từ title + vocab headings → `vocab_cues` (không invent catalog)

Excerpt rỗng → `skipped`; attach title-only.

Nếu **strong** (§3) → `enrichment_status=done`, `enrichment_method=heuristic`; **không gọi LLM**.

### 6.4 LLM enrich (weak-only)

Gọi **chỉ khi**:

- Heuristic **weak**, **và**
- `UNIT_ENRICH_LLM_ENABLED` (default **true** nếu có key; có thể tắt), **và**
- `OPENAI_API_KEY` có

Input (ngắn): book title, cefr_level, unit title, pages, **excerpt đã cap**, catalog `[{slug,title}, …]` cùng level.

Output:

```json
{
  "language_focus": "string",
  "grammar_cues": ["slug_or_label", "..."],
  "vocab_cues": ["...", "..."],
  "content_summary": "string"
}
```

Rules:

- Ưu tiên slug ∈ catalog trong `grammar_cues`
- Không invent skill / không phải bước attach
- Fail/timeout → giữ kết quả heuristic; `method=heuristic` hoặc `failed` nếu heuristic cũng trống
- Success → `enrichment_method=heuristic+llm`, `status=done`

**Cấm:** một prompt chứa full unit chunks chưa cắt; **cấm** LLM enrich khi đã strong.

### 6.5 Attach (unchanged cardinality; richer input)

Payload unit → attach LLM/rule:

```json
{
  "unit_index": 0,
  "title": "Unit 1 People",
  "language_focus": "...",
  "grammar_cues": ["present_simple"],
  "vocab_cues": ["people", "jobs"],
  "content_summary": "..."
}
```

`ATTACH_SYSTEM_PROMPT`: ưu tiên cues/focus khi title thematic; one slug; no invent.

Rule fallback: `grammar_cues` ∩ catalog_slugs sau khi title normalize fail.

**Attach không nhận `excerpt` / chunk bodies.**

---

## 7. API / FE

| Item | Change |
|------|--------|
| `POST .../enrich-units` | New; chunks-first; heuristic ± weak LLM |
| `POST .../sync-skills` | Enrich-missing rồi attach; meta: `enriched`, `enrichment_method_counts` (`heuristic` vs `heuristic+llm`), `mapped`, `unmapped`, `excluded` |
| Preview GET | New fields |
| Admin UI | Show focus/cues; optional badge `heuristic` / `+llm` / source chunks\|pdf |

---

## 8. Error handling

| Case | Behavior |
|------|----------|
| Not `ready` | 400 |
| No chunks | PDF fallback; cả hai rỗng → `skipped` |
| Heuristic strong | Skip LLM |
| LLM fail on weak | Keep heuristic; continue attach |
| Partial enrich | Attach continues; `enrichment_incomplete: true` |

---

## 9. Success metrics (Empower A2)

Baseline: ~5 mapped / 7 unmapped.

| Metric | Target |
|--------|--------|
| Unmapped sau enrich+resync | Giảm rõ (hướng ≤3 unmapped hoặc ≥75% mapped+excluded) |
| Invented slugs / new catalog rows | 0 |
| `% units` chỉ `enrichment_method=heuristic` | Càng cao càng tốt (cost); kỳ vọng phần lớn Empower |
| Attach prompt size | Không chứa raw chunk text |
| `enrichment_source=chunks` | Đa số units trên sách ready |

---

## 10. Testing

- Aggregate chunks by unit + window around “Language focus” + cap 3000
- Empty chunks → PDF fallback once
- Heuristic strong → **mock LLM must not be called**
- Heuristic weak → LLM called once with capped excerpt
- Rule attach: thematic title + cue slug → mapped
- Attach validate: reject invented slug; payload without excerpt field
- Regression: skipped enrichment → title-only attach

---

## 11. Rollout

1. Migration columns (+ `enrichment_method`)  
2. `load_unit_excerpt` + `window_prefer_language_focus`  
3. Heuristic + weak-only LLM enrich service  
4. Wire sync + enrich-units endpoint  
5. Attach prompt/rule  
6. FE  
7. Re-enrich Empower A2; report mapped/unmapped + method counts + token/cost note  

Config:

| Key | Default |
|-----|---------|
| `UNIT_ENRICH_ENABLED` | `true` |
| `UNIT_ENRICH_MAX_CHARS` | `3000` |
| `UNIT_ENRICH_LLM_ENABLED` | `true` (nhưng chỉ weak-path) |

---

## 12. Follow-ups (out of scope)

- Multi-attach; seed topic vocab; subunit detect; fix auto-index; cải overlap chunking; enrich pre-ready  

---

## 13. Locked decisions (checklist)

| # | Point | Decision |
|---|--------|----------|
| 1 | Primary text | **Mongo chunks** (aggregate by unit); PDF fallback |
| 2 | Cap excerpt | **3000** chars; prefer Grammar/Language focus window |
| 3 | Heuristic | **Always first** |
| 4 | LLM enrich | **Weak-only** (cues trống/yếu) |
| 5 | Attach input | **Signals only** — no full chunk |
| 6 | Sync enrich failure | **Best-effort** |
| 7 | Persist excerpt | **No** |

---

## 14. Summary

Trên sách `ready`: gộp chunk theo unit → cắt excerpt ngắn (ưu tiên language focus) → **heuristic trước** → LLM chỉ khi yếu → lưu signals → attach nhẹ (title + cues). Giữ catalog; giảm unmapped theme-unit; kiểm soát token.

---

*Spec updated 2026-07-31 — heuristic-first, LLM weak-only, chunks-primary, attach without full text. Approve trước khi writing-plans / implement.*
