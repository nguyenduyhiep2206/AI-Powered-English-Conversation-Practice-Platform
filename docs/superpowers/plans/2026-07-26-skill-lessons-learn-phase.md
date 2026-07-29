# Skill Lessons Learn Phase (Slides + Offline Images) Implementation Plan

> **SUPERSEDED (2026-07-29):** Use `docs/superpowers/plans/2026-07-29-skill-lesson-mini-unit.md` and design `docs/superpowers/specs/2026-07-29-skill-lesson-mini-unit-design.md`. Slide Learn discarded.

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Offline pipeline sinh slide lesson (text + ảnh) theo skill, admin publish; learner chỉ thấy Learn khi flag bật + lesson `published`; FE slide deck → Practice quiz; complete week vẫn chỉ mastery ≥ 0.7.

**Architecture:** Bảng `skill_lessons` (1/skill, JSON slides) + `user_lesson_progress`. Serve-time chỉ đọc (`lesson_service`). Gen offline: `chat_json` → validate slides → image API → upload Supabase → draft → publish (ảnh bắt buộc trên intro/explanation/example/key_points). Feature flag `LEARN_SLIDES_ENABLED` (default false) giữ Practice quiz-only đến khi sẵn.

**Tech Stack:** FastAPI, SQLAlchemy async, Alembic, LangChain/`chat_json`, OpenAI-compatible image API, Supabase Storage, Next.js practice page, pytest.

**Spec:** `docs/superpowers/specs/2026-07-26-skill-lessons-learn-phase-design.md`

## Global Constraints

- Không gọi LLM/image khi learner `GET` lesson / mở Practice
- 1 lesson / skill (`UNIQUE(skill_id)`)
- Publish chỉ khi slide bắt buộc có `image_url`
- `LEARN_SLIDES_ENABLED=false` → `learn_available=false` dù có published
- Thiếu published / flag off → FE thẳng Practice (không fallback Learn text)
- Complete week **không** kiểm tra lesson progress
- `can_skip = lesson_completed OR mastery >= 0.7` (`MASTERY_STRONG`)
- Ngôn ngữ: meta VI; example/key_points EN
- Permission admin: `book:manage` (giống quiz generate)
- Commit style: conventional (`feat:`, `test:`, `fix:`) — chỉ commit khi session được phép

---

## File map

| File | Responsibility |
|------|----------------|
| `backend/alembic/versions/k1l2m3n4o5p6_add_skill_lessons_and_progress.py` | Tables `skill_lessons`, `user_lesson_progress` |
| `backend/app/models/skill_lesson.py` | ORM `SkillLessonDB`, `UserLessonProgressDB` |
| `backend/app/models/__init__.py` | Export models |
| `backend/app/core/config.py` | `LEARN_SLIDES_ENABLED`, image model, lesson bucket |
| `backend/app/services/lesson_slide_validate.py` | Pure validate/normalize slide JSON + publish readiness |
| `backend/app/services/lesson_service.py` | GET payload + mark complete + mastery skip |
| `backend/app/services/lesson_image_storage.py` | Upload image bytes → public/signed URL |
| `backend/app/services/image_client.py` | Offline image bytes from prompt |
| `backend/app/services/lesson_generation_service.py` | Orchestrate text LLM + images → draft; publish |
| `backend/app/api/skills.py` | Learner GET/POST lesson |
| `backend/app/api/admin_quiz.py` (or `admin_lessons.py`) | Admin generate + publish |
| `backend/main.py` | Mount `/api/v1/skills` |
| `backend/tests/test_lesson_slide_validate.py` | Schema / publish rules |
| `backend/tests/test_lesson_service.py` | learn_available / can_skip / complete |
| `backend/tests/test_lesson_generation_service.py` | Mock LLM + image → draft/publish |
| `frontend/my-app/lib/lesson.ts` | fetchLesson / completeLesson |
| `frontend/my-app/components/lesson/LessonSlideDeck.tsx` | Slide UI |
| `frontend/my-app/src/app/dashboard/practice/[skillId]/page.tsx` | Learn → Practice phases |

---

### Task 1: Migration + ORM models

