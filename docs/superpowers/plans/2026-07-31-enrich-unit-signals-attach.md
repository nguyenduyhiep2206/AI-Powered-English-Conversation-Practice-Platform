# Enrich Unit Signals for Catalog Attach — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** On `ready` books, enrich each structure unit from Mongo chunks (PDF fallback) with heuristic-first signals, optionally LLM only when cues are weak, then attach to the existing A1/A2 catalog without inventing skills or sending full chunk text to attach.

**Architecture:** New `unit_enrichment_service` loads aggregated unit text → windows/caps excerpt → heuristic → weak-only LLM → persists columns on `book_structure_preview`. `sync_skills_from_preview` calls enrich-missing first; attach LLM/rule consume `language_focus` / `grammar_cues` / `vocab_cues` / `content_summary` only. Admin `POST .../enrich-units` forces re-enrich.

**Tech Stack:** FastAPI, SQLAlchemy async, Alembic, Mongo `get_unit_chunks`, `chat_json`, pytest, Next.js admin types/UI.

**Spec:** `docs/superpowers/specs/2026-07-31-enrich-unit-signals-attach-design.md`

## Global Constraints

- Catalog attach-only: **no** invent slugs; **1 unit → 0..1 skill**
- Text primary: **Mongo chunks by `unit_id`**; PDF skim **fallback only**
- Excerpt cap: **`UNIT_ENRICH_MAX_CHARS=3000`**; prefer Grammar / Language focus / Vocabulary / Unit goals window
- Heuristic **always first**; LLM enrich **only when heuristic weak**
- Attach payload: **signals only** — never full excerpt/chunks
- Enrich vs sync: **best-effort** (enrich fail does not block attach)
- No re-index / re-upload required for existing `ready` books
- No seed catalog expansion in this plan
- **Do not commit.** Leave all changes in the working tree for the user to review and commit themselves.
- Alembic head at plan time: **`o4p5q6r7s8t9`** — re-check `alembic heads` before writing migration

---

## File map

| File | Responsibility |
|------|----------------|
| `backend/alembic/versions/<rev>_enrich_unit_signals.py` | Add enrich columns on `book_structure_preview` |
| `backend/app/models/book_structure_preview.py` | ORM columns |
| `backend/app/core/config.py` | `UNIT_ENRICH_*` settings |
| `backend/app/schemas/book_schema.py` | Preview API fields |
| `backend/app/services/unit_enrichment_excerpt.py` | Pure: join chunks, window, truncate |
| `backend/app/services/unit_enrichment_heuristic.py` | Pure: cues + strong/weak |
| `backend/app/services/unit_enrichment_llm.py` | Weak-only LLM JSON enrich |
| `backend/app/services/unit_enrichment_service.py` | Orchestrator: load → heuristic → maybe LLM → persist |
| `backend/app/services/skill_graph_service.py` | Enrich-missing before attach; richer `_unit_dicts`; rule uses cues |
| `backend/app/services/skill_graph_llm_service.py` | Attach prompt prefers cues |
| `backend/app/api/admin_books.py` | `POST /{id}/enrich-units` |
| `backend/app/api/admin_quiz.py` | Sync response meta for enrichment |
| `frontend/my-app/lib/admin-books.ts` | Types + `enrichBookUnits` |
| `frontend/my-app/components/admin/BookQuizPanel.tsx` | Show cues / method badges (minimal) |
| `backend/tests/test_unit_enrichment_excerpt.py` | Excerpt/window/cap |
| `backend/tests/test_unit_enrichment_heuristic.py` | Strong/weak + cue extract |
| `backend/tests/test_unit_enrichment_service.py` | Orchestrator; LLM not called when strong |
| `backend/tests/test_skill_graph_attach.py` | Rule/LLM payload with cues (extend) |

---

### Task 1: Migration + model + config

**Files:**
- Create: `backend/alembic/versions/p5q6r7s8t9u0_enrich_unit_signals.py` (revision id may change — match `alembic revision`)
- Modify: `backend/app/models/book_structure_preview.py`
- Modify: `backend/app/core/config.py`
- Modify: `backend/app/schemas/book_schema.py`

