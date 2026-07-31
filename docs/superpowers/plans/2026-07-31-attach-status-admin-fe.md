# Attach status admin FE — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans (or implement inline for this small plan).  
> **Goal:** Load `book_skill_sources` + skill titles on admin quiz FE; Retry attach when already attached.

**Spec:** `docs/superpowers/specs/2026-07-31-attach-status-admin-fe-design.md`

## Files

| File | Change |
|------|--------|
| `backend/app/services/skill_graph_service.py` | `list_book_skill_sources` + serialize helper with `skill_title` |
| `backend/app/api/admin_quiz.py` | GET skill-sources; enrich POST sync response with titles |
| `backend/tests/test_skill_graph_attach.py` (or new) | Test list sources + title |
| `frontend/my-app/lib/admin-quiz.ts` | Types + `fetchBookSkillSources` |
| `frontend/my-app/components/admin/BookQuizPanel.tsx` | Load on mount; title column; Retry label |

## Tasks

### Task 1: Backend list + skill_title

- Add `serialize_skill_source(source, skill_title) -> dict`
- Add `async def list_book_skill_sources(db, book_id) -> tuple[list[dict], dict]`  
  Load book units (preview), left-join sources+skills, build sources with titles, unmapped list for units without source
- GET `/books/{book_id}/skill-sources`
- POST sync: after create, load titles for returned sources (batch select skills by id)

### Task 2: FE wire-up

- `SkillSourceRow.skill_title?: string`
- `fetchBookSkillSources(bookId)`
- On mount: refresh sources from GET (alongside drafts/unit meta)
- Button: `hasSynced ? "Retry attach" : "Attach units"`; confirm on retry
- Catalog skill cell: `source.skill_title ?? \`#${source.skill_id}\``

### Task 3: Verify

- Run targeted pytest for list/sync serialization
- Manual: open quiz page for attached book → see titles + Retry