**Files:**
- Create: `backend/app/models/skill_lesson.py`
- Create: `backend/alembic/versions/k1l2m3n4o5p6_add_skill_lessons_and_progress.py`
- Modify: `backend/app/models/__init__.py`

**Interfaces:**
- Produces: `SkillLessonDB`, `UserLessonProgressDB`

- [ ] **Step 1: Add model file**

```python
# backend/app/models/skill_lesson.py
from sqlalchemy import (
    BigInteger, Column, ForeignKey, String, Text, TIMESTAMP, UniqueConstraint, func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from app.core.database import Base


class SkillLessonDB(Base):
    __tablename__ = "skill_lessons"
    __table_args__ = (UniqueConstraint("skill_id", name="uq_skill_lessons_skill_id"),)

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    skill_id = Column(
        BigInteger, ForeignKey("learning_skills.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    title = Column(String(500), nullable=False)
    objective = Column(Text, nullable=False)
    content = Column(JSONB, nullable=False)  # list[slide dict]
    source = Column(String(20), nullable=False, server_default="llm_reviewed")
    status = Column(String(20), nullable=False, server_default="draft")
    book_source_id = Column(
        BigInteger, ForeignKey("book_skill_sources.id", ondelete="SET NULL"), nullable=True,
    )
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(
        TIMESTAMP(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now(),
    )


class UserLessonProgressDB(Base):
    __tablename__ = "user_lesson_progress"
    __table_args__ = (
        UniqueConstraint("user_id", "skill_id", name="uq_user_lesson_progress"),
    )

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    skill_id = Column(
        BigInteger, ForeignKey("learning_skills.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    completed_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())
```

- [ ] **Step 2: Export in `models/__init__.py`**

Import `SkillLessonDB`, `UserLessonProgressDB` and add to `__all__`.

- [ ] **Step 3: Alembic revision**

`down_revision = "j0k1l2m3n4o5"` (verify with `alembic heads` at execute time).

```python
"""add skill_lessons and user_lesson_progress

Revision ID: k1l2m3n4o5p6
Revises: j0k1l2m3n4o5
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "k1l2m3n4o5p6"
down_revision = "j0k1l2m3n4o5"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "skill_lessons",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("skill_id", sa.BigInteger(), sa.ForeignKey("learning_skills.id", ondelete="CASCADE"), nullable=False),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("objective", sa.Text(), nullable=False),
        sa.Column("content", postgresql.JSONB(), nullable=False),
        sa.Column("source", sa.String(20), nullable=False, server_default="llm_reviewed"),
        sa.Column("status", sa.String(20), nullable=False, server_default="draft"),
        sa.Column("book_source_id", sa.BigInteger(), sa.ForeignKey("book_skill_sources.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("skill_id", name="uq_skill_lessons_skill_id"),
    )
    op.create_index("ix_skill_lessons_skill_id", "skill_lessons", ["skill_id"])

    op.create_table(
        "user_lesson_progress",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.BigInteger(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("skill_id", sa.BigInteger(), sa.ForeignKey("learning_skills.id", ondelete="CASCADE"), nullable=False),
        sa.Column("completed_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("user_id", "skill_id", name="uq_user_lesson_progress"),
    )
    op.create_index("ix_user_lesson_progress_user_id", "user_lesson_progress", ["user_id"])
    op.create_index("ix_user_lesson_progress_skill_id", "user_lesson_progress", ["skill_id"])


def downgrade() -> None:
    op.drop_table("user_lesson_progress")
    op.drop_table("skill_lessons")
```

- [ ] **Step 4: Run migration**

```bash
cd backend && .venv/bin/alembic upgrade head
```

Expected: success; tables exist.

- [ ] **Step 5: Commit** (when session allows)

```bash
git add backend/app/models/skill_lesson.py backend/app/models/__init__.py \
  backend/alembic/versions/k1l2m3n4o5p6_add_skill_lessons_and_progress.py
git commit -m "$(cat <<'EOF'
feat: add skill_lessons and user_lesson_progress tables

EOF
)"
```

---

### Task 2: Slide schema validation (pure)

**Files:**
- Create: `backend/app/services/lesson_slide_validate.py`
- Test: `backend/tests/test_lesson_slide_validate.py`

