# Review prompt — Core Inventory catalogs A2 / B1 / B2 / C1 (batch)

Copy everything below the line into a fresh AI chat (attach PDFs + the listed JSONL/MD files).

---

# Role
You are a senior ELT curriculum reviewer auditing a CEFR **skill graph catalog** derived from the British Council–EAQUALS Core Inventory. Evaluate **A2, B1, B2, and C1 in one pass**. Do **not** regenerate the catalogs from scratch unless a defect cannot be described as a concrete fix.

# Gold-standard reference (style + schema)
Completed **A1** catalog (already reviewed through multiple rounds):
- `skills.jsonl` — 46 nodes
- `edges.jsonl` — 43 edges
- `summary.md`, `validation_report.md`

Use A1 for:
- node granularity (one teachable Learn+Practice chunk)
- `skill_type` split: `grammar | vocabulary | functional | reading`
- slug / title style, `difficulty_in_level` 1–10, `source_refs`, sparse prerequisite edges
- known A1 defect patterns to **re-check on A2–C1** (below)

# Sources of truth (do not invent inventory)
Use ONLY the BC–EAQUALS Core Inventory materials provided:
- Essential Guide poster pages (Functions / Grammar / Discourse Markers / Vocabulary / Topics per level)
- Appendix D (Mapping Language Content — first-appearance / core vs less-core)
- Appendix E (Exponents)
- Level poster pages (Communicative / Grammar & Vocabulary Objectives / Language Work)

If unsure whether an item belongs at a level, mark **UNCERTAIN** — do not guess.

# Files under review
Base path: `backend/app/seeds/core_inventory/`

| Level | Skills | Within-level edges | Cross-level bridges | Author notes | Machine self-check |
|-------|--------|--------------------|---------------------|--------------|--------------------|
| A2 | `skills_a2.jsonl` | `edges_a2.jsonl` | `edges_bridge_a2.jsonl` (from A1) | `summary_a2.md` | `self_validation_a2.md` |
| B1 | `skills_b1.jsonl` | `edges_b1.jsonl` | `edges_bridge_b1.jsonl` (from A2) | `summary_b1.md` | `self_validation_b1.md` |
| B2 | `skills_b2.jsonl` | `edges_b2.jsonl` | `edges_bridge_b2.jsonl` (from B1) | `summary_b2.md` | `self_validation_b2.md` |
| C1 | `skills_c1.jsonl` | `edges_c1.jsonl` | `edges_bridge_c1.jsonl` (from B2) | `summary_c1.md` | `self_validation_c1.md` |

Also read A1: `skills.jsonl`, `edges.jsonl` for bridging and style comparison.

**Schema (must match A1 — flag any deviation):**
```json
{"slug":"snake_case","title":"≤60 chars","cefr_level":"A2|B1|B2|C1","skill_type":"grammar|vocabulary|functional|reading","difficulty_in_level":1-10,"source_refs":["poster:…","appendixD:…","appendixE:…"],"notes":"optional"}
{"from_slug":"…","to_slug":"…","relation":"prerequisite"}
```

A2 must **incorporate** (not duplicate/rename away) these scaffold slugs if still intended:
`vocab_travel_services`, `vocab_colours_clothes`, `adjectives_comparative_a2`, `directions_a2`.

# Defect patterns that failed A1 review (re-check every level)
1. **Difficulty inversions:** any edge where `from.difficulty_in_level > to.difficulty_in_level`
2. **Isolated nodes:** degree 0 (no in and no out edge within-level; bridges alone do not count as “connected enough” unless the node also has ≥1 within-level edge **or** you explicitly justify foundation→bridge-only isolates — default policy: **every node needs ≥1 within-level edge**)
3. **Over-/under-split:** one poster item → many tiny nodes, or unrelated modals/topics merged into one
4. **Wrong level:** item that Appendix D marks first at another level (classic A1 fail: A2-only vocab seeded at A1)
5. **Missing reading:** every level needs ≥1 `skill_type: reading` mapped to that poster’s READING can-dos
6. **Functional thinness / grammar overweight:** A1 ended grammar-heavy; flag if functional/vocab coverage of the Essential Guide column is thin
7. **Dangling slugs** in edges or bridges
8. **Cycles** in within-level graph
9. **Forced bridges:** cross-level edges without a genuine pedagogical prereq
10. **Taxonomy drift:** discourse markers tagged as grammar without note; topics duplicated as both vocab and functional with no merge note

# Review procedure (do all four levels)

