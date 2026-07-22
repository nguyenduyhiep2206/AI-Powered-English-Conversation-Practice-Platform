# Skill Graph ZPD Roadmap Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Khi sync sách, LLM (có fallback rule) gộp unit vào skill graph chung theo CEFR; khi assemble lộ trình, chọn skill theo ZPD + prerequisite + mastery; hoàn thành tuần khi mastery ≥ 0.7 và unlock tuần sau; user thấy level quá dễ có thể promote +1 CEFR qua challenge 6 câu.

**Architecture:** Hybrid sync (`skill_normalize` → `skill_graph_llm` → validate → upsert incremental). Assembler đổi sang filter ZPD trên `difficulty_in_level` + `skill_edges`. Progress service đánh dấu week `completed` / mở week kế. Level-challenge service lấy published quiz @ level đích, đậu thì cập nhật `current_level` + `placement_score` và clear roadmap. Không gọi LLM khi assemble / complete-week / challenge.

**Tech Stack:** FastAPI, SQLAlchemy async, Alembic, LangChain `chat_json` (`app.services.llm_client`), pytest.

**Spec:** `docs/superpowers/specs/2026-07-20-skill-graph-zpd-roadmap-design.md`

## Global Constraints

- LLM chỉ khi **sync skill graph** (1 batch / sách); không LLM trong assemble / complete-week / level-challenge
- Incremental merge — không xóa toàn bộ graph CEFR khi thêm sách
- `MASTERY_STRONG = 0.7`; path length 8–12; ZPD `window = 2`
- `placement_score` 0 → clamp thành 1; thiếu difficulty → treat as 5
- LLM fail → fallback rule-based sync hiện tại; sách vẫn sync được
- Giữ contract `POST /roadmap/assemble` (cùng URL); placement không auto-assemble
- Level promote: chỉ **+1** CEFR; challenge **6** câu published @ đích; đậu **≥ 4/6**; không free bump
- Commit message style: conventional (`feat:`, `test:`, `fix:`) — chỉ commit khi user/agent được phép trong session thực thi

---

## File map

| File | Responsibility |
|------|----------------|
| `backend/alembic/versions/i9j0k1l2m3n4_add_skill_difficulty_in_level.py` | Migration cột `difficulty_in_level` + backfill |
| `backend/app/models/learning_skill.py` | Thêm field ORM |
| `backend/app/services/skill_graph_difficulty.py` | Rule difficulty từ `unit_index`; median merge |
| `backend/app/services/skill_graph_llm_service.py` | Prompt + `chat_json` + parse/validate payload |
| `backend/app/services/skill_graph_service.py` | Orchestrate LLM path + fallback rule path |
| `backend/app/services/roadmap_assembler_service.py` | ZPD `select_skills_for_roadmap` |
| `backend/app/services/roadmap_progress_service.py` | Complete week + unlock next |
| `backend/app/services/level_challenge_service.py` | Challenge promote +1 CEFR |
| `backend/app/api/roadmap.py` | Endpoint complete week (+ giữ assemble) |
| `backend/app/api/onboarding.py` (or profile) | GET/POST level-challenge |
| `backend/app/api/admin_quiz.py` | Response sync thêm `llm_used` |
| `backend/tests/test_skill_graph_difficulty.py` | Unit difficulty helpers |
| `backend/tests/test_skill_graph_llm_service.py` | Validate LLM JSON / cycle |
| `backend/tests/test_roadmap_assembler_service.py` | ZPD + prereq tests |
| `backend/tests/test_roadmap_progress_service.py` | Pass / fail week |
| `backend/tests/test_level_challenge_service.py` | Pass / fail promote |

---

### Task 1: Migration + model `difficulty_in_level`

**Files:**
- Create: `backend/alembic/versions/i9j0k1l2m3n4_add_skill_difficulty_in_level.py`
- Modify: `backend/app/models/learning_skill.py`
- Test: verify model import + migration upgrade (manual/local)

**Interfaces:**
- Produces: `LearningSkillDB.difficulty_in_level: int | None` (SMALLINT, nullable until backfill sets values; service clamps 1–10)

- [ ] **Step 1: Add column on model**

