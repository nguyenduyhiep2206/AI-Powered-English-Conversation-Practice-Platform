# Plan triển khai: Theme Unit path + Lesson densify (Phương án D)

> **Cho agent:** REQUIRED SUB-SKILL: Dùng `superpowers:subagent-driven-development` (khuyến nghị) hoặc `superpowers:executing-plans` để làm từng task. Các bước dùng checkbox (`- [x]`) để theo dõi.

**Mục tiêu:** Làm roadmap/lesson giống product hơn bằng LessonPack (3 micro-lesson/skill) + Theme Unit (can-do) trên UI, **không** bỏ sách attach + skill graph + ZPD assemble.

**Kiến trúc:** Thêm `pack_index` trên `skill_lessons` để chuỗi Learn; learner đi L1→L3 rồi Practice. Seed `learning_theme_units` + join; DTO roadmap thêm metadata unit; FE gom section theo unit. Assembler vẫn chọn skill.

**Tech stack:** FastAPI, SQLAlchemy async, Alembic, `chat_json`, Next.js, pytest.

**Spec:** `docs/superpowers/specs/2026-08-03-theme-unit-path-densified-lessons-design.md`

> **Note (commits):** Task 1 migration/model + Task 4 union surfaces landed in `5f38053`; Task 3 gen helpers in `4a6530d`; Task 5 Learn micro-steps/pack FE types in `f9dfb96`. Remaining tasks committed on this branch per task.

## Ràng buộc toàn cục

- Core giữ: catalog attach-only, ZPD assemble, mastery ≥ 0.7, level-challenge nâng band
- Copy lesson/quiz English→English
- MVP densify: đúng **3** micro-lesson (`pack_index` 0,1,2) + Practice checkpoint
- Legacy: skill chỉ có `pack_index=0` published vẫn hoạt động
- Mỗi skill catalog thuộc **đúng một** Theme Unit (MVP)
- Assembler **không** đổi sang chọn Unit; chỉ thêm DTO/gom UI
- Không listening/speaking/streak/XP trong plan này
- Review hub = Task cuối (phase 4), nhẹ — không SRS đầy đủ
- Commit conventional (`feat:`, `test:`, `fix:`) — chỉ khi session được phép commit
- Alembic: kiểm tra `alembic heads` trước khi viết migration (hiện có thể là `p5q6r7s8t9u0`; revision mới ví dụ `q6r7s8t9u0v1` / `r7s8t9u0v1w2`)

---

## Bản đồ file

| File | Trách nhiệm |
|------|-------------|
| `backend/alembic/versions/q6r7s8t9u0v1_skill_lesson_pack_index.py` | Thêm `pack_index`; đổi unique `(skill_id, pack_index)` |
| `backend/alembic/versions/r7s8t9u0v1w2_learning_theme_units.py` | Bảng theme unit + join |
| `backend/app/models/skill_lesson.py` | ORM `pack_index` |
| `backend/app/models/theme_unit.py` | ORM Theme Unit + join |
| `backend/app/models/__init__.py` | Export model mới |
| `backend/app/services/lesson_service.py` | List pack published; complete theo index; `can_skip` pack |
| `backend/app/services/lesson_generation_service.py` | Gen LessonPack L1–L3 |
| `backend/app/services/lesson_content_validate.py` | Validate từng micro-lesson (giữ luật hiện có) |
| `backend/app/api/skills.py` / `admin_lessons.py` | API pack (get/complete/gen/publish) |
| `backend/app/services/quiz_generation_service.py` | Targets = union surfaces mọi lesson pack published |
| `backend/app/services/roadmap_assembler_service.py` | Gắn metadata theme unit vào week dict |
| `backend/app/seeds/theme_units_a1_a2.py` | Seed Unit + membership phủ hết catalog |
| `backend/tests/test_lesson_pack.py` | Pack index / complete / legacy |
| `backend/tests/test_theme_unit_seed.py` | Seed idempotent + không orphan |
| `backend/tests/test_roadmap_theme_unit_dto.py` | DTO có field unit |
| `frontend/my-app/lib/lesson.ts` | Types pack |
| `frontend/my-app/lib/roadmap.ts` | Types theme unit trên week |
| `frontend/my-app/components/lesson/LessonMiniUnit.tsx` (hoặc wrapper) | Chuỗi Learn 1/3→3/3 |
| `frontend/my-app/components/roadmap/WeekNode.tsx` + dashboard | Gom section theo Theme Unit; copy foundation |

