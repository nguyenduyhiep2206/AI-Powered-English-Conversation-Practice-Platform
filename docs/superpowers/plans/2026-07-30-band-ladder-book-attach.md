# Band Ladder A1+A2 + Book Attach Implementation Plan

> **Status:** Accepted / largely implemented — Tasks 1–4 (origin, seed, attach validate/LLM, attach orchestration) in code. Task 5 (assembler coverage filter) deferred to theme-unit commit (same working-tree file).

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Seed a fixed A1+A2 skill catalog; change book sync to attach units onto that catalog only; assemble roadmaps only from covered catalog skills.

**Architecture:** Catalog is the source of truth (`learning_skills.origin=catalog`). `sync_skills_from_preview` becomes attach-only: LLM/rule maps units → existing catalog slugs, writes `book_skill_sources`, never inserts unknown skills or rewrites edges. Assembler filters to skills with at least one non-excluded source. Legacy non-catalog skills are deactivated after seed.

**Tech Stack:** FastAPI, SQLAlchemy async, Alembic, LangChain `chat_json`, pytest, existing seed pattern (`app.seeds.scenarios`).

**Spec:** `docs/superpowers/specs/2026-07-30-band-ladder-book-attach-design.md`

## Global Constraints

- MVP seed levels: **A1 + A2 only** (no B1–C1 catalog in this plan)
- Book sync **must not** create skills whose slug is outside the catalog for that CEFR level
- Sync **must not** add/rewrite `skill_edges` or overwrite catalog `difficulty_in_level`
- Assemble: only `is_active` skills with ≥1 `book_skill_sources` where `is_excluded=false`
- Auto-attach MVP (no human approve gate); return `unmapped_units` in sync response
- No coverage admin UI / CRUD API in this plan (phase 2)
- No frontend redesign required beyond optional copy later
- Commit style: conventional (`feat:`, `test:`, `fix:`) — only when the executing session is allowed to commit
- Alembic current head at plan time: `n3o4p5q6r7s8` (re-check `alembic heads` before writing migration)

---

## File map

| File | Responsibility |
|------|----------------|
| `backend/alembic/versions/o4p5q6r7s8t9_add_learning_skill_origin.py` | Add `learning_skills.origin` |
| `backend/app/models/learning_skill.py` | ORM `origin` column |
| `backend/app/seeds/cefr_ladder_a1_a2.py` | Idempotent catalog + edges seed |
| `backend/app/services/skill_graph_llm_service.py` | Attach-only LLM prompt + parse |
| `backend/app/services/skill_graph_validate.py` | Validate attach payload against catalog slugs |
| `backend/app/services/skill_graph_service.py` | Attach orchestration; no create-unknown; no edge union from sync |
| `backend/app/services/roadmap_assembler_service.py` | Coverage filter in `load_active_skills` / plan |
| `backend/app/api/admin_quiz.py` | Sync response: mapped/unmapped/excluded |
| `backend/tests/test_cefr_ladder_seed.py` | Seed idempotency + sizes |
| `backend/tests/test_skill_graph_attach.py` | Attach-only behavior (no new skills) |
| `backend/tests/test_roadmap_assembler_service.py` | Coverage filter cases |

---

### Task 1: Migration + model `origin`

**Files:**
- Create: `backend/alembic/versions/o4p5q6r7s8t9_add_learning_skill_origin.py`
- Modify: `backend/app/models/learning_skill.py`
- Test: `backend/tests/test_learning_skill_origin_model.py` (import/smoke) or rely on migration upgrade in Task 2 seed tests

**Interfaces:**
- Produces: `LearningSkillDB.origin: str` with values `"catalog"` \| `"legacy"`; DB default `"legacy"` for existing rows; seed sets `"catalog"`

- [ ] **Step 1: Update model**

In `backend/app/models/learning_skill.py`, add after `is_active`:

```python
origin = Column(String(20), nullable=False, server_default="legacy")
```

- [ ] **Step 2: Write Alembic revision**

Re-check head: `cd backend && .venv/bin/alembic heads`

```python
"""add learning_skills.origin

Revision ID: o4p5q6r7s8t9
Revises: n3o4p5q6r7s8
"""
from alembic import op
import sqlalchemy as sa

revision = "o4p5q6r7s8t9"
down_revision = "n3o4p5q6r7s8"  # replace if heads differ
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "learning_skills",
        sa.Column("origin", sa.String(length=20), nullable=False, server_default="legacy"),
    )


def downgrade() -> None:
    op.drop_column("learning_skills", "origin")
```