In `LearningSkillDB`, after `skill_type`:

```python
from sqlalchemy import SmallInteger  # add to imports

difficulty_in_level = Column(SmallInteger, nullable=True)
```

- [ ] **Step 2: Write Alembic revision**

`down_revision` = latest head (check `cd backend && .venv/bin/alembic heads` — currently expect `h8i9j0k1l2m3` or whatever `alembic heads` prints; set correctly).

```python
"""add learning_skills.difficulty_in_level

Revision ID: i9j0k1l2m3n4
Revises: <HEAD>
"""
from alembic import op
import sqlalchemy as sa

revision = "i9j0k1l2m3n4"
down_revision = "<HEAD>"  # replace with actual head
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "learning_skills",
        sa.Column("difficulty_in_level", sa.SmallInteger(), nullable=True),
    )
    # Backfill from primary (or any) book_skill_sources unit_index via structure preview
    op.execute(
        """
        UPDATE learning_skills AS ls
        SET difficulty_in_level = sub.diff
        FROM (
            SELECT
                bss.skill_id,
                GREATEST(1, LEAST(10,
                    1 + ROUND(
                        9.0 * COALESCE(bsp.unit_index, 0)
                        / NULLIF(
                            (SELECT MAX(bsp2.unit_index)
                             FROM book_structure_preview bsp2
                             WHERE bsp2.book_id = bss.book_id),
                            0
                        )
                    )::int
                )) AS diff
            FROM book_skill_sources bss
            JOIN book_structure_preview bsp ON bsp.id = bss.unit_id
            WHERE bss.is_excluded = false
        ) AS sub
        WHERE ls.id = sub.skill_id
          AND ls.difficulty_in_level IS NULL
        """
    )
    op.execute(
        "UPDATE learning_skills SET difficulty_in_level = 5 WHERE difficulty_in_level IS NULL"
    )


def downgrade() -> None:
    op.drop_column("learning_skills", "difficulty_in_level")
```

If the SQL join is awkward on Postgres for multi-source skills, acceptable MVP alternative in `upgrade()`:

```python
op.execute("UPDATE learning_skills SET difficulty_in_level = 5 WHERE difficulty_in_level IS NULL")
```

…and rely on Task 2–4 recompute on next sync. Prefer the full backfill if it runs cleanly.

- [ ] **Step 3: Run migration**

```bash
cd backend && .venv/bin/alembic upgrade head
```

Expected: success, column exists.

- [ ] **Step 4: Commit** (when executing session allows)

```bash
git add backend/app/models/learning_skill.py backend/alembic/versions/i9j0k1l2m3n4_add_skill_difficulty_in_level.py
git commit -m "$(cat <<'EOF'
feat: add difficulty_in_level on learning_skills

EOF
)"
```

---

### Task 2: Pure helpers — difficulty + LLM payload validation

**Files:**
- Create: `backend/app/services/skill_graph_difficulty.py`
- Create: `backend/app/services/skill_graph_validate.py`
- Test: `backend/tests/test_skill_graph_difficulty.py`
- Test: `backend/tests/test_skill_graph_validate.py`

**Interfaces:**
- Produces:
  - `difficulty_from_unit_index(unit_index: int, n_units: int) -> int`  # 1..10
  - `median_difficulty(values: list[int]) -> int`
  - `validate_llm_graph_payload(payload: dict, *, unit_indexes: set[int], existing_slugs: set[str], allowed_skill_types: set[str]) -> tuple[list[dict], list[tuple[str, str]]]`  
    Returns `(unit_mappings, prereq_pairs)` after clamp/filter; raises `ValueError` if unusable (empty mappings / missing coverage). Soft-drops bad edges (self, unknown slug, cycle).

- [ ] **Step 1: Failing tests — difficulty**

```python
# backend/tests/test_skill_graph_difficulty.py
from app.services.skill_graph_difficulty import difficulty_from_unit_index, median_difficulty


def test_difficulty_dau_cuoi_sach():
    assert difficulty_from_unit_index(0, 10) == 1
    assert difficulty_from_unit_index(9, 10) == 10


def test_difficulty_mot_unit():
    assert difficulty_from_unit_index(0, 1) == 1


def test_median_difficulty():
    assert median_difficulty([2, 8, 5]) == 5
    assert median_difficulty([3, 4]) == 3  # lower median of even pair OK, or average-then-round — pick one and document
```