---

### Task 1: Migration + model `pack_index`

**Files:**
- Tạo: `backend/alembic/versions/q6r7s8t9u0v1_skill_lesson_pack_index.py` (revision id chỉnh theo `alembic heads`)
- Modify: `backend/app/models/skill_lesson.py`
- Test: `backend/tests/test_lesson_pack_model.py`

**Interfaces:**
- Sinh ra: `SkillLessonDB.pack_index: int` (default 0); unique `(skill_id, pack_index)`; bỏ unique chỉ `skill_id`

- [x] **Bước 1: Cập nhật model**

Trong `SkillLessonDB`:

```python
__table_args__ = (
    UniqueConstraint("skill_id", "pack_index", name="uq_skill_lessons_skill_pack"),
)

pack_index = Column(Integer, nullable=False, server_default="0")
```

Import `Integer` từ sqlalchemy.

- [x] **Bước 2: Viết migration**

- Drop constraint `uq_skill_lessons_skill_id`
- Add column `pack_index` Integer NOT NULL server_default `0`
- Create unique `uq_skill_lessons_skill_pack` trên `(skill_id, pack_index)`
- `down_revision` = head hiện tại

- [x] **Bước 3: Test import model**

```python
# backend/tests/test_lesson_pack_model.py
from app.models.skill_lesson import SkillLessonDB

def test_pack_index_column_exists():
    assert hasattr(SkillLessonDB, "pack_index")
```

- [x] **Bước 4: Chạy test**

Run: `cd backend && pytest tests/test_lesson_pack_model.py -v`  
Expected: PASS

- [x] **Bước 5: Commit** (nếu được phép)

```bash
git add backend/app/models/skill_lesson.py backend/alembic/versions/q6r7s8t9u0v1_skill_lesson_pack_index.py backend/tests/test_lesson_pack_model.py
git commit -m "$(cat <<'EOF'
feat: add skill_lessons.pack_index for LessonPack

EOF
)"
```

---

### Task 2: Service LessonPack (đọc / complete / legacy)

**Files:**
- Modify: `backend/app/services/lesson_service.py`
- Modify: `backend/app/services/lesson_generation_service.py` (`lesson_to_dict` thêm `pack_index`)
- Test: `backend/tests/test_lesson_pack.py`
- Modify: `backend/app/api/skills.py` nếu response shape đổi

**Interfaces:**
- Sinh ra:
  - `async def list_published_pack(db, skill_id) -> list[SkillLessonDB]` — order by `pack_index`
  - `async def get_lesson_for_user(...)` trả thêm `pack: list[dict]`, `pack_completed_count`, `pack_total`, `lesson` = bài đang học / đầu tiên chưa complete (hoặc toàn pack)
  - `async def complete_lesson_pack_index(db, user_id, skill_id, pack_index: int) -> dict`
- Tiến độ: mở rộng `user_lesson_progress` **hoặc** (MVP đơn giản hơn) coi “pack xong” khi user complete lần cuối `pack_index == max` và đã xem đủ — **chốt MVP:** thêm cột JSON/int `highest_pack_index_completed` trên progress **hoặc** bảng progress theo `(user_id, skill_id, pack_index)`.

**Chốt persistence progress (MVP):** thêm bảng `user_lesson_pack_progress` với unique `(user_id, skill_id, pack_index)` + `completed_at`. `lesson_completed` (pack) = True khi mọi index published đều có progress row. Migration nhỏ gộp vào Task 1 hoặc migration phụ `q6r7..._b` nếu tách.

- [x] **Bước 1: Viết test fail**

