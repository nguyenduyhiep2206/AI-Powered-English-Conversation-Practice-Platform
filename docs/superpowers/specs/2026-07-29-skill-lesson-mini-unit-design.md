# Design: Skill lessons — Mini-unit Learn (hướng D)

**Date:** 2026-07-29  
**Status:** Implementing  
**Plan:** `docs/superpowers/plans/2026-07-29-skill-lesson-mini-unit.md`  
**Scope:** `backend` (models + offline text gen + serve-time writing feedback + APIs), `frontend/my-app` (mini-unit Learn → Practice quiz)  
**Depends on:** Skill graph + ZPD roadmap (`2026-07-20-skill-graph-zpd-roadmap-design.md`), quiz per skill  
**Supersedes:** `2026-07-26-skill-lessons-learn-phase-design.md` (slides + images discarded), `2026-07-21-roadmap-learning-content-design.md`  
**Research:** Exa — Readov/Lenguia/LingQ input→output; Busuu tip→drill→write hybrid  

---

## 1. Problem

Learner vào skill từ roadmap chỉ làm quiz, hoặc (bản slide 26/07) xem carousel GRR rồi quiz — không khớp pattern đọc/viết thắng trên market. Cần **mini-unit**: đọc đoạn → notice targets → check nhẹ → viết + AI feedback → quiz mastery.

## 2. Goals / Non-goals

### Goals

- 1 published mini-unit / skill (`passage`, `targets`, `checks`, `writing`)
- Cùng schema mọi `skill_type`; nội dung khác qua prompt guidance
- FE: Learn (read→check→write→feedback) → Practice quiz trên `/dashboard/practice/[skillId]`
- Learn bắt buộc lần đầu; skip khi `user_lesson_progress` hoặc mastery ≥ 0.7
- Content gen **offline** (text only); writing feedback **serve-time** LLM (không mastery)
- Flag `LEARN_UNIT_ENABLED` (default false) đến khi có lesson published đủ
- **English→English only**: title, objective, glosses, checks, writing prompt, feedback notes đều EN; gloss = định nghĩa/paraphrase đơn giản theo CEFR của skill
- Complete week chỉ mastery ≥ 0.7

### Non-goals

- Slide deck / image-per-slide / `image_client`
- SRS flashcard bank; tap-to-translate mọi từ; audio
- Đổi ZPD / skill graph / quiz generation
- Complete week phụ thuộc Learn
- WYSIWYG admin editor lớn

## 3. Decisions

| Chủ đề | Quyết định |
|--------|------------|
| Presentation | Mini-unit steps, không slides |
| Images | Không (MVP) |
| Writing feedback | Serve-time LLM side-by-side |
| Cardinality | 1 lesson / skill |
| Learn gate | Bắt buộc lần đầu; rồi skip |
| Missing published / flag off | Thẳng Practice |
| Complete week | Chỉ mastery ≥ 0.7 |

## 4. Architecture

```text
Offline (admin)
  skill + book excerpt → LLM JSON mini-unit → draft → publish

Online (learner)
  GET lesson → FE mini-unit → POST writing/feedback → POST complete → quiz → mastery
```

Feature flag: `LEARN_UNIT_ENABLED` (default false).

## 5. Data model

### `skill_lessons`

| Column | Notes |
|--------|--------|
| `skill_id` UNIQUE FK | 1 / skill |
| `title`, `objective` | |
| `content` JSON | mini-unit object (not slides array) |
| `source` | `llm_reviewed` \| `human` |
| `status` | `draft` \| `published` |
| `book_source_id` | nullable FK |

### `user_lesson_progress`

UNIQUE(`user_id`, `skill_id`), `completed_at`.

### Content schema

```json
{
  "passage": { "text": "EN...", "gloss": "optional short EN context at CEFR" },
  "targets": [{ "surface": "...", "gloss": "simple EN definition at CEFR", "note": "optional EN tip" }],
  "checks": [{ "type": "mcq|cloze", "prompt": "EN", "options": ["..."], "answer": "..." }],
  "writing": { "prompt": "EN instruction", "min_words": 15, "must_use": ["..."] }
}
```

Publish: passage non-empty; 4–7 targets; 1–2 valid checks; writing.prompt non-empty.

## 6. APIs

- `GET /api/v1/skills/{id}/lesson`
- `POST /api/v1/skills/{id}/lesson/writing/feedback` body `{ text }`
- `POST /api/v1/skills/{id}/lesson/complete`
- Admin: list / get / generate / publish (`book:manage`)

## 7. Frontend

Phase `learn` | `practice`. Component `LessonMiniUnit`: steps read → check → write → feedback → complete → quiz.

## 8. Summary

Learn = mini-unit input→output. Slides/images discarded. Quiz mastery unchanged.