**Interfaces:**
- Produces:
  - `REQUIRED_IMAGE_TYPES = frozenset({"intro", "explanation", "example", "key_points"})`
  - `OPTIONAL_IMAGE_TYPES = frozenset({"inline_check", "takeaway"})`
  - `ALLOWED_TYPES = REQUIRED_IMAGE_TYPES | OPTIONAL_IMAGE_TYPES`
  - `normalize_slides(raw: list) -> list[dict]` — raises `ValueError`
  - `assert_publishable(slides: list[dict]) -> None` — raises if required slides missing image_url

- [ ] **Step 1: Failing tests**

```python
# backend/tests/test_lesson_slide_validate.py
import pytest
from app.services.lesson_slide_validate import assert_publishable, normalize_slides


def _base_slides():
    return [
        {"type": "intro", "text": "Xin chào", "image_url": "https://x/a.webp", "image_alt": "a"},
        {"type": "explanation", "text": "Rule VI", "image_url": "https://x/b.webp", "image_alt": "b"},
        {"type": "example", "text": "I am Mai.", "gloss_vi": "Tôi là Mai.", "image_url": "https://x/c.webp", "image_alt": "c"},
        {"type": "key_points", "items": ["I'm", "You're"], "image_url": "https://x/d.webp", "image_alt": "d"},
        {"type": "inline_check", "prompt": "She ___ a teacher.", "options": ["am", "is", "are"], "answer": "is"},
        {"type": "takeaway", "text": "I→am"},
    ]


def test_normalize_ok():
    slides = normalize_slides(_base_slides())
    assert len(slides) == 6
    assert slides[3]["items"] == ["I'm", "You're"]


def test_reject_unknown_type():
    bad = _base_slides()
    bad[0]["type"] = "video"
    with pytest.raises(ValueError):
        normalize_slides(bad)


def test_publishable_requires_images():
    slides = normalize_slides(_base_slides())
    assert_publishable(slides)
    slides[0]["image_url"] = ""
    with pytest.raises(ValueError, match="image"):
        assert_publishable(slides)


def test_must_include_required_types():
    with pytest.raises(ValueError):
        normalize_slides([{"type": "intro", "text": "only"}])
```

- [ ] **Step 2: Run — expect FAIL**

```bash
cd backend && .venv/bin/python -m pytest tests/test_lesson_slide_validate.py -v
```

- [ ] **Step 3: Implement `lesson_slide_validate.py`**

```python
"""Validate / normalize skill lesson slide JSON."""

from __future__ import annotations

from typing import Any

REQUIRED_IMAGE_TYPES = frozenset({"intro", "explanation", "example", "key_points"})
OPTIONAL_IMAGE_TYPES = frozenset({"inline_check", "takeaway"})
ALLOWED_TYPES = REQUIRED_IMAGE_TYPES | OPTIONAL_IMAGE_TYPES


def normalize_slides(raw: list[Any]) -> list[dict[str, Any]]:
    if not isinstance(raw, list) or not raw:
        raise ValueError("content must be a non-empty list of slides")
    out: list[dict[str, Any]] = []
    seen: set[str] = set()
    for i, item in enumerate(raw):
        if not isinstance(item, dict):
            raise ValueError(f"slide {i} must be an object")
        t = str(item.get("type") or "").strip()
        if t not in ALLOWED_TYPES:
            raise ValueError(f"slide {i}: unknown type {t!r}")
        seen.add(t)
        slide: dict[str, Any] = {"type": t}
        if t == "key_points":
            items = item.get("items")
            if not isinstance(items, list) or not items:
                raise ValueError(f"slide {i}: key_points needs non-empty items")
            slide["items"] = [str(x).strip() for x in items if str(x).strip()]
        elif t == "inline_check":
            prompt = str(item.get("prompt") or "").strip()
            answer = str(item.get("answer") or "").strip()
            if not prompt or not answer:
                raise ValueError(f"slide {i}: inline_check needs prompt and answer")
            slide["prompt"] = prompt
            slide["answer"] = answer
            opts = item.get("options")
            if opts is not None:
                slide["options"] = [str(x) for x in opts]
        else:
            text = str(item.get("text") or "").strip()
            if not text:
                raise ValueError(f"slide {i}: text required")
            slide["text"] = text
        if item.get("title"):
            slide["title"] = str(item["title"]).strip()
        if item.get("gloss_vi"):
            slide["gloss_vi"] = str(item["gloss_vi"]).strip()
        if item.get("image_url"):
            slide["image_url"] = str(item["image_url"]).strip()
        if item.get("image_alt"):
            slide["image_alt"] = str(item["image_alt"]).strip()
        out.append(slide)
    missing = REQUIRED_IMAGE_TYPES - seen
    if missing:
        raise ValueError(f"missing required slide types: {sorted(missing)}")
    return out


def assert_publishable(slides: list[dict[str, Any]]) -> None:
    for s in slides:
        if s["type"] in REQUIRED_IMAGE_TYPES:
            if not s.get("image_url"):
                raise ValueError(f"publish requires image_url on {s['type']} slide")
```