```python
# backend/tests/test_lesson_pack.py
from app.services.lesson_service import compute_pack_completed, compute_can_skip

def test_pack_completed_when_all_indices_done():
    assert compute_pack_completed(published_indices=[0, 1, 2], completed_indices={0, 1, 2}) is True

def test_pack_not_completed_partial():
    assert compute_pack_completed(published_indices=[0, 1, 2], completed_indices={0, 1}) is False

def test_legacy_single_lesson_pack_total_one():
    assert compute_pack_completed(published_indices=[0], completed_indices={0}) is True
```

- [x] **Bước 2: Chạy test — expect FAIL**

Run: `cd backend && pytest tests/test_lesson_pack.py -v`  
Expected: FAIL (hàm chưa có)

- [x] **Bước 3: Implement pure helpers + service**

```python
def compute_pack_completed(*, published_indices: list[int], completed_indices: set[int]) -> bool:
    if not published_indices:
        return False
    return set(published_indices).issubset(completed_indices)
```

Cập nhật `get_lesson_for_user` trả:

```python
{
  "learn_available": ...,
  "can_skip": ...,
  "lesson_completed": pack_done,  # cả pack
  "pack_total": len(published),
  "pack_completed_count": len(completed ∩ published),
  "pack": [lesson_to_dict(x) for x in published],
  "lesson": lesson_to_dict(current) if current else None,  # bài tiếp theo hoặc None nếu xong
  "mastery": mastery,
}
```

`complete_lesson`: nhận optional `pack_index` (default 0); ghi progress index đó; nếu legacy chỉ gọi complete index 0.

- [x] **Bước 4: Chạy test — expect PASS**

Run: `cd backend && pytest tests/test_lesson_pack.py tests/test_lesson_service.py -v`

- [x] **Bước 5: Commit**

```bash
git commit -m "$(cat <<'EOF'
feat: serve LessonPack progress by pack_index

EOF
)"
```

---

### Task 3: Admin gen + publish LessonPack

**Files:**
- Modify: `backend/app/services/lesson_generation_service.py`
- Modify: `backend/app/api/admin_lessons.py` (và/hoặc `admin_skills.py` workspace)
- Test: `backend/tests/test_lesson_generation_service.py` (thêm case pack)

**Interfaces:**
- Sinh ra: `async def generate_lesson_pack(db, skill_id, *, count: int = 3) -> list[dict]`
  - Tạo/cập nhật draft `pack_index` 0..count-1
  - Prompt phân vai: L1 situation/notice, L2 form+checks, L3 meaning+writing
  - Mỗi bài vẫn `normalize_content` riêng
- `async def publish_lesson_pack(db, skill_id) -> dict` — publish tất cả draft đủ 0..2; fail nếu thiếu hoặc validate fail

- [x] **Bước 1: Test fail — publish pack thiếu index**

```python
import pytest
from app.services.lesson_generation_service import assert_pack_publishable

def test_assert_pack_publishable_requires_three_indices():
    with pytest.raises(ValueError, match="pack"):
        assert_pack_publishable(indices_ready={0, 1}, required=3)
```

- [x] **Bước 2: Implement `assert_pack_publishable` + gen stub/LLM**

```python
def assert_pack_publishable(*, indices_ready: set[int], required: int = 3) -> None:
    need = set(range(required))
    if not need.issubset(indices_ready):
        missing = sorted(need - indices_ready)
        raise ValueError(f"LessonPack incomplete; missing pack_index={missing}")
```

Gen: gọi LLM 1 lần trả mảng 3 content **hoặc** 3 lần theo role prompt (chốt: **1 lần JSON `{ "lessons": [ {...}, {...}, {...} ] }`** để giảm cost).

- [x] **Bước 3: Wire admin endpoint**

`POST /admin/skills/{skill_id}/lessons/generate-pack`  
`POST /admin/skills/{skill_id}/lessons/publish-pack`

- [x] **Bước 4: Pytest + smoke thủ công một skill `be_present`**

- [x] **Bước 5: Commit**