Pick even-median rule: `sorted[len//2 - 1]` for even (lower), document in docstring.

- [ ] **Step 2: Run — expect FAIL**

```bash
cd backend && .venv/bin/python -m pytest tests/test_skill_graph_difficulty.py -v
```

- [ ] **Step 3: Implement `skill_graph_difficulty.py`**

```python
"""Rule-based difficulty_in_level (1–10) helpers."""

from __future__ import annotations


def difficulty_from_unit_index(unit_index: int, n_units: int) -> int:
    if n_units <= 1:
        return 1
    idx = max(0, min(int(unit_index), n_units - 1))
    raw = 1 + round(9 * idx / (n_units - 1))
    return max(1, min(10, int(raw)))


def median_difficulty(values: list[int]) -> int:
    if not values:
        return 5
    xs = sorted(max(1, min(10, int(v))) for v in values)
    return xs[(len(xs) - 1) // 2]
```

- [ ] **Step 4: Failing tests — validate**

```python
# backend/tests/test_skill_graph_validate.py
from app.services.skill_graph_validate import validate_llm_graph_payload


def test_validate_maps_and_keeps_valid_edge():
    payload = {
        "unit_mappings": [
            {
                "unit_index": 0,
                "slug": "be_present",
                "title": "Be present",
                "skill_type": "grammar",
                "difficulty_in_level": 2,
                "exclude": False,
            },
            {
                "unit_index": 1,
                "slug": "present_simple",
                "title": "Present simple",
                "skill_type": "grammar",
                "difficulty_in_level": 5,
                "exclude": False,
            },
        ],
        "prerequisites": [
            {"from_slug": "be_present", "to_slug": "present_simple"},
            {"from_slug": "present_simple", "to_slug": "present_simple"},  # self — drop
        ],
    }
    mappings, edges = validate_llm_graph_payload(
        payload,
        unit_indexes={0, 1},
        existing_slugs=set(),
        allowed_skill_types={"grammar", "vocabulary", "reading", "functional"},
    )
    assert len(mappings) == 2
    assert edges == [("be_present", "present_simple")]


def test_validate_drops_cycle_edge():
    payload = {
        "unit_mappings": [
            {"unit_index": 0, "slug": "a", "title": "A", "skill_type": "grammar", "difficulty_in_level": 1, "exclude": False},
            {"unit_index": 1, "slug": "b", "title": "B", "skill_type": "grammar", "difficulty_in_level": 2, "exclude": False},
        ],
        "prerequisites": [
            {"from_slug": "a", "to_slug": "b"},
            {"from_slug": "b", "to_slug": "a"},
        ],
    }
    _mappings, edges = validate_llm_graph_payload(
        payload,
        unit_indexes={0, 1},
        existing_slugs=set(),
        allowed_skill_types={"grammar", "vocabulary", "reading", "functional"},
    )
    # Keep a linear order: first edge OK, second dropped as cycle
    assert edges == [("a", "b")]


def test_validate_rejects_missing_unit_coverage():
    import pytest

    payload = {"unit_mappings": [], "prerequisites": []}
    with pytest.raises(ValueError):
        validate_llm_graph_payload(
            payload,
            unit_indexes={0},
            existing_slugs=set(),
            allowed_skill_types={"grammar"},
        )
```

- [ ] **Step 5: Implement `skill_graph_validate.py`**

Requirements:
- Slug regex `^[a-z0-9_]{2,120}$`
- Clamp difficulty 1–10
- `skill_type` ∈ allowed
- Every `unit_index` in `unit_indexes` appears exactly once in accepted mappings (or raise)
- Prereq endpoints ∈ mapping slugs ∪ `existing_slugs`
- Drop self-edges
- Add edges one-by-one; if edge creates cycle in directed graph of accepted edges, skip that edge
- Normalize slug to lowercase

- [ ] **Step 6: Run tests**