- [ ] **Step 3: Run migration**

Run: `cd backend && .venv/bin/alembic upgrade head`  
Expected: upgrade succeeds; column exists.

- [ ] **Step 4: Commit**

```bash
git add backend/app/models/learning_skill.py backend/alembic/versions/o4p5q6r7s8t9_add_learning_skill_origin.py
git commit -m "$(cat <<'EOF'
feat: add learning_skills.origin for catalog vs legacy

EOF
)"
```

---

### Task 2: Seed A1+A2 catalog + edges

**Files:**
- Create: `backend/app/seeds/cefr_ladder_a1_a2.py`
- Create: `backend/tests/test_cefr_ladder_seed.py`

**Interfaces:**
- Produces: `async def seed_cefr_ladder(db: AsyncSession) -> dict` returning `{"a1": int, "a2": int, "edges": int}`
- CLI: `python -m app.seeds.cefr_ladder_a1_a2` (mirror `scenarios.py`)
- Catalog skills: `origin="catalog"`, `is_active=True`, `skill_type` mostly `grammar`
- After upsert catalog: set `is_active=False` for A1/A2 skills where `origin != "catalog"` OR slug not in seed set for that level (treat as legacy)

**Catalog data (use exactly these lists unless pedagogy review changes them in the same PR):**

A1 (`cefr_level=A1`), ~22 skills — `(slug, title, difficulty_in_level, skill_type)`:

```python
A1_SKILLS = [
    ("be_present", "Verb to be (present)", 1, "grammar"),
    ("subject_pronouns", "Subject pronouns", 1, "grammar"),
    ("articles_a_an_the", "Articles a/an/the (basic)", 2, "grammar"),
    ("this_that_these_those", "This/that/these/those", 2, "grammar"),
    ("possessives", "Possessive adjectives", 3, "grammar"),
    ("have_got", "Have got", 3, "grammar"),
    ("there_is_are", "There is / there are", 3, "grammar"),
    ("present_simple", "Present simple", 4, "grammar"),
    ("present_continuous", "Present continuous", 5, "grammar"),
    ("can_cant", "Can / can't (ability)", 5, "grammar"),
    ("imperatives", "Imperatives", 5, "grammar"),
    ("wh_questions_basic", "Basic Wh- questions", 6, "grammar"),
    ("prepositions_place", "Prepositions of place", 6, "grammar"),
    ("prepositions_time_basic", "Prepositions of time (in/on/at)", 6, "grammar"),
    ("countable_uncountable_basic", "Countable / uncountable (basic)", 7, "grammar"),
    ("some_any", "Some / any", 7, "grammar"),
    ("past_simple_be", "Past simple of be", 8, "grammar"),
    ("past_simple_regular", "Past simple regular verbs", 8, "grammar"),
    ("past_simple_irregular_common", "Past simple common irregulars", 9, "grammar"),
    ("going_to_future", "Going to (future plans)", 9, "grammar"),
    ("everyday_vocab_people", "Everyday vocab: people & jobs", 4, "vocabulary"),
    ("everyday_vocab_places", "Everyday vocab: places & directions", 5, "vocabulary"),
]
```

A2:

```python
A2_SKILLS = [
    ("present_simple_vs_continuous", "Present simple vs continuous", 2, "grammar"),
    ("past_continuous", "Past continuous", 3, "grammar"),
    ("past_simple_vs_continuous", "Past simple vs continuous", 4, "grammar"),
    ("present_perfect_basic", "Present perfect (experience/just)", 5, "grammar"),
    ("present_perfect_vs_past", "Present perfect vs past simple", 6, "grammar"),
    ("will_future", "Will (predictions/decisions)", 4, "grammar"),
    ("going_to_vs_will", "Going to vs will", 5, "grammar"),
    ("comparatives_superlatives", "Comparatives & superlatives", 3, "grammar"),
    ("quantifiers_much_many", "Quantifiers much/many/a lot of", 3, "grammar"),
    ("modals_should_must", "Should / must (advice/obligation)", 5, "grammar"),
    ("modals_have_to", "Have to / don't have to", 5, "grammar"),
    ("first_conditional", "First conditional", 7, "grammar"),
    ("second_conditional_intro", "Second conditional (intro)", 8, "grammar"),
    ("passive_present_basic", "Present passive (basic)", 7, "grammar"),
    ("used_to", "Used to", 6, "grammar"),
    ("gerunds_infinitives_basic", "Gerunds & infinitives (basic)", 6, "grammar"),
    ("relative_clauses_who_which", "Relative clauses who/which", 8, "grammar"),
    ("reported_speech_basic", "Reported speech (basic)", 9, "grammar"),
    ("adverbs_frequency_manner", "Adverbs of frequency & manner", 2, "grammar"),
    ("connectors_because_so", "Connectors because/so/but", 2, "grammar"),
    ("vocab_travel_daily", "Vocab: travel & daily routines", 4, "vocabulary"),
    ("vocab_opinions_feelings", "Vocab: opinions & feelings", 5, "vocabulary"),
]
```