```bash
git commit -m "$(cat <<'EOF'
feat: admin generate and publish LessonPack

EOF
)"
```

---

### Task 4: Practice gen dùng union targets của pack

**Files:**
- Modify: `backend/app/services/quiz_generation_service.py` (và nơi load lesson targets)
- Test: `backend/tests/test_quiz_generation_skill_drill.py`

**Interfaces:**
- Khi load targets cho `skill_drill`: union `targets[].surface` từ **mọi** `skill_lessons` status=published của skill (mọi `pack_index`), không chỉ bài đầu.

- [x] **Bước 1: Test pure helper**

```python
from app.services.skill_drill_align import surfaces_from_lessons  # hoặc lesson helper

def test_union_surfaces_across_pack():
    lessons = [
        {"content": {"targets": [{"surface": "am"}]}},
        {"content": {"targets": [{"surface": "is"}, {"surface": "are"}]}},
    ]
    assert surfaces_from_lessons(lessons) == {"am", "is", "are"}
```

- [x] **Bước 2: Implement + gắn vào gen skill_drill**

- [x] **Bước 3: Pytest**

Run: `cd backend && pytest tests/test_quiz_generation_skill_drill.py tests/test_skill_drill_align.py -v`

- [x] **Bước 4: Commit**

```bash
git commit -m "$(cat <<'EOF'
feat: skill_drill targets union LessonPack surfaces

EOF
)"
```

---

### Task 5: FE Learn chuỗi 1/3 → 3/3

**Files:**
- Modify: `frontend/my-app/lib/lesson.ts`
- Modify: trang learn / `LessonMiniUnit.tsx` / dashboard week learn entry
- Modify: `frontend/my-app/lib/api.ts` nếu cần complete kèm `pack_index`

**Interfaces:**
- Type response có `pack`, `pack_total`, `pack_completed_count`
- UI: tiến độ “Learn · 2/3”; sau bài cuối → CTA Practice
- Complete gọi API với `pack_index` của bài vừa xong

- [x] **Bước 1: Cập nhật types + client**

- [x] **Bước 2: Wire UI chuỗi pack; legacy `pack_total === 1` giữ UX cũ**

- [x] **Bước 3: Checklist tay** — skill 1 lesson vẫn OK; skill 3 lesson đi đủ rồi Practice

- [x] **Bước 4: Commit**

```bash
git commit -m "$(cat <<'EOF'
feat: learner UI for LessonPack micro-lesson chain

EOF
)"
```

---

### Task 6: Migration + model Theme Unit

**Files:**
- Tạo: `backend/alembic/versions/r7s8t9u0v1w2_learning_theme_units.py`
- Tạo: `backend/app/models/theme_unit.py`
- Modify: `backend/app/models/__init__.py`

**Interfaces:**

```python
class LearningThemeUnitDB(Base):
    __tablename__ = "learning_theme_units"
    id: int
    slug: str  # unique with cefr_level
    cefr_level: CEFRLevel
    title: str
    can_do: str
    sort_order: int
    is_active: bool

class ThemeUnitSkillDB(Base):
    __tablename__ = "theme_unit_skills"
    theme_unit_id: int
    skill_id: int
    position: int
    # Unique(theme_unit_id, skill_id)
    # Unique(skill_id)  # MVP: một skill một unit
```

- [x] **Bước 1: Model + migration** (unique `skill_id` trên join để enforce 1 unit/skill)

- [x] **Bước 2: Test import**

```python
from app.models.theme_unit import LearningThemeUnitDB, ThemeUnitSkillDB
```

- [x] **Bước 3: Commit**

```bash
git commit -m "$(cat <<'EOF'
feat: add learning_theme_units tables

EOF
)"
```

---

### Task 7: Seed Theme Unit A1/A2

**Files:**
- Tạo: `backend/app/seeds/theme_units_a1_a2.py`
- Test: `backend/tests/test_theme_unit_seed.py`
- Phụ thuộc: catalog đã seed (`cefr_ladder_a1_a2`)