```bash
cd backend && .venv/bin/python -m pytest tests/test_skill_graph_difficulty.py tests/test_skill_graph_validate.py -v
```

Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add backend/app/services/skill_graph_difficulty.py backend/app/services/skill_graph_validate.py \
  backend/tests/test_skill_graph_difficulty.py backend/tests/test_skill_graph_validate.py
git commit -m "$(cat <<'EOF'
feat: add skill graph difficulty and LLM payload validation

EOF
)"
```

---

### Task 3: `skill_graph_llm_service` (call + parse)

**Files:**
- Create: `backend/app/services/skill_graph_llm_service.py`
- Test: `backend/tests/test_skill_graph_llm_service.py` (mock `chat_json`)

**Interfaces:**
- Consumes: `chat_json`, `validate_llm_graph_payload`
- Produces:
  - `async` not required if sync like other services — match `chat_json` sync style:
  - `refine_units_with_llm(*, cefr_level: str, book_title: str, existing_skills: list[dict], units: list[dict]) -> tuple[list[dict], list[tuple[str, str]]]`
  - On any error: raise (caller falls back)

`units` items: `{unit_index, title, rule_slug}`  
`existing_skills` items: `{slug, title, difficulty_in_level}`

- [ ] **Step 1: Failing test with mock**

```python
from unittest.mock import patch
from app.services.skill_graph_llm_service import refine_units_with_llm


def test_refine_units_with_llm_happy_path():
    fake = {
        "unit_mappings": [
            {
                "unit_index": 0,
                "slug": "be_present",
                "title": "Be",
                "skill_type": "grammar",
                "difficulty_in_level": 2,
                "exclude": False,
            }
        ],
        "prerequisites": [],
    }
    with patch("app.services.skill_graph_llm_service.chat_json", return_value=fake):
        mappings, edges = refine_units_with_llm(
            cefr_level="A1",
            book_title="Book",
            existing_skills=[],
            units=[{"unit_index": 0, "title": "Hello", "rule_slug": "hello"}],
        )
    assert mappings[0]["slug"] == "be_present"
    assert edges == []
```

- [ ] **Step 2: Implement service**

```python
"""LLM refine for skill graph sync (one batch call per book)."""

from __future__ import annotations

import json
from typing import Any

from app.models.enums import SkillTypeEnum
from app.services.llm_client import chat_json
from app.services.skill_graph_validate import validate_llm_graph_payload

SYSTEM_PROMPT = """You are an ESL curriculum graph assistant.
Map book units to canonical learning skills for ONE CEFR level.
Prefer reusing existing_skills slugs when the unit teaches the same skill.
Return JSON only:
{
  "unit_mappings":[
    {"unit_index":int,"slug":str,"title":str,"skill_type":"grammar|vocabulary|reading|functional",
     "difficulty_in_level":1-10,"exclude":bool}
  ],
  "prerequisites":[{"from_slug":str,"to_slug":str}]
}
Rules:
- One mapping per unit_index; slug snake_case [a-z0-9_]{2,120}
- difficulty_in_level: 1=start of level, 10=end of level
- exclude=true for answer keys / index / non-teaching units
- prerequisites: from must be learned before to; only use slugs in mappings or existing_skills
- Do not invent CEFR levels; stay within the given level's skills
"""


def refine_units_with_llm(
    *,
    cefr_level: str,
    book_title: str,
    existing_skills: list[dict[str, Any]],
    units: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[tuple[str, str]]]:
    user = json.dumps(
        {
            "cefr_level": cefr_level,
            "book_title": book_title,
            "existing_skills": existing_skills,
            "units": units,
        },
        ensure_ascii=False,
    )
    payload = chat_json(SYSTEM_PROMPT, user)
    if not isinstance(payload, dict):
        raise ValueError("LLM skill graph response must be an object")
    allowed = {e.value for e in SkillTypeEnum}
    return validate_llm_graph_payload(
        payload,
        unit_indexes={int(u["unit_index"]) for u in units},
        existing_slugs={str(s["slug"]) for s in existing_skills},
        allowed_skill_types=allowed,
    )