A1 edges `(from_slug, to_slug)` — minimal DAG (extend if needed, keep acyclic):

```python
A1_EDGES = [
    ("be_present", "possessives"),
    ("be_present", "there_is_are"),
    ("be_present", "past_simple_be"),
    ("subject_pronouns", "present_simple"),
    ("articles_a_an_the", "countable_uncountable_basic"),
    ("present_simple", "present_continuous"),
    ("present_simple", "can_cant"),
    ("present_simple", "wh_questions_basic"),
    ("present_simple", "past_simple_regular"),
    ("past_simple_be", "past_simple_regular"),
    ("past_simple_regular", "past_simple_irregular_common"),
    ("present_simple", "going_to_future"),
    ("countable_uncountable_basic", "some_any"),
]
```

A2 edges:

```python
A2_EDGES = [
    ("present_simple_vs_continuous", "past_continuous"),
    ("past_continuous", "past_simple_vs_continuous"),
    ("present_perfect_basic", "present_perfect_vs_past"),
    ("will_future", "going_to_vs_will"),
    ("modals_should_must", "modals_have_to"),
    ("first_conditional", "second_conditional_intro"),
    ("connectors_because_so", "relative_clauses_who_which"),
    ("present_perfect_basic", "used_to"),
]
```

- [ ] **Step 1: Write failing test**

```python
# backend/tests/test_cefr_ladder_seed.py
import pytest
from sqlalchemy import func, select

from app.models.enums import CEFRLevel
from app.models.learning_skill import LearningSkillDB, SkillEdgeDB
from app.seeds.cefr_ladder_a1_a2 import A1_SKILLS, A2_SKILLS, seed_cefr_ladder


@pytest.mark.asyncio
async def test_seed_cefr_ladder_idempotent(db_session):
    # db_session = project's AsyncSession fixture name — match existing tests
    r1 = await seed_cefr_ladder(db_session)
    await db_session.commit()
    r2 = await seed_cefr_ladder(db_session)
    await db_session.commit()

    assert r1["a1"] == len(A1_SKILLS)
    assert r1["a2"] == len(A2_SKILLS)
    assert r2["a1"] == len(A1_SKILLS)

    n_a1 = await db_session.scalar(
        select(func.count()).select_from(LearningSkillDB).where(
            LearningSkillDB.cefr_level == CEFRLevel.A1,
            LearningSkillDB.origin == "catalog",
            LearningSkillDB.is_active.is_(True),
        )
    )
    assert n_a1 == len(A1_SKILLS)
```

Adapt fixture name to whatever `test_roadmap_assembler_service.py` / `test_skill_graph_service.py` use. If tests are pure (no DB), extract pure `build_skill_rows()` and test list lengths + unique slugs instead; still add one integration test if DB fixtures exist.

- [ ] **Step 2: Run test — expect fail**

Run: `cd backend && .venv/bin/pytest tests/test_cefr_ladder_seed.py -v`  
Expected: FAIL (module missing)

- [ ] **Step 3: Implement seed module**

Follow `app/seeds/scenarios.py`: `AsyncSessionLocal`, `pg_insert(...).on_conflict_do_update` on `(slug, cefr_level)`, upsert edges with unique `(from_skill_id, to_skill_id)`, then deactivate non-catalog A1/A2 actives:

```python
await db.execute(
    update(LearningSkillDB)
    .where(
        LearningSkillDB.cefr_level.in_([CEFRLevel.A1, CEFRLevel.A2]),
        LearningSkillDB.origin != "catalog",
    )
    .values(is_active=False)
)
```

Also set `origin="catalog"` on upserted rows.

- [ ] **Step 4: Run test — expect pass**

Run: `cd backend && .venv/bin/pytest tests/test_cefr_ladder_seed.py -v`  
Expected: PASS

- [ ] **Step 5: Manual CLI smoke**