**Interfaces:**
- `async def seed_theme_units(session) -> dict` idempotent
- Membership: phủ **mọi** slug trong `A1_SKILLS` + `A2_SKILLS`; không orphan
- ~6–8 unit/level; `can_do` / `title` EN

Ví dụ cấu trúc seed (chỉnh membership cho khớp slug thật):

```python
A2_UNITS: list[tuple[str, str, str, list[str]]] = [
    # (slug, title, can_do, skill_slugs)
    (
        "a2_talk_about_past",
        "Talking about the past",
        "I can talk about past events using past simple and past continuous.",
        ["past_continuous", "past_simple_vs_continuous", "used_to"],
    ),
    # ... đủ phủ A2_SKILLS
]
```

- [x] **Bước 1: Test fail**

```python
import pytest
from app.seeds.cefr_ladder_a1_a2 import A1_SKILLS, A2_SKILLS
from app.seeds.theme_units_a1_a2 import all_unit_skill_slugs, A1_UNITS, A2_UNITS

def test_a1_units_cover_all_catalog_slugs():
    catalog = {s[0] for s in A1_SKILLS}
    assert all_unit_skill_slugs(A1_UNITS) == catalog

def test_a2_units_cover_all_catalog_slugs():
    catalog = {s[0] for s in A2_SKILLS}
    assert all_unit_skill_slugs(A2_UNITS) == catalog

def test_no_duplicate_skill_across_units():
    slugs = all_unit_skill_slugs(A1_UNITS) | all_unit_skill_slugs(A2_UNITS)
    # all_unit_skill_slugs returns set — duplicate would have been dropped; assert len flat == len set
    flat_a1 = [s for _, _, _, skills in A1_UNITS for s in skills]
    assert len(flat_a1) == len(set(flat_a1))
```

- [x] **Bước 2: Viết seed lists + `seed_theme_units`**

- [x] **Bước 3: Pytest**

Run: `cd backend && pytest tests/test_theme_unit_seed.py -v`

- [x] **Bước 4: Commit**

```bash
git commit -m "$(cat <<'EOF'
feat: seed A1/A2 theme units over catalog skills

EOF
)"
```

---

### Task 8: DTO roadmap gắn Theme Unit

**Files:**
- Modify: `backend/app/services/roadmap_assembler_service.py` (`_assemble_week_dict` + load map skill→unit)
- Test: `backend/tests/test_roadmap_theme_unit_dto.py` (unit helper pure nếu tách)

**Interfaces:**
- Week dict thêm (nullable nếu skill chưa map — sau seed phải luôn có):

```python
"theme_unit_slug": str | None,
"theme_unit_title": str | None,
"theme_unit_can_do": str | None,
"theme_unit_position": int | None,
```

- Helper: `def attach_theme_unit_fields(week: dict, unit_by_skill_id: dict[int, dict]) -> dict`

- [x] **Bước 1: Test pure attach**

```python
from app.services.roadmap_assembler_service import attach_theme_unit_fields

def test_attach_theme_unit_fields():
    week = {"skill_id": 10, "skill_slug": "be_present"}
    out = attach_theme_unit_fields(
        week,
        {10: {"slug": "a1_be_basics", "title": "Basics with be", "can_do": "I can…", "position": 1}},
    )
    assert out["theme_unit_slug"] == "a1_be_basics"
    assert out["theme_unit_position"] == 1
```

- [x] **Bước 2: Load map khi assemble / get roadmap; gắn vào mọi week dict**

- [x] **Bước 3: Pytest assembler liên quan**

Run: `cd backend && pytest tests/test_roadmap_assembler_service.py tests/test_roadmap_theme_unit_dto.py -v`

- [x] **Bước 4: Commit**

```bash
git commit -m "$(cat <<'EOF'
feat: expose theme unit metadata on roadmap weeks

EOF
)"
```

---

### Task 9: FE roadmap gom theo Theme Unit + copy foundation