**Interfaces:**
- Produces: columns on `BookStructurePreviewDB` and `StructureUnitPreview`; settings `UNIT_ENRICH_ENABLED`, `UNIT_ENRICH_MAX_CHARS`, `UNIT_ENRICH_LLM_ENABLED`

- [ ] **Step 1: Re-check Alembic head**

```bash
cd backend && .venv/bin/alembic heads
```

Expected: shows current head (e.g. `o4p5q6r7s8t9`). Use that as `down_revision`.

- [ ] **Step 2: Update ORM**

In `backend/app/models/book_structure_preview.py`, add imports if needed (`DateTime`, `JSON` from SQLAlchemy / dialect) and columns after `depth_or_source`:

```python
from sqlalchemy import JSON  # or from sqlalchemy.dialects.postgresql import JSONB

language_focus = Column(String(1000), nullable=True)
grammar_cues = Column(JSON, nullable=True)
vocab_cues = Column(JSON, nullable=True)
content_summary = Column(String(2000), nullable=True)
enrichment_status = Column(String(20), nullable=True)
enriched_at = Column(TIMESTAMP(timezone=True), nullable=True)
enrichment_source = Column(String(20), nullable=True)
enrichment_method = Column(String(32), nullable=True)
```

Prefer `JSONB` on Postgres if the project already uses it elsewhere for consistency.

- [ ] **Step 3: Add settings**

In `backend/app/core/config.py` after `LEARN_UNIT_ENABLED`:

```python
UNIT_ENRICH_ENABLED: bool = True
UNIT_ENRICH_MAX_CHARS: int = 3000
UNIT_ENRICH_LLM_ENABLED: bool = True
```

- [ ] **Step 4: Extend `StructureUnitPreview`**

In `backend/app/schemas/book_schema.py`:

```python
language_focus: Optional[str] = None
grammar_cues: Optional[list[str]] = None
vocab_cues: Optional[list[str]] = None
content_summary: Optional[str] = None
enrichment_status: Optional[str] = None
enriched_at: Optional[datetime] = None
enrichment_source: Optional[str] = None
enrichment_method: Optional[str] = None
```

- [ ] **Step 5: Create and apply migration**

```bash
cd backend && .venv/bin/alembic revision --autogenerate -m "enrich unit signals on structure preview"
# Review file; ensure only book_structure_preview columns
.venv/bin/alembic upgrade head
```

Expected: upgrade succeeds; `\d book_structure_preview` shows new columns.


---

### Task 2: Excerpt builders (chunks → window → cap)

**Files:**
- Create: `backend/app/services/unit_enrichment_excerpt.py`
- Test: `backend/tests/test_unit_enrichment_excerpt.py`

**Interfaces:**
- Produces:
  - `join_chunk_texts(chunks: list[dict]) -> str`
  - `window_prefer_language_focus(raw: str) -> str`
  - `truncate_excerpt(text: str, max_chars: int) -> str`
  - `FOCUS_HEADING_RE` matching Grammar / Language focus / Vocabulary / Unit goals (case-insensitive)

- [ ] **Step 1: Write failing tests**

```python
# backend/tests/test_unit_enrichment_excerpt.py
from app.services.unit_enrichment_excerpt import (
    join_chunk_texts,
    truncate_excerpt,
    window_prefer_language_focus,
)


def test_join_chunk_texts_orders_by_chunk_index():
    chunks = [
        {"chunk_index": 1, "text": "second"},
        {"chunk_index": 0, "text": "first"},
    ]
    assert join_chunk_texts(chunks) == "first\n\nsecond"


def test_window_prefers_language_focus_heading():
    raw = "Intro fluff\n\nLanguage focus\nshould / must\nmore text"
    out = window_prefer_language_focus(raw)
    assert "Language focus" in out
    assert out.index("Language focus") == 0 or out.lstrip().startswith("Language focus")


def test_truncate_excerpt_respects_max():
    assert len(truncate_excerpt("a" * 5000, 3000)) == 3000
```

