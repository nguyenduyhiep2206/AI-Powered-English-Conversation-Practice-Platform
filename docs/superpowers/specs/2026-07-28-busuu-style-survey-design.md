# Design: Survey onboarding kiểu Busuu (Option C)

**Date:** 2026-07-28  
**Status:** Approved for planning  
**Scope:** Survey questions + submit API + onboarding FE wizard + level fork  
**Non-scope:** Drop DB columns `occupation` / `weak_point`; habit reminders; change placement engine

---

## 1. Decision

Onboarding learner theo Busuu-lite:

1. Why learning (goal)  
2. Daily study time  
3. Level fork: beginner → A1 | self-select CEFR | placement test  
4. Learn (assemble roadmap when onboarding complete)

**Keep** `user_profiles.occupation` and `weak_point` columns and existing placement/roadmap fallbacks when null. **Stop collecting** them in the active survey.

---

## 2. Why → goal mapping

Extend `GoalEnum` with Busuu-style reasons (keep legacy values for existing rows):

| UI label | Enum value | `GOAL_TO_CATEGORY` |
|---|---|---|
| Work | `work` | `job_interview` |
| School | `school` | `custom` |
| Travel | `travel` | `travel` (existing) |
| Culture | `culture` | `small_talk` |
| Family & community | `family` | `small_talk` |
| Challenge myself | `challenge` | `small_talk` |
| Other | `other` | `small_talk` |

Legacy: `job_interview`, `daily_conversation`, `ielts`, `business` remain valid; map unchanged in `GOAL_TO_CATEGORY`.

---

## 3. Daily time

Active options: `5` / `10` / `15` / `25` minutes → `daily_time_min`.  
Still storage-only (no session-length logic in this change).

---

## 4. Level resolution

`POST /onboarding/survey` accepts `level_resolution`:

| `mode` | Effect |
|---|---|
| `beginner` | `current_level=A1`, `placement_score=1`, skip placement |
| `self_selected` | requires `cefr_level`; set level + `placement_score=5` (neutral sub-level floor) |
| `placement` | `survey_done=True`, `placement_score` stays null → FE → `/onboarding/placement` |

`onboarding_complete` unchanged: `survey_done && placement_score is not None`.

Response includes `next_step`: `"placement"` | `"completed"`.

---

## 5. FE UX

Wizard: one question per screen + progress bar (Busuu pattern).  
Screens: why → time → know English? → (optional) know level? → (optional) pick CEFR → submit → redirect by `next_step`.

---

## 6. Out of scope

- Deleting `occupation` / `weak_point` columns or bias code  
- Wiring `daily_time_min` into reminders / lesson length  
- Changing adaptive placement algorithm  