**Files:**
- Modify: `frontend/my-app/lib/roadmap.ts`
- Modify: `frontend/my-app/src/app/dashboard/page.tsx`
- Modify: `frontend/my-app/components/roadmap/WeekNode.tsx`
- (Tùy chọn) component mới `ThemeUnitSection.tsx`

**Interfaces:**
- Group weeks (và completed nếu có) theo `theme_unit_slug`
- Header section: `theme_unit_title` + `theme_unit_can_do`
- Copy path: “A2 foundation path” / tương đương EN theo `level`; **không** “You’ve achieved CEFR A2”
- Khi roadmap rỗng eligible / terminal: CTA level-challenge (dùng flow onboarding challenge hiện có nếu đã có trên dashboard)

- [x] **Bước 1: Types + group helper**

```typescript
export function groupWeeksByThemeUnit(weeks: RoadmapWeek[]): { unitKey: string; title: string; canDo: string; weeks: RoadmapWeek[] }[]
```

- [x] **Bước 2: Render section; WeekNode hiện title skill + tiến độ Learn pack nếu API có**

- [x] **Bước 3: Checklist tay** — home đọc theo unit

- [x] **Bước 4: Commit**

```bash
git commit -m "$(cat <<'EOF'
feat: group roadmap UI by theme unit with foundation copy

EOF
)"
```

---

### Task 10: Review hub nhẹ (phase 4) + polish copy thoát band

**Files:**
- Tạo/modify: endpoint hoặc mở rộng dashboard payload — ví dụ `GET /api/v1/skills/weak` hoặc field trên roadmap
- Modify: FE dashboard section “Review”
- Test: service pure filter mastery dưới 0.7 cùng `current_level`

**Interfaces:**
- `list_weak_skills(db, user_id, *, limit=5) -> list[{skill_id, title, mastery}]`
- Chỉ skill có quiz published; deep-link `/dashboard/practice/[skillId]`
- Không gắn Review vào horizon locked trong task này

- [x] **Bước 1: Test filter mastery**

```python
def test_pick_weak_skills_orders_by_mastery_asc():
    rows = [{"skill_id": 1, "mastery": 0.9}, {"skill_id": 2, "mastery": 0.2}]
    assert [r["skill_id"] for r in pick_weak(rows, threshold=0.7, limit=5)] == [2]
```

- [x] **Bước 2: API + FE section**

- [x] **Bước 3: Copy CTA challenge khi path cạn**

- [x] **Bước 4: Commit**

```bash
git commit -m "$(cat <<'EOF'
feat: light weak-skill review hub and band-exit copy

EOF
)"
```

---

### Task 11: Ops / verify (phase 3 checklist)

Không bắt buộc code mới; checklist khi chạy live:

- [x] Chạy migration + `python -m app.seeds.cefr_ladder_a1_a2` + `python -m app.seeds.theme_units_a1_a2`
- [x] Gen + publish LessonPack cho ≥3 skill thuộc **một** Theme Unit đã cover sách
- [x] Gen + publish `skill_drill` sau pack
- [x] Learner: Learn 1/3→3/3 → Practice → mastery ≥ 0.7 → complete week
- [x] Dashboard: section Theme Unit đúng can-do
- [x] Xác nhận copy không claim CEFR chứng chỉ

---

## Self-review plan ↔ spec

| Spec | Task |
|------|------|
| LessonPack 3 + Practice | Task 1–5 |
| Union targets drill | Task 4 |
| Theme Unit seed + 1 skill/unit | Task 6–7 |
| DTO + FE gom unit | Task 8–9 |
| Core assemble không đổi sang Unit | Task 8 (chỉ metadata) |
| Review hub | Task 10 |
| Ops một unit densify live | Task 11 |
| Không listen/speak/streak | Ràng buộc toàn cục |

---

## Handoff

Plan đã lưu tại `docs/superpowers/plans/2026-08-03-theme-unit-path-densified-lessons.md`.

**Hai cách chạy:**

1. **Subagent-Driven (khuyến nghị)** — mỗi task một subagent, review giữa các task  
2. **Inline Execution** — làm tuần tự trong session với checkpoint  

Bạn muốn cách nào?