- [ ] **Step 2: Run tests — expect FAIL**

```bash
cd backend && .venv/bin/pytest tests/test_unit_enrichment_excerpt.py -v
```

Expected: import/collection error or FAIL.

- [ ] **Step 3: Implement minimal module**

```python
# backend/app/services/unit_enrichment_excerpt.py
from __future__ import annotations

import re

FOCUS_HEADING_RE = re.compile(
    r"(?im)^(?:\s*)(?:grammar|language\s+focus|vocabulary|unit\s+goals)\b[^\n]*$"
)


def join_chunk_texts(chunks: list[dict]) -> str:
    ordered = sorted(chunks, key=lambda c: int(c.get("chunk_index") or 0))
    parts = [(c.get("text") or "").strip() for c in ordered]
    return "\n\n".join(p for p in parts if p)


def window_prefer_language_focus(raw: str) -> str:
    if not raw:
        return ""
    m = FOCUS_HEADING_RE.search(raw)
    if not m:
        return raw
    return raw[m.start() :].lstrip()


def truncate_excerpt(text: str, max_chars: int) -> str:
    if max_chars < 1:
        return ""
    if len(text) <= max_chars:
        return text
    return text[:max_chars]
```

- [ ] **Step 4: Run tests — expect PASS**

```bash
cd backend && .venv/bin/pytest tests/test_unit_enrichment_excerpt.py -v
```


---

### Task 3: Heuristic strong/weak + cue extraction

**Files:**
- Create: `backend/app/services/unit_enrichment_heuristic.py`
- Test: `backend/tests/test_unit_enrichment_heuristic.py`

**Interfaces:**
- Consumes: excerpt string; `catalog_skills: list[dict]` with `slug`, `title`
- Produces:
  - `HeuristicResult` dataclass: `language_focus: str | None`, `grammar_cues: list[str]`, `vocab_cues: list[str]`, `strong: bool`
  - `run_heuristic(excerpt: str, *, unit_title: str, catalog_skills: list[dict]) -> HeuristicResult`

**Strong rule (spec):**

- `grammar_cues` has ≥1 slug ∈ catalog, **OR**
- `language_focus` non-empty **and** matches ≥1 catalog slug/title token

- [ ] **Step 1: Write failing tests**

```python
from app.services.unit_enrichment_heuristic import run_heuristic

CATALOG = [
    {"slug": "modals_should_must", "title": "Should / must (advice/obligation)"},
    {"slug": "present_simple", "title": "Present simple"},
]


def test_language_focus_heading_yields_strong_cue():
    excerpt = "Language focus\nPractice should and must for advice.\n"
    r = run_heuristic(excerpt, unit_title="Unit 8 Fit and healthy", catalog_skills=CATALOG)
    assert r.strong is True
    assert "modals_should_must" in r.grammar_cues or (
        r.language_focus and "should" in r.language_focus.lower()
    )


def test_thematic_title_alone_is_weak_without_body_cues():
    r = run_heuristic(
        "Some reading about people in a town.",
        unit_title="Unit 1 People",
        catalog_skills=CATALOG,
    )
    assert r.strong is False
```

Tune assertions to match the heuristic you implement (slug-in-cues is the clearest strong signal).

- [ ] **Step 2: Run — expect FAIL**

```bash
cd backend && .venv/bin/pytest tests/test_unit_enrichment_heuristic.py -v
```

- [ ] **Step 3: Implement heuristic**

Implement in `unit_enrichment_heuristic.py`:

1. Find focus block via `FOCUS_HEADING_RE` / following lines → `language_focus` (trim, max ~200 chars).
2. For each catalog skill, if slug tokens or distinctive title tokens appear in excerpt (word-ish), append slug to `grammar_cues` (dedupe, preserve order).
3. Light `vocab_cues` from unit title words (filter stopwords) — optional, not catalog invent.
4. `strong = bool(set(grammar_cues) & catalog_slugs) or (language_focus and _focus_matches_catalog(...))`.

Keep pure (no DB, no LLM).

- [ ] **Step 4: Run — expect PASS**