```

- [ ] **Step 3: Run test**

```bash
cd backend && .venv/bin/python -m pytest tests/test_skill_graph_llm_service.py -v
```

- [ ] **Step 4: Commit**

```bash
git add backend/app/services/skill_graph_llm_service.py backend/tests/test_skill_graph_llm_service.py
git commit -m "$(cat <<'EOF'
feat: add LLM refine service for skill graph sync

EOF
)"
```

---

### Task 4: Wire LLM into `sync_skills_from_preview` (fallback rule)

**Files:**
- Modify: `backend/app/services/skill_graph_service.py`
- Modify: `backend/app/api/admin_quiz.py` (return `llm_used`)
- Test: `backend/tests/test_skill_graph_service.py` — add pure helper tests if you extract `_apply_llm_or_rule`; optional mock integration test

**Interfaces:**
- Consumes: `refine_units_with_llm`, `difficulty_from_unit_index`, `median_difficulty`
- Produces: `sync_skills_from_preview` still returns `list[BookSkillSourceDB]`; set module-level or return tuple — **prefer** changing return to:

```python
async def sync_skills_from_preview(
    db: AsyncSession, book_id: int
) -> tuple[list[BookSkillSourceDB], dict[str, Any]]:
    # meta: {"llm_used": bool, "edge_count_added": int}
```

Update `admin_quiz.admin_sync_skills` to unpack and include `llm_used` in JSON.

**Behavior:**

1. Load book + units (existing).
2. Build `units` with `rule_slug` via `normalize_unit_to_slug`.
3. Load `existing_skills` same `cefr_level` (slug, title, difficulty_in_level) — cap 200 rows ordered by id if huge.
4. Try `refine_units_with_llm(...)`; on success `llm_used=True` and use mappings/edges.
5. On failure: log exception; build mappings from rule slugs + `should_exclude_unit`; edges from `build_linear_edges` on skill ids after create; `llm_used=False`.
6. For each mapping: `_get_or_create_skill` with slug/title/type; set `difficulty_in_level` from mapping (or rule difficulty); create `BookSkillSourceDB`.
7. Recompute `is_primary` (existing).
8. Union prerequisite edges by resolving slugs → ids; skip duplicates; no delete of other books' edges.
9. For each affected skill, optionally recompute difficulty as `median_difficulty` of suggestions from all non-excluded sources' unit positions + latest LLM values stored on skill (MVP: set from this sync's mapping when LLM used; else rule from this book's unit_index only if skill.difficulty is null).

Keep excluded units creating sources with `is_excluded=True` (current behavior).

- [ ] **Step 1: Update sync signature + admin response**

Admin response add:

```python
"llm_used": meta["llm_used"],
```

- [ ] **Step 2: Implement LLM-first branch with try/except around `refine_units_with_llm`**

Use `logging.getLogger(__name__).exception(...)` on fallback.

- [ ] **Step 3: Manual smoke (optional)** — sync one ready book in local env.

- [ ] **Step 4: Run related tests**

```bash
cd backend && .venv/bin/python -m pytest tests/test_skill_graph_service.py tests/test_skill_graph_llm_service.py -v
```

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/skill_graph_service.py backend/app/api/admin_quiz.py backend/tests/test_skill_graph_service.py
git commit -m "$(cat <<'EOF'
feat: merge LLM refine into skill graph sync with rule fallback

EOF
)"
```

---

### Task 5: ZPD `select_skills_for_roadmap`

**Files:**
- Modify: `backend/app/services/roadmap_assembler_service.py`
- Modify: `backend/tests/test_roadmap_assembler_service.py`

**Interfaces:**
- Change signature to:

```python
def select_skills_for_roadmap(
    skills: list[dict[str, Any]] | list[LearningSkillDB],
    mastery: dict[int, float],
    *,
    placement_score: int | None,
    prereq_from_by_to: dict[int, list[int]],
    max_steps: int = 10,
    weak_point: WeakPointEnum | str | None = None,
    window: int = 2,
) -> list[dict[str, Any]]:
```

- `prereq_from_by_to[to_id] = [from_id, ...]` meaning from must be mastered before to
- `assemble_user_roadmap` loads edges:

```python
edges = (await db.execute(
    select(SkillEdgeDB).where(SkillEdgeDB.relation == "prerequisite")
)).scalars().all()
prereq_from_by_to: dict[int, list[int]] = defaultdict(list)
for e in edges:
    prereq_from_by_to[int(e.to_skill_id)].append(int(e.from_skill_id))
```

Only edges whose both ends are in the loaded level skill id set need to matter (filter optional).

**Algorithm:** as spec §9 (expand `hi` if too few candidates).

Include `difficulty_in_level` on `_skill_as_dict` (default 5 if None).

- [ ] **Step 1: Rewrite failing tests**

```python
from app.services.roadmap_assembler_service import select_skills_for_roadmap


def _skill(id, slug, diff, stype="grammar"):
    return {
        "id": id,
        "slug": slug,
        "title": slug,
        "cefr_level": "A1",
        "skill_type": stype,
        "is_active": True,
        "difficulty_in_level": diff,
    }


def test_zpd_score_3_khong_lay_diff_9():
    skills = [
        _skill(1, "be", 2),
        _skill(2, "poss", 3),
        _skill(3, "ps", 5),
        _skill(4, "past", 9),
    ]
    selected = select_skills_for_roadmap(
        skills,
        mastery={1: 0.75, 2: 0.2, 3: 0.2, 4: 0.2},
        placement_score=3,
        prereq_from_by_to={2: [1], 3: [1], 4: [3]},
        max_steps=10,
    )
    ids = [s["id"] for s in selected]
    assert 4 not in ids
    assert 2 in ids


def test_prereq_chua_dat_thi_bo():
    skills = [_skill(1, "be", 2), _skill(2, "ps", 4)]
    selected = select_skills_for_roadmap(
        skills,
        mastery={1: 0.2, 2: 0.2},
        placement_score=3,
        prereq_from_by_to={2: [1]},
        max_steps=10,
    )
    assert [s["id"] for s in selected] == [] or all(s["id"] != 2 for s in selected)
    # With expand window, be (diff 2) may enter when hi expands; ps must not while be weak
    assert 2 not in [s["id"] for s in selected]


def test_max_steps_van_ton_trong():
    skills = [_skill(i, f"s{i}", 4) for i in range(1, 40)]
    selected = select_skills_for_roadmap(
        skills,
        mastery={i: 0.1 for i in range(1, 40)},
        placement_score=3,
        prereq_from_by_to={},
        max_steps=12,
    )
    assert len(selected) == 12
```

Remove/update old tests that called the old signature.

- [ ] **Step 2: Implement ZPD selection + wire `assemble_user_roadmap`**

Pass `profile.placement_score` into selector.

- [ ] **Step 3: Run tests**

```bash
cd backend && .venv/bin/python -m pytest tests/test_roadmap_assembler_service.py -v
```

- [ ] **Step 4: Commit**

```bash
git add backend/app/services/roadmap_assembler_service.py backend/tests/test_roadmap_assembler_service.py
git commit -m "$(cat <<'EOF'
feat: assemble roadmap skills via ZPD and prerequisites

EOF
)"
```

---

### Task 6: Complete week + unlock next (mastery gate)

**Files:**
- Create: `backend/app/services/roadmap_progress_service.py`
- Modify: `backend/app/api/roadmap.py`
- Test: `backend/tests/test_roadmap_progress_service.py`

**Interfaces:**
- Produces:

```python
async def complete_roadmap_week(
    db: AsyncSession,
    user_id: int,
    roadmap_step_id: int,
) -> dict[str, Any]:
    """
    Pass if mastery of the step's quiz skill >= MASTERY_STRONG.
    Mark step completed; unlock next week_number for same user roadmap.
    Raise ValueError/PermissionError with clear messages.
    """
```

Logic:
1. Load `UserProgressDB` for (user, step); must be `in_progress`.
2. Load `RoadmapStepSkillDB` role=`quiz` → `skill_id`.
3. Load mastery; if `< MASTERY_STRONG` → raise `ValueError("Chưa đạt mastery 0.7 cho skill của tuần này")`.
4. Set progress `completed`, `completed_at=now()`.
5. Find next step: same user progresses join steps where `week_number = current+1` (or parse unlock_condition); set that progress from `locked` → `in_progress`.
6. Return `{step_id, status, unlocked_step_id?, mastery}`.

