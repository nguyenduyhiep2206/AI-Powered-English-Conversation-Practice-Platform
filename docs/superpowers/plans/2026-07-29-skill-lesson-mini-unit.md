# Skill Lesson Mini-Unit (hướng D) Implementation Plan

> **For agentic workers:** Use superpowers:executing-plans or subagent-driven-development. Steps use checkbox syntax.

**Goal:** Discard slide Learn; ship mini-unit Learn (read→check→write→feedback) then Practice quiz; mastery/complete-week unchanged.

**Architecture:** `skill_lessons.content` = mini-unit JSON; offline text gen; serve-time writing feedback; `LEARN_UNIT_ENABLED` flag.

**Tech Stack:** FastAPI, SQLAlchemy async, Alembic, `chat_json`, Next.js, pytest.

**Spec:** `docs/superpowers/specs/2026-07-29-skill-lesson-mini-unit-design.md`

## Global Constraints

- No image gen for lessons
- 1 lesson / skill
- `LEARN_UNIT_ENABLED=false` → `learn_available=false`
- Complete week does not require lesson progress
- `can_skip = lesson_completed OR mastery >= 0.7`
- Admin permission: `book:manage`

## Tasks (summary)

1. Migration + models + `lesson_content_validate`
2. Offline `lesson_generation_service` + tests
3. `lesson_service` + `lesson_writing_feedback` + APIs + `main.py` + settings flag
4. FE `LessonMiniUnit` + practice page + admin lessons page