```bash
cd backend && .venv/bin/pytest tests/test_unit_enrichment_heuristic.py -v
```


---

### Task 4: Enrich orchestrator + weak-only LLM

**Files:**
- Create: `backend/app/services/unit_enrichment_llm.py`
- Create: `backend/app/services/unit_enrichment_service.py`
- Test: `backend/tests/test_unit_enrichment_service.py`
- Modify: use `get_unit_chunks` from `book_chunk_service.py`; PDF fallback via `book_indexing_service.extract_pages_text` + download helper from `book_structure_service`

**Interfaces:**
- Produces:
  - `enrich_units_for_book(db, book_id, *, force: bool = False) -> dict` meta counts
  - `enrich_unit_signals_llm(...)` only called from orchestrator when weak
- Consumes: excerpt helpers, heuristic, `settings.UNIT_ENRICH_*`, `chat_json`

- [ ] **Step 1: Write failing orchestrator tests (mock chunks + LLM)**

```python
from unittest.mock import MagicMock, patch
import pytest

# Pseudocode shape — adapt to how you inject chunk loading:

def test_strong_heuristic_skips_llm(monkeypatch):
    # Arrange unit + book ready mocks OR patch load_excerpt + run_heuristic to return strong
    # Patch enrich LLM; assert not called; method == "heuristic"
    ...


def test_weak_heuristic_calls_llm_once(monkeypatch):
    # Heuristic weak; LLM returns grammar_cues with catalog slug
    # Assert LLM called once; method == "heuristic+llm"
    ...
```

Include at least:

- strong → LLM not called  
- weak → LLM called once with excerpt length ≤ `UNIT_ENRICH_MAX_CHARS`  
- empty excerpt → `skipped`, LLM not called  

- [ ] **Step 2: Run — expect FAIL**

```bash
cd backend && .venv/bin/pytest tests/test_unit_enrichment_service.py -v
```

- [ ] **Step 3: Implement LLM helper**

```python
# unit_enrichment_llm.py — outline
ENRICH_SYSTEM = """You extract ESL unit teaching signals for a FIXED CEFR catalog.
Return JSON only:
{"language_focus":str|null,"grammar_cues":[str],"vocab_cues":[str],"content_summary":str|null}
Rules:
- Prefer grammar_cues slugs from catalog_skills[].slug
- Do not invent catalog skills as attach results
- Keep language_focus short
"""

def enrich_unit_signals_llm(*, cefr_level, book_title, unit_title, excerpt, catalog_skills) -> dict:
    ...
```

Validate lightly: `grammar_cues` list of str; unknown slugs allowed as labels but prefer catalog.

- [ ] **Step 4: Implement orchestrator**

`unit_enrichment_service.py` flow per unit:

1. If not `settings.UNIT_ENRICH_ENABLED`: return early meta.  
2. Load book; require `ready`.  
3. For each preview unit: skip if not `force` and `enrichment_status == "done"`.  
4. `chunks = get_unit_chunks(book_id, unit.id)` → `join_chunk_texts`; else PDF fallback (download once per book if possible).  
5. Window + truncate to `UNIT_ENRICH_MAX_CHARS`.  
6. `run_heuristic(...)`.  
7. If strong → persist, `method=heuristic`.  
8. Elif weak and `UNIT_ENRICH_LLM_ENABLED` and API key → LLM → merge cues → `method=heuristic+llm`.  
9. Else persist heuristic (possibly empty) → `done` or `failed`/`skipped`.  
10. Set `enriched_at=now(utc)`, `enrichment_source`.  
11. `await db.commit()` (or flush per batch then commit once).

Return meta:

```python
{
  "enriched": n,
  "method_counts": {"heuristic": x, "heuristic+llm": y, "skipped": z},
  "source_counts": {"chunks": a, "pdf_skim": b},
}
```

- [ ] **Step 5: Run tests — PASS**

```bash
cd backend && .venv/bin/pytest tests/test_unit_enrichment_service.py tests/test_unit_enrichment_excerpt.py tests/test_unit_enrichment_heuristic.py -v
```


---

### Task 5: Wire sync-skills + enrich-units API

