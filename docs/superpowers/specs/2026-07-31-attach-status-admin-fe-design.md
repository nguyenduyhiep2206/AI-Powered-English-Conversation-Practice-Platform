# Design: Attach status from DB + catalog skill title on admin FE

**Date:** 2026-07-31  
**Status:** Approved (chat)  
**Depends on:** Band ladder book attach (`2026-07-30-band-ladder-book-attach-design.md`)

---

## Problem

Admin “Attach to CEFR catalog” only shows mapping status after a successful sync in the current browser session. Reload loses Primary/Linked/Excluded rows and catalog skill ids. The Catalog skill column shows `#skill_id` only. There is no clear Retry when sources already exist in `book_skill_sources`.

## Goals

- Load existing attach rows from DB when opening a book on admin quiz FE
- Show **skill title** in Catalog skill column
- If sources already exist → button label **Retry attach** (same POST replace semantics)
- Keep unmapped / excluded / primary status badges accurate from persisted data

## Non-goals

- Admin CRUD for catalog skills
- Changing attach LLM/rule algorithm
- Persisting unmapped units as DB rows (still derived: units without a source)

## Approach

**GET** ` /api/v1/admin/quiz/books/{book_id}/skill-sources`  
Join `book_skill_sources` → `learning_skills`; return sources with `skill_title`. Derive `unmapped_units` from structure units that have no source for this book.

**POST** `sync-skills` response: add `skill_title` on each source (same shape as GET).

**FE** `BookQuizPanel`: on book load call GET; fill table; button **Attach units** vs **Retry attach** based on `sources.length > 0`.

## API shape

```json
{
  "data": {
    "book_id": 1,
    "source_count": 12,
    "excluded": 0,
    "mapped_count": 12,
    "unmapped_units": [{ "unit_index": 3, "unit_title": "Review 1" }],
    "sources": [
      {
        "id": 10,
        "skill_id": 42,
        "skill_title": "Present simple: be",
        "unit_id": 100,
        "unit_title": "Unit 1",
        "section_title": null,
        "is_excluded": false,
        "is_primary": true
      }
    ]
  }
}
```

## FE behavior

| State | Button | Table |
|-------|--------|-------|
| No sources in DB | Attach units | Status — until first sync; Catalog skill — |
| Has sources | Retry attach | Status + skill title from GET |
| After retry POST | Retry attach | Refreshed from response / GET |

Optional confirm dialog before Retry (destructive replace of sources).

## Out of scope follow-ups

- Show slug under title
- Partial re-attach of a single unit
