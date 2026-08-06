# Design: Practice critique follow-ups (UX harden)

**Date:** 2026-08-06  
**Status:** Implemented  
**Plan:** `docs/superpowers/plans/2026-08-06-practice-critique-followups.md`  
**Route:** `/dashboard/practice/[skillId]`  
**Critique source:** `.impeccable/critique/2026-08-06T02-03-06Z__my-app-src-app-dashboard-practice-skillid-page-tsx.md`  
**Depends on:** Practice Promova redesign (`2026-08-05-practice-promova-redesign-design.md`), `DESIGN.md`  
**Out of scope:** Backend APIs, mastery math, quiz generation, AppHeader redesign, Duolingo-style gamification  

---

## 1. Problem

Impeccable critique scored the practice surface **20/40**. Three **P1** issues were patched in-session (Back, Lesson reference, Review pack label). Remaining gaps still hurt Operate-mode learners:

| Priority | Issue | Status |
|----------|--------|--------|
| P1 | Continue-only mini-unit (no Back) | **Done** |
| P1 | Memory Bridge (content vanishes before Check/Write) | **Done** |
| P1 | Pack label `Part 4/3` vs chips | **Done** |
| P2 | `QuizCard` visual drift + raw `mcq` badge | Open |
| P2 | Duplicate titles + non-interactive `StepChips` | Open |
| Minor | Shell jargon `mastery ≥ 70%` | Open |
| Minor | Wrong Check → no Try again | Open |
| Minor | QaDock suggestions compete with Continue on Notice | Open |
| Minor | Review always restarts at step 1 (no scrub) | Open |
| Minor | Detector `low-contrast` on muted ink | Open |

Goal: **close the critique backlog** with small, testable UX refinements — same IA and APIs, better control, clarity, and Promova consistency.

---

## 2. Goals / Non-goals

### Goals

1. **Quiz feels like Learn** — `QuizCard` uses the same panel/CTA language as `LessonMiniUnit` (cream-adjacent Promova, not generic `bg-card`).
2. **Human labels** — no raw `mcq` / enum strings in learner chrome; shell copy avoids engineer jargon.
3. **Navigation freedom** — StepChips jump Learn ↔ Practice ↔ Path when allowed; one title authority.
4. **Error recovery on Check** — wrong reveal offers **Try again** without forcing Continue or leaving the step.
5. **Lower first-viewport load on Learn** — Q&A suggestions do not outcompete Continue on Notice.
6. **Review efficiency** — returning learners can jump to a mini-unit step without replaying every Continue.
7. **Contrast floor** — secondary text meets WCAG AA (~4.5:1) on `#FFF8F4` / white panels where easy.

### Non-goals

- Changing `MASTERY_PASS = 0.7` or mastery computation.
- Making StepChips control pack index across multi-pack learn (only phase jumps).
- Full QaDock redesign or moving Q&A into Practice phase.
- Re-running brand/world replacement (`new-work`); this is refinement on incumbent Promova.
- Fixing detector false positives (`overused-font`, intentional atmosphere glow) unless contrast is real.

---

## 3. Decisions (locked for this increment)

| Topic | Decision |
|-------|----------|
| Scope | All remaining critique items above (not P1 rework) |
| Title ownership | **Shell H1 wins.** Embedded `LessonMiniUnit` drops duplicate H2 title when `embedded`; keeps objective + progress (`Notice · 2 of 5`) + pack label |
| Chip clicks | `learn` → phase learn if lesson available; `practice` → `openPractice` when `can_skip` or learn done or already in practice; `path` → `/dashboard` always (same as Back to path). Upcoming / locked chips are non-interactive |
| Quiz type labels | Map: `mcq` → `Multiple choice`, `cloze` → `Fill in the blank`, `fix_grammar` → `Fix the sentence`; unknown → title-case fallback |
| Shell subtitle | Default: `Learn the skill, then practice until Mastery reaches 70%.` (badge still shows `Mastery N%`) |
| Try again | On Check/Exit wrong reveal: secondary **Try again** clears answer + `revealed`; Back + Continue remain |
| QaDock | On Learn: suggestion chips **hidden until learner leaves first content step** (after first Continue from hook/notice — i.e. when mini-unit step ≠ first in order). Dock chrome (Ask field) stays. Alternative acceptable: mobile starts collapsed via existing panel prop if simpler — prefer suggestion delay for lower risk |
| Review scrub | When reviewing (`packLabel === "Review"` or explicit `reviewMode`), show a compact step jumper under progress; jumping does not call `onFinished` |
| Contrast | Prefer `#6B6478` (or darker) over `#8A8396` for body/secondary on cream/white; leave coral CTA white text unless a follow-up audit demands change |