- [ ] **Step 4: Run tests — PASS**

```bash
cd backend && .venv/bin/python -m pytest tests/test_lesson_slide_validate.py -v
```

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/lesson_slide_validate.py backend/tests/test_lesson_slide_validate.py
git commit -m "$(cat <<'EOF'
feat: validate skill lesson slide schema and publish rules

EOF
)"
```

---

### Task 3: Config flag + `lesson_service` (serve path)

**Files:**
- Modify: `backend/app/core/config.py`
- Create: `backend/app/services/lesson_service.py`
- Test: `backend/tests/test_lesson_service.py`

**Interfaces:**
- Consumes: `SkillLessonDB`, `UserLessonProgressDB`, `UserSkillMasteryDB`, `LearningSkillDB`, `MASTERY_STRONG`, `settings.LEARN_SLIDES_ENABLED`
- Produces:
  - `async def get_lesson_for_user(db, user_id: int, skill_id: int) -> dict`
  - `async def complete_lesson(db, user_id: int, skill_id: int) -> dict`

`get_lesson_for_user` return shape:

```python
{
  "skill_id": int,
  "skill_title": str,
  "lesson": None | {"title", "objective", "content", "source"},
  "lesson_completed": bool,
  "can_skip": bool,
  "learn_available": bool,
}
```

Rules:
- Skill missing/inactive → raise `ValueError("Skill not found")`
- `learn_available = settings.LEARN_SLIDES_ENABLED and published_lesson_exists`
- If not learn_available → `lesson=None`
- `can_skip = lesson_completed or mastery >= MASTERY_STRONG`

- [ ] **Step 1: Add settings**

In `Settings`:

```python
LEARN_SLIDES_ENABLED: bool = False
OPENAI_IMAGE_MODEL: str = "dall-e-3"
SUPABASE_LESSON_BUCKET: str = "lesson-images"
SUPABASE_LESSON_BUCKET_PUBLIC: bool = True
```

- [ ] **Step 2: Failing pure/unit tests with mocks**

Prefer testing helpers that don't need DB if extracted; otherwise mock AsyncSession patterns used in `test_roadmap_progress_service.py`.

```python
# backend/tests/test_lesson_service.py
from app.services.lesson_service import compute_can_skip, compute_learn_available
from app.services.mastery_service import MASTERY_STRONG


def test_learn_available_needs_flag_and_published():
    assert compute_learn_available(flag=False, has_published=True) is False
    assert compute_learn_available(flag=True, has_published=False) is False
    assert compute_learn_available(flag=True, has_published=True) is True


def test_can_skip():
    assert compute_can_skip(lesson_completed=False, mastery=0.2) is False
    assert compute_can_skip(lesson_completed=True, mastery=0.2) is True
    assert compute_can_skip(lesson_completed=False, mastery=MASTERY_STRONG) is True
```

- [ ] **Step 3: Implement service**

```python
# backend/app/services/lesson_service.py  (core helpers + async orchestrators)
def compute_learn_available(*, flag: bool, has_published: bool) -> bool:
    return bool(flag) and bool(has_published)