Run: `cd backend && .venv/bin/python -m app.seeds.cefr_ladder_a1_a2`  
Expected: prints counts for A1/A2/edges

- [ ] **Step 6: Commit**

```bash
git add backend/app/seeds/cefr_ladder_a1_a2.py backend/tests/test_cefr_ladder_seed.py
git commit -m "$(cat <<'EOF'
feat: seed curated CEFR A1+A2 skill ladder

EOF
)"
```

---

### Task 3: Attach-only LLM + validate (no invent slugs)

**Files:**
- Modify: `backend/app/services/skill_graph_llm_service.py`
- Modify: `backend/app/services/skill_graph_validate.py`
- Modify: `backend/tests/test_skill_graph_llm_service.py`
- Create or extend: `backend/tests/test_skill_graph_validate.py`

**Interfaces:**
- Change `refine_units_with_llm` to attach mode OR add `attach_units_with_llm(...)` used by sync
- Input: `catalog_skills: list[dict]` with `slug`, `title`, `difficulty_in_level`
- Output mappings: `unit_index`, `slug | None`, `exclude: bool` — **slug must be in catalog or null**
- **No** `prerequisites` in attach payload (ignore if model returns them)
- Produces: `validate_llm_attach_payload(payload, unit_indexes, catalog_slugs) -> list[dict]`

- [ ] **Step 1: Write failing tests**

```python
def test_validate_attach_rejects_unknown_slug():
    from app.services.skill_graph_validate import validate_llm_attach_payload

    with pytest.raises(ValueError):
        validate_llm_attach_payload(
            {
                "unit_mappings": [
                    {"unit_index": 1, "slug": "not_in_catalog", "exclude": False},
                ]
            },
            unit_indexes={1},
            catalog_slugs={"present_simple"},
        )


def test_validate_attach_allows_null_slug_unmapped():
    from app.services.skill_graph_validate import validate_llm_attach_payload

    out = validate_llm_attach_payload(
        {
            "unit_mappings": [
                {"unit_index": 1, "slug": None, "exclude": False},
                {"unit_index": 2, "slug": "present_simple", "exclude": False},
            ]
        },
        unit_indexes={1, 2},
        catalog_slugs={"present_simple"},
    )
    assert out[0]["slug"] is None
    assert out[1]["slug"] == "present_simple"
```

- [ ] **Step 2: Run — expect fail**

Run: `cd backend && .venv/bin/pytest tests/test_skill_graph_validate.py -k attach -v`  
Expected: FAIL

- [ ] **Step 3: Implement validate + LLM wrapper**

New system prompt (replace sync invent prompt for the attach path):

```text
You map ESL book units onto a FIXED catalog of skills for one CEFR level.
Return JSON only:
{"unit_mappings":[{"unit_index":int,"slug":str|null,"exclude":bool}]}
Rules:
- slug MUST be one of catalog_skills[].slug, or null if no good match
- exclude=true for review/test/index/answer key units (slug may be null)
- Do not invent slugs. Do not return prerequisites.
- Prefer the closest pedagogical match; one unit → at most one skill
```

`attach_units_with_llm(...)` calls `chat_json`, then `validate_llm_attach_payload`.

Keep old `refine_units_with_llm` only if tests still need it; otherwise delete/redirect to attach and update callers.

- [ ] **Step 4: Run tests — pass**

Run: `cd backend && .venv/bin/pytest tests/test_skill_graph_validate.py tests/test_skill_graph_llm_service.py -v`  
Expected: PASS (update old invent-style tests to attach semantics)

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/skill_graph_llm_service.py backend/app/services/skill_graph_validate.py backend/tests/test_skill_graph_validate.py backend/tests/test_skill_graph_llm_service.py
git commit -m "$(cat <<'EOF'
feat: LLM attach maps units only onto catalog slugs