## Pass A — Structural (per level)
Re-run or re-derive:
1. Acyclic within-level graph?
2. Zero difficulty inversions?
3. Zero isolated nodes (within-level)?
4. Zero dangling slug refs (within-level + bridges that touch this level)?
5. Node count in **45–65** (target 45–55)?
6. ≥1 `reading` node?
7. Duplicate slugs / duplicate near-identical titles?

Self-validation files already claim PASS — **independently verify**; if they lie, say so.

## Pass B — Coverage vs Core Inventory (per level)
Against that level’s Essential Guide / poster tables:
- List **UNMAPPED** Functions, Grammar, Discourse Markers, Vocabulary, Topics (core / non-italic first; italic “less core” only if claimed in summary as gap-fill)
- For each, require author treatment: mapped to slug | MERGED (slug + reason) | OMITTED (reason) | UNCERTAIN
- Flag invents: nodes that do not appear in sources
- Flag wrong-level placements vs Appendix D

## Pass C — Granularity & pedagogy (per level)
- Compare chunk size to A1 (e.g. do not require 5 future-form nodes; do not glue unrelated modals)
- Difficulty ordering: earlier Appendix D sub-band ≈ lower difficulty; grammar dependencies respected
- Edge sparsity: prefer **1–3** prerequisites per node; flag hub nodes with >5 in-edges or kitchen-sink prereq fans
- Each edge: is the pedagogical “must know A before B” claim real?

## Pass D — Cross-level bridges (A1→A2→B1→B2→C1)
For each `edges_bridge_<level>.jsonl`:
- `from_slug` must exist in previous level (A1 uses `skills.jsonl`)
- `to_slug` must exist in current level
- Prefer bridging from **high-difficulty terminals** of previous level into **low-difficulty foundations** of next — flag bridges that invent soft theme associations
- Flag missing obvious bridges (e.g. past simple → past continuous) as **suggestion**, not automatic FAIL
- Confirm levels can still start independently (bridges sparse, not a hard gating wall)

## Pass E — Cross-level consistency (whole suite)
- Same construct renamed across levels without progression (`past_simple` vs `past_simple_a2` OK if noted; random renames FAIL)
- Overlap / near-duplicate teaching target across adjacent levels without clear progression
- Mix of skill_types drifting from A1 proportions without pedagogical reason (especially zero functional or zero vocab)
- Title length, slug style, source_refs quality vs A1

# Severity rubric
- **BLOCKER:** inversions, cycles, dangling slugs, wrong CEFR level for a core item, missing reading node, count outside 45–65, isolated nodes, invented non-inventory nodes presented as core
- **MAJOR:** large Essential Guide coverage gaps unmarked, bad merges, over-connected graph, weak/wrong bridges, scaffold A2 slugs dropped
- **MINOR:** title clarity, source_refs incomplete, difficulty ties that could be reordered, notes missing on MERGED items
- **NIT:** wording only

# Output format (strict)

Write one report file content (markdown) with this structure:

```markdown
# Multi-level catalog review — A2 / B1 / B2 / C1

## Executive verdict
- Overall: PASS | PASS WITH FIXES | FAIL
- One paragraph: biggest systemic issues across levels

## Scorecard
| Level | Nodes | Edges | Bridges | Structural | Coverage | Pedagogy | Bridges | Verdict |
|-------|------:|------:|--------:|------------|----------|----------|---------|---------|
| A2 | | | | PASS/FAIL | … | … | … | … |
| B1 | | | | | | | | |
| B2 | | | | | | | | |
| C1 | | | | | | | | |

## Structural findings (all levels)
### Blockers
- [A2|B1|B2|C1] …
### Majors
…

## Coverage gaps & invents (by level)
### A2
#### Unmapped / OMITTED without reason
#### Invented / wrong-level
### B1
…
(same for B2, C1)

## Edge & difficulty defects
List every inversion, cycle, isolate, dangling slug as:
`LEVEL | type | from → to | detail`

## Bridge review
### A1→A2
### A2→B1
### B1→B2
### B2→C1
For each: keep / drop / replace suggestions (slug pairs)

## Required fixes (ordered, actionable)
1. [BLOCKER][A2] file + change…
2. …
Do **not** dump a full rewritten catalog unless <15 nodes are affected; prefer patch lists (add/remove/retag edges, rename slug, retarget difficulty).

## Optional improvements
…

## UNCERTAIN items (human decision needed)
|
```

# Constraints
- Evaluate **all four levels in this single response** — do not stop after A2.
- Prefer concrete slug-level evidence over vague praise.
- Do not “fix” inventing content into the catalog; flag gaps instead.
- Self-validation PASS is necessary but **not sufficient** — coverage and pedagogy can still FAIL.
- End with a clear go / no-go for seeding each level into the DB.