def compute_can_skip(*, lesson_completed: bool, mastery: float) -> bool:
    from app.services.mastery_service import MASTERY_STRONG
    return bool(lesson_completed) or float(mastery) >= float(MASTERY_STRONG)
```

Implement `get_lesson_for_user` / `complete_lesson` with SQLAlchemy selects; upsert progress on complete (`on conflict` or select-then-insert). Commit in API layer or service — match existing quiz pattern (service flush, API commit if needed). Prefer service commits like other orchestrators in this codebase — check `complete_roadmap_week` (commits) vs quiz (commits in route). **Match `complete_roadmap_week`: service commits.**

- [ ] **Step 4: Run tests**

```bash
cd backend && .venv/bin/python -m pytest tests/test_lesson_service.py -v
```

- [ ] **Step 5: Commit**

```bash
git add backend/app/core/config.py backend/app/services/lesson_service.py backend/tests/test_lesson_service.py
git commit -m "$(cat <<'EOF'
feat: add lesson serve helpers and LEARN_SLIDES_ENABLED flag

EOF
)"
```

---

### Task 4: Learner API `/api/v1/skills/{skill_id}/lesson`

**Files:**
- Create: `backend/app/api/skills.py`
- Modify: `backend/main.py`

**Interfaces:**
- Consumes: `get_lesson_for_user`, `complete_lesson`, `get_current_active_user`

- [ ] **Step 1: Router**

```python
# backend/app/api/skills.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_active_user
from app.core.database import get_db
from app.models.user import UserDB
from app.services.lesson_service import complete_lesson, get_lesson_for_user

router = APIRouter()


@router.get("/{skill_id}/lesson")
async def get_skill_lesson(
    skill_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: UserDB = Depends(get_current_active_user),
):
    try:
        return await get_lesson_for_user(db, int(current_user.id), skill_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/{skill_id}/lesson/complete")
async def post_skill_lesson_complete(
    skill_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: UserDB = Depends(get_current_active_user),
):
    try:
        return await complete_lesson(db, int(current_user.id), skill_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
```

- [ ] **Step 2: Mount**

In `backend/main.py`:

```python
from app.api import skills
app.include_router(skills.router, prefix="/api/v1/skills", tags=["skills"])
```

- [ ] **Step 3: Smoke manually or add thin test** — optional httpx if project has TestClient patterns; otherwise rely on service tests.

- [ ] **Step 4: Commit**

```bash
git add backend/app/api/skills.py backend/main.py
git commit -m "$(cat <<'EOF'
feat: add learner skill lesson GET and complete APIs

EOF
)"
```

---

### Task 5: Lesson image storage helper

**Files:**
- Create: `backend/app/services/lesson_image_storage.py`
- Optionally extend: `backend/app/services/supabase_storage_service.py` with generic `upload_bytes` — prefer thin wrapper in `lesson_image_storage.py` reusing client pattern from `supabase_storage_service`.

**Interfaces:**
- Produces: `upload_lesson_image(*, skill_id: int, slide_index: int, content: bytes, content_type: str = "image/webp") -> str`  # returns URL

```python
def upload_lesson_image(*, skill_id: int, slide_index: int, content: bytes, content_type: str = "image/png") -> str:
    from app.core.config import settings
    from app.services import supabase_storage_service
    # reuse _get_client / bucket settings.SUPABASE_LESSON_BUCKET
    path = f"lessons/{skill_id}/slide_{slide_index:02d}.png"
    ...
    return url
```

If Supabase not configured in tests, generation service must inject/mock this function.

- [ ] **Step 1: Implement upload helper** (mirror `upload_pdf` but image content-type + lesson bucket + `SUPABASE_LESSON_BUCKET_PUBLIC`).

- [ ] **Step 2: Commit**

```bash
git add backend/app/services/lesson_image_storage.py backend/app/core/config.py
git commit -m "$(cat <<'EOF'
feat: upload lesson slide images to Supabase Storage

EOF
)"
```

---

### Task 6: Image client (offline)

**Files:**
- Create: `backend/app/services/image_client.py`
- Test: `backend/tests/test_image_client.py` (mock HTTP / OpenAI)

**Interfaces:**
- Produces: `generate_image_png(prompt: str) -> bytes`
- Raises `RuntimeError` if no `OPENAI_API_KEY`

Implementation sketch (OpenAI Images API):

```python
def generate_image_png(prompt: str) -> bytes:
    if not settings.OPENAI_API_KEY:
        raise RuntimeError("OPENAI_API_KEY chưa được cấu hình")
    from openai import OpenAI
    client = OpenAI(api_key=settings.OPENAI_API_KEY, base_url=settings.OPENAI_BASE_URL or None)
    # Use images.generate; decode b64 → bytes
    ...