API:

```python
@router.post("/steps/{roadmap_step_id}/complete")
async def complete_step(...):
```

- [ ] **Step 1: Unit-test pure decision helper if extracted**

```python
def can_pass_week(mastery: float, threshold: float = MASTERY_STRONG) -> bool:
    return mastery >= threshold
```

Or full service tests with mocks — prefer testing `can_pass_week` + integration-style with in-memory if project lacks DB fixtures; follow existing test style (pure unit first).

```python
# backend/tests/test_roadmap_progress_service.py
from app.services.mastery_service import MASTERY_STRONG
from app.services.roadmap_progress_service import can_pass_week


def test_pass_khi_mastery_du():
    assert can_pass_week(0.7) is True
    assert can_pass_week(0.69) is False
```

- [ ] **Step 2: Implement service + endpoint**

- [ ] **Step 3: Run tests**

```bash
cd backend && .venv/bin/python -m pytest tests/test_roadmap_progress_service.py tests/test_roadmap_assembler_service.py -v
```

- [ ] **Step 4: Commit**

```bash
git add backend/app/services/roadmap_progress_service.py backend/app/api/roadmap.py backend/tests/test_roadmap_progress_service.py
git commit -m "$(cat <<'EOF'
feat: complete roadmap week when skill mastery passes gate

EOF
)"
```

---

### Task 7: Level challenge — promote +1 CEFR

**Files:**
- Create: `backend/app/services/level_challenge_service.py`
- Modify: `backend/app/api/onboarding.py` (prefer — cùng cụm placement) **hoặc** `backend/app/api/roadmap.py` nếu onboarding router chật; chọn một và giữ path ổn định
- Test: `backend/tests/test_level_challenge_service.py`
- Reuse: `_clear_user_roadmap` từ `roadmap_assembler_service` (export nếu đang private)

**Interfaces:**
- Consumes: `QuizQuestionDB` published + `LearningSkillDB.cefr_level`, `grade_placement_answer` / `grade_mcq`, `CEFR_ORDER`
- Produces:

```python
CHALLENGE_SIZE = 6
CHALLENGE_PASS = 4  # >= 4/6

def next_cefr_level(current: CEFRLevel) -> CEFRLevel | None:
    """A1→A2…; C1 → None."""

def challenge_score_to_placement(correct: int, total: int = CHALLENGE_SIZE) -> int:
    """max(1, min(10, round(correct/total*10)))."""

async def get_level_challenge_questions(
    db: AsyncSession, user_id: int, target_level: CEFRLevel | None = None
) -> list[dict]:
    """target default = next(current_level). Sample 6 published @ target. Public dicts no answers."""

async def submit_level_challenge(
    db: AsyncSession, user_id: int, target_level: CEFRLevel, answers: list[dict]
) -> dict:
    """
    Grade; if correct >= 4:
      profile.current_level = target
      profile.placement_score = challenge_score_to_placement(correct)
      await _clear_user_roadmap(...)
      return {passed: True, current_level, placement_score, correct_count, total}
    else:
      return {passed: False, current_level: unchanged, ...}
    """
```

Rules:
- `target_level` must equal `next_cefr_level(profile.current_level)` (MVP: không nhảy có chọn xa)
- User must have completed placement (`placement_score is not None`)
- Insufficient bank → `ValueError` message rõ (cần ≥6 published @ target)
- Optional: apply_answer mastery trên skill câu challenge — **có** (giống placement) để seed mastery level mới
- Không đổi công thức placement onboarding gốc

- [x] **Step 1: Failing unit tests**

```python
# backend/tests/test_level_challenge_service.py
from app.models.enums import CEFRLevel
from app.services.level_challenge_service import (
    challenge_score_to_placement,
    next_cefr_level,
)


def test_next_cefr():
    assert next_cefr_level(CEFRLevel.A1) == CEFRLevel.A2
    assert next_cefr_level(CEFRLevel.C1) is None


def test_challenge_score_to_placement():
    assert challenge_score_to_placement(4, 6) >= 1
    assert challenge_score_to_placement(6, 6) == 10
    assert challenge_score_to_placement(0, 6) == 1
```