EOF
)"
```

---

### Task 4: Rewrite `sync_skills_from_preview` to attach-only

**Files:**
- Modify: `backend/app/services/skill_graph_service.py`
- Modify: `backend/app/api/admin_quiz.py`
- Create: `backend/tests/test_skill_graph_attach.py`

**Interfaces:**
- `sync_skills_from_preview(db, book_id) -> tuple[list[BookSkillSourceDB], dict]`
- Meta dict MUST include:
  - `llm_used: bool`
  - `mapped_count: int`
  - `unmapped_units: list[{"unit_index": int, "unit_title": str}]`
  - `excluded_count: int`
  - `edge_count_added: 0` (always 0; keep key for API compat)
- Must **not** call skill create for unknown slugs
- Must **not** call `_union_prerequisite_edges` / linear edge builder from sync
- Must **not** overwrite catalog `difficulty_in_level`
- Rule fallback: `normalize_unit_to_slug(title)` → if slug in catalog use it; else unmapped; `should_exclude_unit` → excluded source skipped or stored excluded without skill — **chốt: excluded units create no source row OR source with is_excluded and skill_id of a sentinel — simpler: no row for exclude/unmapped; only create sources for mapped+not-excluded**

**Preferred source write rule (locked):**
- `exclude=true` → no `book_skill_sources` row; count in `excluded_count`
- `slug is None` → no row; append to `unmapped_units`
- mapped → upsert/create source to that catalog `skill_id`

Still `_clear_book_sources` for the book then recreate mapped rows (same as today replace semantics).

- [ ] **Step 1: Write failing test (pure + mocked)**

```python
import pytest
from unittest.mock import AsyncMock, patch

@pytest.mark.asyncio
async def test_attach_does_not_create_unknown_skills(db_session):
    # Arrange: seed catalog A1; create ready book with units including weird title
    # Act: patch attach_units_with_llm to return unknown slug for one unit AND
    #      a valid present_simple for another
    # Assert: LearningSkillDB count for A1 catalog unchanged;
    #         only valid mapping has a BookSkillSourceDB
    ...
```

Also unit-test a pure helper if extracted:

```python
def test_rule_attach_mapping_only_catalog():
    from app.services.skill_graph_service import build_rule_attach_mappings

    catalog = {"present_simple", "past_simple_regular"}
    units = [
        {"unit_index": 1, "title": "Present simple"},
        {"unit_index": 2, "title": "Totally Unique Chapter About Dragons"},
        {"unit_index": 3, "title": "Review Unit 1-3"},
    ]
    mappings = build_rule_attach_mappings(units, catalog_slugs=catalog)
    by_i = {m["unit_index"]: m for m in mappings}
    assert by_i[1]["slug"] == "present_simple"
    assert by_i[2]["slug"] is None
    assert by_i[3]["exclude"] is True
```

- [ ] **Step 2: Run — expect fail**

Run: `cd backend && .venv/bin/pytest tests/test_skill_graph_attach.py -v`  
Expected: FAIL

- [ ] **Step 3: Implement attach orchestration**

Refactor `sync_skills_from_preview`:

1. Load book+units (existing)
2. `catalog = await load_catalog_skills(db, book.cefr_level)` — `origin=="catalog"` and `is_active`
3. If catalog empty → `ValueError("No catalog skills for this CEFR level — run cefr ladder seed")`
4. Try `attach_units_with_llm(...); llm_used=True` except → `build_rule_attach_mappings`; `llm_used=False`
5. Clear sources; for each mapping with slug and not exclude: resolve skill id from catalog only; insert `BookSkillSourceDB`
6. Recompute primary
7. Commit; return meta with unmapped/excluded

Remove overwrite_difficulty path for attach.

- [ ] **Step 4: Update admin response**

In `admin_quiz.py` `admin_sync_skills` return:

```python
return {
    "data": {
        "book_id": book_id,
        "source_count": len(sources),
        "excluded": int(meta.get("excluded_count") or 0),
        "mapped_count": int(meta.get("mapped_count") or 0),
        "unmapped_units": meta.get("unmapped_units") or [],
        "llm_used": bool(meta.get("llm_used")),
        "edge_count_added": 0,
        "sources": [ ... same shape ... ],
    }
}
```

- [ ] **Step 5: Run tests**

Run: `cd backend && .venv/bin/pytest tests/test_skill_graph_attach.py tests/test_skill_graph_service.py -v`  
Expected: PASS (fix/delete obsolete create-skill tests)

- [ ] **Step 6: Commit**

```bash
git add backend/app/services/skill_graph_service.py backend/app/api/admin_quiz.py backend/tests/test_skill_graph_attach.py
git commit -m "$(cat <<'EOF'
feat: attach book units to catalog skills only

EOF
)"
```

---

### Task 5: Assemble coverage filter

**Files:**
- Modify: `backend/app/services/roadmap_assembler_service.py`
- Modify: `backend/tests/test_roadmap_assembler_service.py`

**Interfaces:**
- Change `load_active_skills` OR add `load_covered_active_skills(db, level)` used by `plan_next_steps`
- Covered = exists `BookSkillSourceDB` with `skill_id=skill.id` AND `is_excluded.is_(False)`
- Prefer also `LearningSkillDB.origin == "catalog"` for A1/A2 (legacy inactive already)

- [ ] **Step 1: Write failing test**

```python
def test_select_skills_only_from_provided_pool_still_works():
    # existing unit tests for select_skills_for_roadmap stay valid
    pass