```

Also:

```python
def build_illustration_prompt(*, slide_type: str, text: str, cefr_level: str) -> str:
    return (
        f"Flat editorial illustration for ESL {cefr_level} lesson slide ({slide_type}). "
        f"Concept: {text[:200]}. No written text letters in the image, no logos, "
        f"warm monochrome soft shapes, simple characters, clean background."
    )
```

- [ ] **Step 1: Test `build_illustration_prompt` contains no-text instruction**

```python
from app.services.image_client import build_illustration_prompt

def test_prompt_bans_text_in_image():
    p = build_illustration_prompt(slide_type="example", text="I am Mai", cefr_level="A1")
    assert "No written text" in p or "no written text" in p.lower()
```

- [ ] **Step 2: Implement + run pytest**

- [ ] **Step 3: Commit**

```bash
git add backend/app/services/image_client.py backend/tests/test_image_client.py
git commit -m "$(cat <<'EOF'
feat: add offline image generation client for lesson slides

EOF
)"
```

---

### Task 7: Lesson generation orchestrator (text + images → draft/publish)

**Files:**
- Create: `backend/app/services/lesson_generation_service.py`
- Test: `backend/tests/test_lesson_generation_service.py`

**Interfaces:**
- Consumes: `chat_json`, `normalize_slides`, `assert_publishable`, `generate_image_png`, `upload_lesson_image`, `get_unit_context` (from primary source like quiz gen)
- Produces:
  - `async def generate_lesson_draft(db, skill_id: int) -> SkillLessonDB`
  - `async def publish_lesson(db, skill_id: int) -> SkillLessonDB`

**Text LLM contract** (system prompt must require VI meta / EN examples, types list, no images in LLM output):

```json
{
  "title": "...",
  "objective": "...",
  "slides": [ { "type": "...", "text": "...", ... } ]
}
```

Flow `generate_lesson_draft`:
1. Load skill; load primary non-excluded `BookSkillSourceDB` if any → excerpt via `get_unit_context` (same as quiz; if none, excerpt=`""` and still allow gen from skill title).
2. `chat_json(SYSTEM, user_payload)` → normalize_slides(slides) — **without** requiring images yet.
3. For each slide in `REQUIRED_IMAGE_TYPES` (and optional if desired): `build_illustration_prompt` → `generate_image_png` → `upload_lesson_image` → set `image_url`/`image_alt`.
4. Upsert `SkillLessonDB`: `status="draft"`, `source="llm_reviewed"`, set `book_source_id`, `content`, title, objective.
5. Commit; return row.

Flow `publish_lesson`:
1. Load lesson for skill; `normalize_slides` + `assert_publishable`.
2. Set `status="published"`; commit.

On LLM/image failure: do not publish; raise; leave previous published untouched if updating (MVP: overwrite draft only; if was published, keep published until new draft published — **MVP simple: one row; generate replaces content and forces `draft`**, admin must re-publish).

- [ ] **Step 1: Failing test with mocks**

```python
from unittest.mock import patch, MagicMock
import pytest

# async test pattern used in project — if rare, test pure `_attach_images(slides, skill_id)` sync helper

def test_attach_images_fills_required(monkeypatch):
    from app.services import lesson_generation_service as mod

    slides = [
        {"type": "intro", "text": "a"},
        {"type": "explanation", "text": "b"},
        {"type": "example", "text": "c"},
        {"type": "key_points", "items": ["x"]},
        {"type": "takeaway", "text": "t"},
    ]

    monkeypatch.setattr(mod, "generate_image_png", lambda prompt: b"PNG")
    monkeypatch.setattr(mod, "upload_lesson_image", lambda **kw: f"https://cdn/slide_{kw['slide_index']}.png")
    monkeypatch.setattr(mod, "build_illustration_prompt", lambda **kw: "p")

    out = mod.attach_images_to_slides(slides, skill_id=9, cefr_level="A1")
    assert out[0]["image_url"].endswith("0.png")
    assert "image_url" not in out[4] or out[4].get("image_url")  # takeaway optional — leave without