- [x] **Step 2: Implement service + routes**

```text
GET  /api/v1/onboarding/level-challenge?target_level=A2
POST /api/v1/onboarding/level-challenge
Body: { "target_level": "A2", "answers": [{"question_id": 1, "answer": "..."}, ...] }
```

HTTP: 400 sai target / thiếu bank / thiếu answers; 403 chưa placement; 200 luôn khi grade xong (kể cả fail) với `passed`.

- [x] **Step 3: Run tests**

```bash
cd backend && .venv/bin/python -m pytest tests/test_level_challenge_service.py -v
```

- [ ] **Step 4: Commit**

```bash
git add backend/app/services/level_challenge_service.py backend/app/api/onboarding.py \
  backend/tests/test_level_challenge_service.py backend/app/services/roadmap_assembler_service.py
git commit -m "$(cat <<'EOF'
feat: CEFR +1 level challenge when current level feels too easy

EOF
)"
```

---

### Task 8: Spec status + smoke checklist

**Files:**
- Modify: `docs/superpowers/specs/2026-07-20-skill-graph-zpd-roadmap-design.md` — status note when implementation done
- No new product FE required for MVP (API-only complete week + challenge)

- [x] **Step 1: Run full related suite**

```bash
cd backend && .venv/bin/python -m pytest \
  tests/test_skill_graph_difficulty.py \
  tests/test_skill_graph_validate.py \
  tests/test_skill_graph_llm_service.py \
  tests/test_skill_graph_service.py \
  tests/test_roadmap_assembler_service.py \
  tests/test_roadmap_progress_service.py \
  tests/test_level_challenge_service.py \
  -v
```

Expected: all PASS — **25 passed** (2026-07-20)

- [x] **Step 2: Manual checklist** (unit smoke mapped; live E2E còn optional)

1. Migration applied — migration `i9j0k1l2m3n4` is head; apply on deploy (`alembic upgrade head`)
2. Sync sách A1 → response có `llm_used` (true nếu có key) — code path Task 4; verify trên env có API key
3. User placement_score=3 → assemble → không thấy skill diff 9 nếu graph đủ — covered by `test_zpd_score_3_khong_lay_diff_9`
4. Quiz đúng đến mastery ≥ 0.7 → `POST .../complete` → week 2 `in_progress` — `can_pass_week` + API Task 6; live unlock optional
5. Complete khi mastery thấp → 400 — `test_pass_khi_mastery_du` (0.69 → False) + API raises
6. Challenge A2: 4/6 → `current_level=A2`, roadmap cleared; 3/6 → vẫn A1 — unit helpers + service; live optional

- [x] **Step 3: Update spec status line when feature shipped**

- [ ] **Step 4: Final commit if docs changed** — chờ user yêu cầu commit (cùng đợt Tasks 2–7 uncommitted)

---

## Self-review (plan vs spec)

| Spec requirement | Task |
|------------------|------|
| `difficulty_in_level` + backfill | Task 1–2 |
| LLM map/merge/prereq/difficulty at sync | Task 3–4 |
| Rule fallback when LLM fails | Task 4 |
| Incremental union edges | Task 4 |
| ZPD assemble + expand window | Task 5 |
| No LLM on assemble | Task 5 (constraint) |
| Complete week → unlock (flow §5.2) | Task 6 |
| Level challenge promote +1 (§4.7 / §5.3) | Task 7 |
| Admin `llm_used` | Task 4 |
| Tests listed in spec §12 | Tasks 2–7 |

**Out of plan (spec non-goals / defer):** Neo4j, BKT, admin edge UI, auto re-assemble, FE difficulty badges, free level bump, multi-skip CEFR, full placement retake.

**Placeholder scan:** none intentional; replace `<HEAD>` in Task 1 with real alembic head at execute time.

---

## Execution handoff

Plan saved to `docs/superpowers/plans/2026-07-20-skill-graph-zpd-roadmap.md`.

**Two execution options:**

1. **Subagent-Driven (recommended)** — fresh subagent per task, review between tasks  
2. **Inline Execution** — execute tasks in this session with checkpoints  

Which approach?