**Files:**
- Modify: `backend/app/services/skill_graph_service.py`
- Modify: `backend/app/api/admin_quiz.py`
- Modify: `backend/app/api/admin_books.py`
- Test: extend `backend/tests/test_skill_graph_attach.py` or add `backend/tests/test_admin_enrich_units_api.py` (optional smoke with mocks)

**Interfaces:**
- `sync_skills_from_preview` calls `enrich_units_for_book(db, book_id, force=False)` when `UNIT_ENRICH_ENABLED` before attach; merges enrich meta into return `meta`
- `POST /api/v1/admin/books/{book_id}/enrich-units` → `enrich_units_for_book(..., force=True)`

- [ ] **Step 1: Update `_unit_dicts` to include signals**

```python
def _unit_dicts(units: list[BookStructurePreviewDB]) -> list[dict[str, Any]]:
    return [
        {
            "id": u.id,
            "title": u.title,
            "unit_index": u.unit_index,
            "depth_or_source": u.depth_or_source,
            "language_focus": u.language_focus,
            "grammar_cues": u.grammar_cues or [],
            "vocab_cues": u.vocab_cues or [],
            "content_summary": u.content_summary,
        }
        for u in units
    ]
```

- [ ] **Step 2: Call enrich at start of `sync_skills_from_preview`**

After `_load_ready_book_and_units`:

```python
enrich_meta = {}
if getattr(settings, "UNIT_ENRICH_ENABLED", True):
    from app.services.unit_enrichment_service import enrich_units_for_book
    enrich_meta = await enrich_units_for_book(db, book_id, force=False)
    # refresh units from DB after enrich
    book, units = await _load_ready_book_and_units(db, book_id)
```

Include `enrich_meta` keys in returned `meta`. Best-effort: wrap enrich in try/except log + `enrichment_incomplete: True`.

- [ ] **Step 3: Add admin endpoint**

In `admin_books.py`:

```python
@router.post(
    "/{book_id}/enrich-units",
    dependencies=[Depends(require_permission("book:manage"))],
)
async def admin_enrich_units(book_id: int, db: AsyncSession = Depends(get_db)):
    try:
        from app.services.unit_enrichment_service import enrich_units_for_book
        meta = await enrich_units_for_book(db, book_id, force=True)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"data": {"book_id": book_id, **meta}}
```

- [ ] **Step 4: Extend sync response** in `admin_quiz.py` to pass through enrich meta fields (`method_counts`, `source_counts`, `enrichment_incomplete`).

- [ ] **Step 5: Manual smoke (docker)**

```bash
# After migrate + restart api
curl -s -X POST "$API/api/v1/admin/books/48/enrich-units" -H "Authorization: Bearer $TOKEN"
curl -s -X POST "$API/api/v1/admin/books/48/sync-skills" -H "Authorization: Bearer $TOKEN"
```

Expected: enrich meta present; mapped/unmapped may change vs baseline; `edge_count_added` still 0.


---

### Task 6: Attach LLM + rule use cues (no full text)

**Files:**
- Modify: `backend/app/services/skill_graph_llm_service.py`
- Modify: `backend/app/services/skill_graph_service.py` (`build_rule_attach_mappings`, `_resolve_attach_mappings` input)
- Test: `backend/tests/test_skill_graph_attach.py` (add cases)

**Interfaces:**
- Attach unit objects may include `grammar_cues`, `language_focus`, …  
- Prompt must instruct: prefer cues when title thematic; still one slug; no invent  
- Rule: after title slug miss, map first `grammar_cues` entry ∈ `catalog_slugs`

- [ ] **Step 1: Failing test for rule fallback via cues**

```python
def test_rule_attach_uses_grammar_cue_when_title_unmapped():
    units = [
        {
            "unit_index": 0,
            "title": "Unit 8 Fit and healthy",
            "grammar_cues": ["modals_should_must"],
        }
    ]
    mappings = build_rule_attach_mappings(
        units, catalog_slugs={"modals_should_must", "present_simple"}
    )
    assert mappings[0]["slug"] == "modals_should_must"
    assert mappings[0]["exclude"] is False
```