```

Implement `attach_images_to_slides` as sync helper used by orchestrator.

- [ ] **Step 2: Implement generation service + tests PASS**

```bash
cd backend && .venv/bin/python -m pytest tests/test_lesson_generation_service.py tests/test_lesson_slide_validate.py -v
```

- [ ] **Step 3: Commit**

```bash
git add backend/app/services/lesson_generation_service.py backend/tests/test_lesson_generation_service.py
git commit -m "$(cat <<'EOF'
feat: offline generate skill lesson slides with images to draft

EOF
)"
```

---

### Task 8: Admin generate + publish endpoints

**Files:**
- Create: `backend/app/api/admin_lessons.py` **or** extend `admin_quiz.py`
- Modify: `backend/main.py` if new router

**Recommend:** `admin_lessons.py` prefix `/api/v1/admin/lessons` for clarity.

```python
@router.post(
    "/skills/{skill_id}/generate",
    dependencies=[Depends(require_permission("book:manage"))],
)
async def admin_generate_lesson(skill_id: int, db: AsyncSession = Depends(get_db)):
    try:
        row = await generate_lesson_draft(db, skill_id)
    except ValueError as exc:
        raise HTTPException(400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(503, detail=str(exc)) from exc
    return {
        "data": {
            "skill_id": row.skill_id,
            "status": row.status,
            "title": row.title,
            "slide_count": len(row.content or []),
        }
    }


@router.post(
    "/skills/{skill_id}/publish",
    dependencies=[Depends(require_permission("book:manage"))],
)
async def admin_publish_lesson(skill_id: int, db: AsyncSession = Depends(get_db)):
    try:
        row = await publish_lesson(db, skill_id)
    except ValueError as exc:
        raise HTTPException(400, detail=str(exc)) from exc
    return {"data": {"skill_id": row.skill_id, "status": row.status}}
```

Mount: `app.include_router(admin_lessons.router, prefix="/api/v1/admin/lessons", tags=["admin-lessons"])`

- [ ] **Step 1: Implement + wire**
- [ ] **Step 2: Commit**

```bash
git add backend/app/api/admin_lessons.py backend/main.py
git commit -m "$(cat <<'EOF'
feat: admin APIs to generate and publish skill lessons

EOF
)"
```

---

### Task 9: Frontend — lesson client + slide deck + practice phases

**Files:**
- Create: `frontend/my-app/lib/lesson.ts`
- Create: `frontend/my-app/components/lesson/LessonSlideDeck.tsx`
- Modify: `frontend/my-app/src/app/dashboard/practice/[skillId]/page.tsx`
- Follow: `.cursor/skills/minimalist-ui/SKILL.md` for Learn UI (warm monochrome, no heavy cards)

**Interfaces:**
- `fetchSkillLesson(skillId) -> LessonResponse`
- `completeSkillLesson(skillId) -> ...`

- [ ] **Step 1: `lib/lesson.ts`**

```typescript
import { authFetch, extractErrorMessage } from "@/lib/api";

export type LessonSlide = {
  type: string;
  title?: string;
  text?: string;
  items?: string[];
  gloss_vi?: string;
  prompt?: string;
  options?: string[];
  answer?: string;
  image_url?: string;
  image_alt?: string;
};

export type SkillLessonResponse = {
  skill_id: number;
  skill_title: string;
  lesson: null | {
    title: string;
    objective: string;
    content: LessonSlide[];
    source: string;
  };
  lesson_completed: boolean;
  can_skip: boolean;
  learn_available: boolean;
};

export async function fetchSkillLesson(skillId: number): Promise<SkillLessonResponse> {
  const res = await authFetch(`/api/v1/skills/${skillId}/lesson`);
  if (!res.ok) {
    const error = await res.json().catch(() => ({}));
    throw new Error(extractErrorMessage(error, "Failed to load lesson"));
  }
  return res.json();
}