@pytest.mark.asyncio
async def test_plan_next_steps_skips_skills_without_sources(db_session):
    # Create 2 catalog A1 skills; only skill A has a non-excluded source
    # mastery low for both; placement_score=1
    # plan_next_steps / load path should only be able to pick skill A
    ...
```

If DB-heavy, test a new pure filter:

```python
def test_filter_skills_with_coverage():
    from app.services.roadmap_assembler_service import filter_skills_with_coverage

    skills = [{"id": 1}, {"id": 2}, {"id": 3}]
    covered_ids = {1, 3}
    assert [s["id"] for s in filter_skills_with_coverage(skills, covered_ids)] == [1, 3]
```

Then wire `plan_next_steps` to load covered ids via SQL.

- [ ] **Step 2: Run — expect fail**

Run: `cd backend && .venv/bin/pytest tests/test_roadmap_assembler_service.py -k coverage -v`  
Expected: FAIL

- [ ] **Step 3: Implement**

```python
async def load_covered_skill_ids(db: AsyncSession, level: CEFRLevel) -> set[int]:
    result = await db.execute(
        select(BookSkillSourceDB.skill_id)
        .join(LearningSkillDB, LearningSkillDB.id == BookSkillSourceDB.skill_id)
        .where(
            LearningSkillDB.cefr_level == level,
            LearningSkillDB.is_active.is_(True),
            BookSkillSourceDB.is_excluded.is_(False),
        )
    )
    return {int(x) for x in result.scalars().all()}
```

In `plan_next_steps`, after `load_active_skills`, filter to ids in covered set before `select_skills_for_roadmap`.

- [ ] **Step 4: Run full assembler tests**

Run: `cd backend && .venv/bin/pytest tests/test_roadmap_assembler_service.py tests/test_roadmap_adaptive_service.py -v`  
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/roadmap_assembler_service.py backend/tests/test_roadmap_assembler_service.py
git commit -m "$(cat <<'EOF'
feat: assemble roadmap only from skills with book coverage

EOF
)"
```

---

### Task 6: Spec status + README seed note + smoke checklist

**Files:**
- Modify: `docs/superpowers/specs/2026-07-30-band-ladder-book-attach-design.md` (Status → Implemented when done)
- Modify: `backend/README.md` — add seed command next to scenarios

- [ ] **Step 1: Document runbook in backend README**

```markdown
### CEFR ladder catalog (A1+A2)

```bash
python -m app.seeds.cefr_ladder_a1_a2
```

Run before attaching books. Then admin `POST .../books/{id}/sync-skills` attaches units to catalog skills.
```

- [ ] **Step 2: Manual smoke checklist** (execute, don't just write)

1. `alembic upgrade head`
2. `python -m app.seeds.cefr_ladder_a1_a2`
3. Sync one ready A1 book → `mapped_count > 0`, skill count catalog unchanged
4. Assemble roadmap for A1 user → weeks only use covered skills
5. (If A2 book exists) sync A2; promote user; assemble A2 path

- [ ] **Step 3: Mark spec status Implemented** with date

- [ ] **Step 4: Commit**

```bash
git add backend/README.md docs/superpowers/specs/2026-07-30-band-ladder-book-attach-design.md
git commit -m "$(cat <<'EOF'
docs: band ladder seed runbook and spec status

EOF
)"
```

---

## Spec coverage check

| Spec requirement | Task |
|------------------|------|
| Migration `origin` | Task 1 |
| Seed A1+A2 + edges + deactivate legacy | Task 2 |
| Attach-only LLM/rule | Tasks 3–4 |
| No edge rewrite on sync | Task 4 |
| Sync response unmapped | Task 4 |
| Assemble coverage filter | Task 5 |
| CLI seed like scenarios | Task 2 |
| README / smoke | Task 6 |
| Admin CRUD / coverage UI | Out of scope (phase 2) |
| Frontend copy polish | Out of scope |
| B1–C1 seed | Out of scope |

---

## Out of scope (do not implement in this plan)

- Admin skill CRUD / coverage dashboard
- Human approve-before-attach
- `can_do` column (optional later)
- Exam-prep B1–C1 mode
- Renaming mastery rows across merged legacy skills (legacy deactivated; users re-earn on catalog ids)