- [ ] **Step 2: Run — FAIL then implement rule branch — PASS**

- [ ] **Step 3: Update `ATTACH_SYSTEM_PROMPT`**

Add rules:

- Prefer `grammar_cues` / `language_focus` when `title` is thematic  
- Never require raw page text; fields shown are sufficient  
- Still at most one slug; no invent  

Ensure `_resolve_attach_mappings` passes enriched fields into `llm_input_units` (not only title).

- [ ] **Step 4: Assert attach path never sends excerpt**

In unit test for building llm_input_units (pure assert keys):  
`assert "excerpt" not in unit and "text" not in unit`.


---

### Task 7: Frontend types + minimal UI

**Files:**
- Modify: `frontend/my-app/lib/admin-books.ts`
- Modify: `frontend/my-app/components/admin/BookQuizPanel.tsx` (and/or books preview if structure units shown)
- Optional: button “Enrich units” calling new API before sync

**Interfaces:**
- `StructureUnitPreview` includes optional enrich fields  
- `enrichBookUnits(bookId: number): Promise<...>`

- [ ] **Step 1: Extend TS types** in `admin-books.ts` to match schema fields.

- [ ] **Step 2: Add client**

```typescript
export async function enrichBookUnits(bookId: number) {
  const res = await authFetch(`/api/v1/admin/books/${bookId}/enrich-units`, {
    method: "POST",
  });
  // parse error like other admin helpers
  return res.json();
}
```

- [ ] **Step 3: UI minimal**

In attach/sync panel:

- After sync (or when preview loaded), show under each unit: `language_focus` and `grammar_cues` join if present  
- Optional badge: enrichment_method  
- Optional button: Enrich units → then user syncs (or sync already enriches missing)

Keep styling consistent with existing admin panel; no redesign.

- [ ] **Step 4: Smoke in browser** on Empower book — cues visible after enrich/sync.


---

### Task 8: Verification on Empower A2 + docs

**Files:**
- Modify: `docs/superpowers/specs/2026-07-31-enrich-unit-signals-attach-design.md` — set Status to Implementing/Implemented  
- Optional note in `backend/README.md` under admin books: enrich + re-sync without re-index

- [x] **Step 1: Run full relevant pytest**

```bash
cd backend && .venv/bin/pytest \
  tests/test_unit_enrichment_excerpt.py \
  tests/test_unit_enrichment_heuristic.py \
  tests/test_unit_enrichment_service.py \
  tests/test_skill_graph_attach.py \
  tests/test_skill_graph_validate.py -v
```

Expected: PASS.

- [x] **Step 2: Ops on live/dev DB (book 48 or Empower ready id)**

1. `alembic upgrade head` (if not done)  
2. `POST enrich-units`  
3. `POST sync-skills`  
4. Record before/after: mapped_count, unmapped list, method_counts, source_counts  

Expected: no new catalog skills; unmapped ≤ baseline; most `enrichment_source=chunks`.

- [x] **Step 3: Update spec status line** to Implemented (date) + link this plan.


---

## Spec coverage checklist

| Spec item | Task |
|-----------|------|
| Migration enrich columns | Task 1 |
| Config UNIT_ENRICH_* | Task 1 |
| Chunks primary / PDF fallback | Task 4 |
| Window + cap 3000 | Task 2 |
| Heuristic first + strong/weak | Task 3–4 |
| LLM weak-only | Task 4 |
| Persist signals, no excerpt | Task 4 |
| sync enrich-missing + enrich-units API | Task 5 |
| Attach cues only / no full text | Task 6 |
| Admin UI signals | Task 7 |
| Empower verify / no re-index | Task 8 |
| No seed expansion / no multi-attach | Global constraints |

---

## Out of plan

- Multi-attach; seed topic vocab; overlap chunker rewrite; auto-index/AI merge bug; enrich pre-ready  

---

*Plan 2026-07-31 — ready for subagent-driven or inline execution.*

**Execution note:** Implement code + tests only. Never `git commit` / `git add` for the user.
