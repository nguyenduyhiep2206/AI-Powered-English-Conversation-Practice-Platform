# Tutor Goal × CEFR Topic Catalog Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans. Steps use checkbox (`- [ ]`) syntax.

**Goal:** Ship a curated tutor topic bank composed at runtime by learner CEFR + goal (primary/explore), not a flat Promova screenshot clone.

**Architecture:** Seed tagged topics with `goal_tags` and CEFR ranges; `list_catalog_scenarios` composes primary vs explore; FE shows two sections; optional linked skills on START.

**Tech Stack:** FastAPI, SQLAlchemy, Alembic, existing tutor FE.

**Spec:** `docs/superpowers/specs/2026-08-04-tutor-promova-topic-catalog-design.md` (v2 Exa)

## Global Constraints

- Curated offline seed — no per-user LLM catalog generation
- Goal = compose/filter, not sort-only
- CEFR = eligibility range + tone (no blind 16×5 clone)
- Deactivate legacy 4-template slugs; keep FK-safe
- Do not commit unless the user explicitly asks

---

## File map

| File | Responsibility |
|------|----------------|
| alembic migration | `goal_tags`, `linked_skill_slugs`, `theme_tags` |
| `models/scenario.py` | ORM |
| `seeds/scenarios.py` | Topic bank + range materialize + deactivate legacy |
| `tutor_service.py` | Compose primary/explore + sort + resolve links |
| `tutor_schema.py` / `api/tutor.py` | `section`, `recommended`, `goal_tags` |
| tests | seed shape, compose by goal/level |
| `ai-tutor/page.tsx` + `lib/tutor.ts` | Two sections UI |

---

### Task 1: Schema

- [ ] Migration + model for JSON `goal_tags`, `linked_skill_slugs`, `theme_tags`

### Task 2: Seed topic bank

- [ ] Templates per spec §5 with `goal_tags`, `min`/`max` CEFR
- [ ] Materialize only in-range levels
- [ ] Deactivate legacy slugs; assert assembler categories covered per level
- [ ] Tests for row counts / tags / inactive legacy

### Task 3: Compose API

- [ ] Map `GoalEnum` → primary tags (spec §4)
- [ ] Primary + explore + recommended + weak-skill boost
- [ ] Catalog START → linked skill ids ≤3
- [ ] Service/API tests

### Task 4: FE

- [ ] Sections “For your goal” / “More topics”
- [ ] Recommended badge

### Task 5: Docs

- [ ] Mark spec Accepted after implement; cross-link roleplay design

---

## Execution handoff

Wait for user review of spec v2. Implement only when asked; no commit until asked.
