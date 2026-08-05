# Design: Practice skill page redesign (Promova UI)

**Date:** 2026-08-05  
**Status:** Accepted  
**Plan:** `docs/superpowers/plans/2026-08-05-practice-promova-redesign.md`  
**Route:** `/dashboard/practice/[skillId]`  
**Approach:** B — component shell (`PracticeShell` + `StepChips` + `QuizCard` + `QaDock`)  
**Depends on:** existing Learn / Practice quiz / Lesson Q&A flows; `DESIGN.md` (EnglishFlow Promova)  
**Out of scope:** backend APIs, quiz generation, RAG logic, AI Tutor session UI  

---

## 1. Problem

The practice page still reads as an older “card + muted shadcn” screen:

- Flat `bg-background` column (max-w-2xl), not warm Promova canvas.
- Learn opens in a modal (`LessonContentWindow`) instead of an inline study layout.
- Lesson Q&A is stacked under Learn with Notion-like chrome, not a docked coach panel.
- Step chips and feedback use green “success” tones that conflict with locked Promova tokens (coral / sky / lilac).
- Logic and layout are tangled in one large `page.tsx`, which makes a full visual pass brittle.

Goal: **same learning IA and APIs**, Promova visual system, clearer Learn vs Practice composition.

---

## 2. Goals / Non-goals

### Goals

- Restyle the full practice UI + Lesson Q&A to Promova (`DESIGN.md` tokens, Plus Jakarta, soft pastels).
- **Learn (desktop):** split — lesson content ~60% left, Q&A dock ~40% right.
- **Learn (mobile):** stack — lesson first, Q&A below (not bottom sheet in v1).
- **Practice:** Q&A hidden; quiz uses a focused full-width (capped) single column.
- Soft step chips: Learn → Practice → Path (Complete week), plus coral mastery pill — **no XP/streak**.
- Remove Learn modal: content is inline in the left column (`embedded` LessonMiniUnit).
- Extract presentational shells so `page.tsx` keeps orchestration only.

### Non-goals

- Changing mastery threshold (still ≥ 70%), question loading, or submit APIs.
- Redesigning AppHeader (already Promova).
- Building a separate marketing “lesson room” or heavy illustration scene (Approach C).
- Showing Q&A during Practice phase.

---

## 3. Information architecture (unchanged)

```
load skill lesson meta
  ├─ Learn available && !can_skip → phase = learn
  └─ else → phase = practice (load quiz)

Learn: finish mini-unit pack step → completeSkillLesson → more packs? stay learn : → practice
Practice: answer questions → mastery updates → mastery ≥ 70% → CTA back to path
Optional: Review lesson from Practice → phase = learn (Q&A returns)
```

Copy may soften (“This week” / skill title) but flow gates stay identical.

---

## 4. Layout

### 4.1 Shared chrome

- Canvas: `#FFF8F4` + light coral/sky atmosphere (subtle, not purple mesh).
- `AppHeader` remains.
- Back link: “Back to path” → `/dashboard`.
- Title: skill lesson title when known, else “This week”.
- Subcopy: short line explaining Learn then Practice to mastery.
- **StepChips:** three soft chips  
  1. Learn (active / done with check)  
  2. Practice quiz (active when phase=practice)  
  3. Path (aka Complete week — ready when mastery ≥ 70%)  
- **Mastery pill:** coral primary when ready; otherwise outline / soft surface with `%`.

### 4.2 Learn — desktop (≥ md)

```
┌─────────────────────────────────────────────────────────────┐
│ AppHeader                                                   │
├─────────────────────────────────────────────────────────────┤
│ Back · Title · StepChips · Mastery                          │
├──────────────────────────────┬──────────────────────────────┤
│ Lesson column (~60%)         │ QaDock (~40%)                │
│ LessonMiniUnit (embedded)    │ LessonQaPanel (dock variant) │
│ rounded-2xl surface card     │ sticky / fill remaining h    │
└──────────────────────────────┴──────────────────────────────┘
```

- No `LessonContentWindow` modal for the primary Learn path.
- Skip / dismiss when `can_skip`: text/button in lesson column header (“Skip to practice”), calling existing `openPractice`.

### 4.3 Learn — mobile (< md)

- Single column: chrome → lesson card → Q&A card stacked.
- Touch targets ≥ 44px; type ramp from `DESIGN.md`.

### 4.4 Practice

- Single column (max ~640–704px centered).
- `QuizCard`: passage, stem, MCQ/cloze/fix_grammar controls, check CTA, feedback panel, next / back-to-path.
- Soft option tiles (coral selected state), gentle correct/incorrect (sky/coral-soft or error tokens — **not Duolingo green**).

---

## 5. Component breakdown (Approach B)

| Component | Responsibility |
|-----------|----------------|
| `PracticeShell` | Canvas, atmosphere, max width grid, header slot (back/title/steps/mastery), phase layout wrapper |
| `StepChips` | Learn / Practice / Path chip states |
| `QuizCard` | Presentational quiz surface (controlled props from page) |
| `QaDock` | Right-column / stacked wrapper; hosts restyled `LessonQaPanel` |
| `LessonQaPanel` | Logic kept; visual + `variant?: "floating" \| "dock"` for height/chrome |
| `LessonMiniUnit` | Logic kept; Promova tokens for steps/buttons/inputs |
| `page.tsx` | State, fetches, phase transitions only |

`LessonContentWindow` stays in repo for any other callers but is **not** used as the primary Learn chrome on this route after redesign.

---

## 6. Visual / motion (Taste dials: 6 / 5 / 5)

- Surfaces: white / `#FFFCF9`, `rounded-2xl`, light ring `ink/6`, soft shadow per `DESIGN.md`.
- Primary CTA: coral `#FF8A6B` → hover `#F47A5A`.
- Links / secondary accent: violet `#7B6EF6`.
- Feedback correct: soft sky / secondary treatment (not `#346538` green).
- Feedback incorrect: `#C24B3A` / `#FFF0EE`.
- Motion: fade/slide-up on phase enter and quiz feedback (`ef-fade-up` or framer-light CSS); respect `prefers-reduced-motion`.
- No XP bars, streak fire, Duolingo green.

---

## 7. Accessibility

- One `h1` (skill / week title).
- Step chips are status, not a second nav (or `nav` with clear `aria-label="Lesson progress"`).
- Quiz options: buttons with selected state + keyboard.
- Q&A dock: existing roles; composer ≥ 44px; focus rings coral.
- Loading / error regions with polite live text where useful.

---

## 8. Testing / QC

- Manual / Playwright: Learn split at 1440; stacked at 390; Practice quiz interactions unchanged.
- Empty quiz / learn unavailable still show clear empty/error states in Promova chrome.
- Impeccable QC pass after Taste implement (token compliance).

---

## 9. Migration notes

- Existing users’ mastery and lesson completion unchanged.
- No API contract changes.
- If `LessonContentWindow` is unused after cutover on this page only, do not delete in this PR unless grep shows zero callers.

---

## 10. Open decisions (resolved in brainstorming)

| Topic | Decision |
|-------|----------|
| Scope | Full UI + Lesson Q&A |
| Layout | Desktop split Learn+Q&A; Practice full-width quiz |
| Q&A timing | Learn only |
| Learn chrome | Inline, no modal |
| Progress | Soft step chips + coral mastery |
| Approach | B — shell components |
| Existing null avatars | N/A (separate work) |

---

## Spec self-review

- No TBD placeholders for core layout.
- Scope limited to frontend practice route + lesson presentational components.
- No contradiction with existing Learn→Practice gate APIs.
- Approach C deliberately excluded.