---

## 4. Information architecture (unchanged)

```
load skill lesson meta
  ├─ Learn available && !can_skip → phase = learn
  └─ else → phase = practice

Learn mini-unit steps (Back already shipped)
  → completeSkillLesson → more packs? stay learn : practice

Practice quiz → mastery updates → ready when ≥ 70% → path
Optional: Review lesson → phase = learn (reviewMode UX)
```

Chip clicks are shortcuts into existing phase transitions — they must not bypass learn-before-practice when `!can_skip`.

---

## 5. UX contracts

### 5.1 QuizCard (Promova)

- Panel: `rounded-[1.75rem]`, white, soft border `#EDE6E0`, shadow matching Learn card.
- Primary CTA: coral `#FF8A6B`, height ~44px, `rounded-2xl`.
- Options: selected = peach wash + coral border; correct feedback = sky tint; incorrect = error soft (no Duolingo green).
- Badges: soft chips (not raw shadcn `secondary` enum dump); hide TOEIC part badge unless useful — if shown, label clearly (`TOEIC Part 5`), never only `r5`.

### 5.2 StepChips

- Visual states unchanged (active coral wash, done sky wash, upcoming muted).
- Interactive chips: `button` or `role="button"` with focus ring coral.
- Locked (`upcoming` when jump disallowed): `aria-disabled`, no pointer handler.
- Current phase chip may be non-navigating (already there) or refresh-safe no-op.

### 5.3 CheckPanel recovery

After wrong reveal:

```
[ Answer: … ]
[ Back ] [ Try again ] [ Continue ]   // stack on mobile: Back+Try on row, Continue full width OK
```

After correct reveal: Back + Continue (no Try again required).

### 5.4 Review step jumper

```
Review · Notice · 2 of 5
[Notice] [Meaning] [Check] [Write] [Feedback]   // only steps present in order
```

- Active step highlighted (coral soft).
- Disabled/hide `feedback` until writing feedback exists (or allow jump to Write only).

### 5.5 Lesson reference (already shipped — do not regress)

- Collapsible passage + targets remain on Check / Write / Feedback / Exit.

---

## 6. Component impact

| Component | Change |
|-----------|--------|
| `QuizCard.tsx` | Promova restyle + type label helper |
| `PracticeShell.tsx` | Subtitle default; pass `onStepSelect` into StepChips; secondary text contrast |
| `StepChips.tsx` | Optional `onSelect`; button semantics |
| `page.tsx` | `handleStepSelect`; title/subtitle wiring; `reviewMode` prop into mini-unit |
| `LessonMiniUnit.tsx` | Hide embedded H2 title; Try again; review jumper; contrast tweaks |
| `QaDock.tsx` / `LessonQaPanel.tsx` | Prop to suppress suggestion chips (`showSuggestions?: boolean`) |
| `DESIGN.md` | No change unless token docs need secondary ink note |

---

## 7. Acceptance criteria

1. Practice quiz screenshot no longer shows raw `mcq`; card matches Learn panel radius/shadow language.
2. Shell subtitle has no `≥` jargon glyph as primary explanation.
3. With `can_skip`, clicking Learn chip from Practice opens Learn; Practice chip returns to quiz.
4. Embedded Learn does not show the same skill title twice (shell + mini-unit).
5. Wrong Check → Try again re-enables options; Back still works.
6. On first Notice viewport, Q&A suggestion chip row is absent; after Continue, suggestions may appear.
7. Review mode: jumper moves to Meaning/Check without completing the pack.
8. Manual mobile ~390px: Back/Try/Continue usable; chips wrap without overflow.
9. Critique Priority Issues P2 + listed minors addressed or explicitly deferred in plan Task notes.

---

## 8. Risks

| Risk | Mitigation |
|------|------------|
| Chip jump bypasses required Learn | Gate `practice` jump on `can_skip \|\| learnDone \|\| phase===practice` |
| Suggestion delay confuses power users | Ask field always visible; only chips delayed |
| Review jumper into Feedback empty | Only enable Feedback step when `feedback != null` |
| Scope creep into full polish | Stick to §2; no QuizCard animation pass |

---

## 9. Related docs

- Critique archive: `.impeccable/critique/2026-08-06T02-03-06Z__my-app-src-app-dashboard-practice-skillid-page-tsx.md`
- Prior redesign: `docs/superpowers/specs/2026-08-05-practice-promova-redesign-design.md`
- Visual system: `DESIGN.md`