export async function completeSkillLesson(skillId: number): Promise<SkillLessonResponse> {
  const res = await authFetch(`/api/v1/skills/${skillId}/lesson/complete`, { method: "POST" });
  if (!res.ok) {
    const error = await res.json().catch(() => ({}));
    throw new Error(extractErrorMessage(error, "Failed to complete lesson"));
  }
  return res.json();
}
```

- [ ] **Step 2: `LessonSlideDeck`**

Props: `slides`, `title`, `objective`, `onFinished: () => void`.  
State: `index`. Show image (if `image_url`) + text/items; Next / Back; on last slide primary CTA “Tiếp tục luyện” → `onFinished`.  
Inline_check: local select + show correct/incorrect without calling mastery API.

- [ ] **Step 3: Wire practice page**

On load:
1. `fetchSkillLesson(skillId)` in parallel or before questions.
2. `phase = learn_available && !can_skip ? "learn" : "practice"`.
3. Learn finish → `completeSkillLesson` → `phase = "practice"` → existing quiz load.
4. If `learn_available && can_skip`, show text button “Xem lại bài học”.

When `!learn_available`, behavior identical to today (quiz only).

- [ ] **Step 4: Manual check** — flag off → quiz only; with fixture published + flag on → slides then quiz.

- [ ] **Step 5: Commit**

```bash
git add frontend/my-app/lib/lesson.ts \
  frontend/my-app/components/lesson/LessonSlideDeck.tsx \
  frontend/my-app/src/app/dashboard/practice/\[skillId\]/page.tsx
git commit -m "$(cat <<'EOF'
feat: add Learn slide deck phase before skill practice

EOF
)"
```

---

### Task 10: Enable checklist + spec status

**Files:**
- Modify: `docs/superpowers/specs/2026-07-26-skill-lessons-learn-phase-design.md` — status note when shipped
- Optional: `.env.example` document new settings

**Definition of done to set `LEARN_SLIDES_ENABLED=true` (ops, not code default):**
1. Migration applied
2. Supabase lesson bucket created
3. Admin generated + published ≥ 3 A1 lessons with images
4. FE Learn→Practice verified on one skill
5. Flag on in env

- [ ] **Step 1: Run full related suite**

```bash
cd backend && .venv/bin/python -m pytest \
  tests/test_lesson_slide_validate.py \
  tests/test_lesson_service.py \
  tests/test_image_client.py \
  tests/test_lesson_generation_service.py \
  -v
```

Expected: all PASS.

- [ ] **Step 2: Update spec status line when feature ready on an env**

- [ ] **Step 3: Commit docs if changed** (only when user allows)

---

## Self-review (plan vs spec)

| Spec requirement | Task |
|------------------|------|
| `skill_lessons` + `user_lesson_progress` | Task 1 |
| Slide schema + publish image rules | Task 2 |
| `LEARN_SLIDES_ENABLED` / learn_available | Task 3–4 |
| GET/POST learner lesson | Task 4 |
| Offline image storage | Task 5–6 |
| Offline LLM text + images → draft | Task 7 |
| Admin generate/publish | Task 8 |
| FE slides → Practice; quiz-only when unavailable | Task 9 |
| Ship gate C (flag default off) | Task 3 + 10 |
| Complete week unchanged | (no task — do not modify progress service) |
| No serve-time LLM | Tasks 3–4 only read DB |

**Placeholder scan:** none intentional; confirm alembic `down_revision` at execute time if heads moved.

**Type consistency:** `normalize_slides` / `assert_publishable` / `attach_images_to_slides` / `get_lesson_for_user` / `generate_lesson_draft` / `publish_lesson` names stable across tasks.

---

## Execution handoff

Plan saved to `docs/superpowers/plans/2026-07-26-skill-lessons-learn-phase.md`.

**Two execution options:**

1. **Subagent-Driven (recommended)** — fresh subagent per task, review between tasks  
2. **Inline Execution** — execute tasks in this session with checkpoints  

Which approach?
