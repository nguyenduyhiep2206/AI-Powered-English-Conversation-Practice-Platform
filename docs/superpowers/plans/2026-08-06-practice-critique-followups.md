# Practice Critique Follow-ups Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close remaining Impeccable critique findings on `/dashboard/practice/[skillId]` (P2 + minors) without changing Learn/Practice APIs or mastery rules.

**Architecture:** Refine presentational shells (`QuizCard`, `StepChips`, `PracticeShell`) and harden `LessonMiniUnit` / QaDock props. Orchestration stays in `page.tsx`. P1 work (Back, Lesson reference, Review label) is already on `main` working tree — do not regress.

**Tech Stack:** Next.js App Router, React client components, Tailwind, shadcn Button/Badge/Input, existing `@/lib/lesson` + `@/lib/quiz`.

**Spec:** `docs/superpowers/specs/2026-08-06-practice-critique-followups-design.md`

## Global Constraints

- Tokens from repo-root `DESIGN.md` (EnglishFlow Promova) — no Duolingo green `#58CC02`
- Preserve `MASTERY_PASS = 0.7` and all fetch/submit handlers
- Q&A only in Learn phase; Practice hides Q&A
- Do **not** commit unless the user explicitly asks
- Do not re-implement P1 Back / Lesson reference / Review pack label unless a regression is found
- Prefer rem literals matching existing practice components (`text-[0.875rem]`, `rounded-[1.75rem]`)

---

## Baseline already shipped (skip unless regression)

| Item | Where |
|------|--------|
| Back on mini-unit steps | `LessonMiniUnit.tsx` (`StepActions`, `goBack`) |
| Lesson reference strip | `LessonContextStrip` on check/write/feedback/exit |
| Review pack label | `page.tsx` `lessonPackLabel` / `learnPackDetail` |

---

## File map

| File | Responsibility |
|------|----------------|
| Modify `frontend/my-app/components/practice/QuizCard.tsx` | Promova panel + human type labels |
| Modify `frontend/my-app/components/practice/PracticeShell.tsx` | Subtitle; chip select prop; contrast |
| Modify `frontend/my-app/components/practice/StepChips.tsx` | Clickable chips |
| Modify `frontend/my-app/src/app/dashboard/practice/[skillId]/page.tsx` | `handleStepSelect`; `reviewMode`; suggestion gate |
| Modify `frontend/my-app/components/lesson/LessonMiniUnit.tsx` | Hide embedded title; Try again; review jumper |
| Modify `frontend/my-app/components/lesson/LessonQaPanel.tsx` | `showSuggestions?: boolean` |
| Modify `frontend/my-app/components/practice/QaDock.tsx` | Pass through `showSuggestions` |

---

### Task 1: `QuizCard` Promova + type labels

**Files:**
- Modify: `frontend/my-app/components/practice/QuizCard.tsx`

**Interfaces:**
- Produces (internal helper):
```ts
function quizTypeLabel(type: string): string {
  switch (type) {
    case "mcq":
      return "Multiple choice";
    case "cloze":
      return "Fill in the blank";
    case "fix_grammar":
      return "Fix the sentence";
    default:
      return type.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
  }
}
```

- [ ] **Step 1: Add label helper and restyle shell**

Replace the outer section and badge row so they match Learn panels:

```tsx
const PANEL =
  "rounded-[1.75rem] border border-[#EDE6E0] bg-white p-6 shadow-[0_12px_40px_rgba(42,36,56,0.04)]";

// badges — soft chips, not variant="secondary" enum dump:
<span className="inline-flex min-h-8 items-center rounded-2xl bg-[#FFF0E8] px-3 text-[0.75rem] font-medium text-[#C45D42] ring-1 ring-[#FF8A6B]/25">
  Question {index + 1} / {total}
</span>
<span className="inline-flex min-h-8 items-center rounded-2xl bg-[#FFFCF9] px-3 text-[0.75rem] font-medium text-[#6B6478] ring-1 ring-[#EDE6E0]">
  {quizTypeLabel(question.question_type)}
</span>
```

- Replace `border-border` / `bg-card` / `text-muted-foreground` option classes with Promova tokens (reuse coral selected / sky correct / error incorrect patterns from redesign).
- Remove left `border-l-2` passage accent if present (craft-floor: colored border-left ban) — use a soft inset panel instead:

```tsx
<div className="mb-5 rounded-2xl bg-[#FFFCF9] px-4 py-3 ring-1 ring-[#EDE6E0]">
  <p className="text-[0.75rem] font-medium uppercase tracking-[0.14em] text-[#6B6478]">
    Passage
  </p>
  ...
</div>
```

- [ ] **Step 2: Typecheck**

Run: `cd frontend/my-app && npx tsc --noEmit -p tsconfig.json 2>&1 | head -40`  
Expected: no new errors from `QuizCard.tsx`.

- [ ] **Step 3: Manual verify**

Open a skill in Practice phase. Confirm: no raw `mcq` string; card radius/shadow matches Learn white card.

---

### Task 2: Shell subtitle + secondary contrast

**Files:**
- Modify: `frontend/my-app/components/practice/PracticeShell.tsx`

**Interfaces:**
- Consumes: later Task 3 will add `onStepSelect` — in this task only change copy/contrast; optionally add the prop as passthrough stub typed optional.

- [ ] **Step 1: Update default subtitle and muted text**

```tsx
subtitle = "Learn the skill, then practice until Mastery reaches 70%.",
```

Change subtitle / loading muted classes from `#8A8396` → `#6B6478`.

- [ ] **Step 2: Manual verify**

Reload practice page — subtitle readable, no `≥` glyph.

---

### Task 3: Interactive `StepChips` + page wiring + single title

**Files:**
- Modify: `frontend/my-app/components/practice/StepChips.tsx`
- Modify: `frontend/my-app/components/practice/PracticeShell.tsx`
- Modify: `frontend/my-app/src/app/dashboard/practice/[skillId]/page.tsx`
- Modify: `frontend/my-app/components/lesson/LessonMiniUnit.tsx` (embedded header only)

**Interfaces:**
- Produces:
```ts
// StepChips.tsx
export function StepChips(props: {
  steps: StepChip[];
  onSelect?: (id: StepChipId) => void;
  /** Chip ids that may be activated (in addition to current active). */
  selectableIds?: StepChipId[];
}): JSX.Element;

// PracticeShell — add:
onStepSelect?: (id: StepChipId) => void;
selectableStepIds?: StepChipId[];
```

- [ ] **Step 1: Make chips buttons when selectable**

```tsx
export function StepChips({
  steps,
  onSelect,
  selectableIds,
}: {
  steps: StepChip[];
  onSelect?: (id: StepChipId) => void;
  selectableIds?: StepChipId[];
}) {
  const canSelect = (id: StepChipId, state: StepChipState) =>
    Boolean(onSelect && selectableIds?.includes(id) && state !== "active");

  return (
    <nav aria-label="Lesson progress" className="mt-3 flex flex-wrap gap-2">
      {steps.map((step, i) => {
        const interactive = canSelect(step.id, step.state);
        const className = cn(
          "inline-flex min-h-9 items-center gap-1.5 rounded-2xl px-3 text-[0.75rem] font-medium ring-1",
          step.state === "active" &&
            "bg-[#FFF0E8] text-[#C45D42] ring-[#FF8A6B]/35",
          step.state === "done" &&
            "bg-[#E8F4FB] text-[#3D7FA0] ring-[#8CC6E8]/40",
          step.state === "upcoming" &&
            "bg-white/70 text-[#6B6478] ring-[#2A2438]/06",
          interactive &&
            "cursor-pointer transition-colors hover:ring-[#FF8A6B]/40 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#FF8A6B]",
          !interactive && step.state !== "active" && "opacity-80",
        );
        const body = (
          <>
            <span className="tabular-nums text-[#B0A9B8]">{i + 1}.</span>
            {step.label}
            {step.detail ? ` ${step.detail}` : ""}
            {step.state === "done" ? (
              <Check className="h-3.5 w-3.5" aria-hidden strokeWidth={2.5} />
            ) : null}
          </>
        );
        if (interactive) {
          return (
            <button
              key={step.id}
              type="button"
              className={className}
              onClick={() => onSelect?.(step.id)}
            >
              {body}
            </button>
          );
        }
        return (
          <span key={step.id} className={className} aria-current={step.state === "active" ? "step" : undefined}>
            {body}
          </span>
        );
      })}
    </nav>
  );
}
```

- [ ] **Step 2: Wire `PracticeShell` → `StepChips`**

Pass `onStepSelect` / `selectableStepIds` through.

- [ ] **Step 3: Implement `handleStepSelect` on the practice page**

```tsx
function handleStepSelect(id: StepChipId) {
  if (id === "learn") {
    if (lessonMeta?.learn_available && lessonMeta.lesson) {
      setPhase("learn");
    }
    return;
  }
  if (id === "practice") {
    if (phase === "practice") return;
    if (lessonMeta?.can_skip || learnDone) {
      void openPractice();
    }
    return;
  }
  if (id === "path") {
    router.push("/dashboard");
  }
}

const selectableStepIds: StepChipId[] = [];
if (hasLearn && phase !== "learn") selectableStepIds.push("learn");
if (
  phase !== "practice" &&
  (lessonMeta?.can_skip || learnDone || questions.length > 0)
) {
  selectableStepIds.push("practice");
}
selectableStepIds.push("path");
```

- [ ] **Step 4: Single title — embedded mini-unit**

In `LessonMiniUnit` embedded header, remove the `<h2>{title}</h2>` (shell already shows title). Keep `packLabel`, `objective`, and `progressLabel`.

- [ ] **Step 5: Manual verify**

From Practice (can_skip skill): click Learn chip → Learn. Click Practice chip → quiz. Path → dashboard. No double H1/H2 title on Learn.

---

### Task 4: Try again on wrong Check

**Files:**
- Modify: `frontend/my-app/components/lesson/LessonMiniUnit.tsx` (`CheckPanel`)

**Interfaces:**
- Extends `CheckPanel` props:
```ts
onRetry?: () => void; // clear answer + revealed
```

- [ ] **Step 1: Add Try again when revealed && !correct**

```tsx
{revealed ? (
  <div className="space-y-3">
    <p className={`text-[0.875rem] ${correct ? "text-[#3D7FA0]" : "text-[#C24B3A]"}`}>
      {correct ? "Correct" : `Answer: ${check.answer}`}
    </p>
    <div className="grid gap-2 sm:grid-cols-2">
      {onBack ? (
        <Button type="button" size="lg" variant="outline" className={SECONDARY_BTN} onClick={onBack}>
          Back
        </Button>
      ) : null}
      {!correct && onRetry ? (
        <Button type="button" size="lg" variant="outline" className={SECONDARY_BTN} onClick={onRetry}>
          Try again
        </Button>
      ) : null}
      <Button
        type="button"
        size="lg"
        className={cn(PRIMARY_BTN, (!correct && onRetry) || onBack ? "sm:col-span-2" : "")}
        onClick={onContinue}
      >
        Continue
      </Button>
    </div>
  </div>
) : (
  ...
)}
```

Wire:

```tsx
onRetry={() => {
  setCheckAnswer("");
  setCheckRevealed(false);
}}
// exit check:
onRetry={() => {
  setExitAnswer("");
  setExitRevealed(false);
}}
```

Adjust grid so Back + Try again share a row when both exist; Continue full width below is fine.

- [ ] **Step 2: Manual verify**

Review lesson → Check → wrong answer → Try again re-enables options → Back still returns to prior step.

---

### Task 5: Delay QaDock suggestions until after first step

**Files:**
- Modify: `frontend/my-app/components/lesson/LessonQaPanel.tsx`
- Modify: `frontend/my-app/components/practice/QaDock.tsx`
- Modify: `frontend/my-app/components/lesson/LessonMiniUnit.tsx` (expose current step or callback)
- Modify: `frontend/my-app/src/app/dashboard/practice/[skillId]/page.tsx`

**Interfaces:**
```ts
// LessonQaPanel + QaDock
showSuggestions?: boolean; // default true for backward compat

// LessonMiniUnit — add optional:
onStepChange?: (step: Step) => void;
// call inside goTo() and on mount for initial step
```

- [ ] **Step 1: Gate suggestions in `LessonQaPanel`**

Where suggestion chips render, wrap with `showSuggestions !== false` (or `if (showSuggestions)` when default true).

- [ ] **Step 2: Track mini-unit step on page**

```tsx
const [learnStep, setLearnStep] = useState<string | null>(null);
// pass onStepChange={setLearnStep} to LessonMiniUnit
// showSuggestions={learnStep != null && learnStep !== orderFirst}
// Simpler rule per spec: hide while on first step of order only.
```

Practical rule for page without knowing order:

```tsx
// LessonMiniUnit reports: onStepChange(step, { index, total })
onStepChange?: (info: { step: string; index: number; total: number }) => void;

// page:
const [learnStepIndex, setLearnStepIndex] = useState(0);
showSuggestions={learnStepIndex > 0}
```

- [ ] **Step 3: Manual verify**

Open Learn Notice: Ask field visible, **no** suggestion chip row. Continue once: suggestions appear.

---

### Task 6: Review step jumper

**Files:**
- Modify: `frontend/my-app/components/lesson/LessonMiniUnit.tsx`
- Modify: `frontend/my-app/src/app/dashboard/practice/[skillId]/page.tsx`

**Interfaces:**
```ts
// LessonMiniUnit Props
reviewMode?: boolean;
```

- [ ] **Step 1: Pass `reviewMode={reviewingLearn}` from page**

- [ ] **Step 2: Render jumper when `reviewMode`**

```tsx
{reviewMode ? (
  <div className="flex flex-wrap gap-1.5" role="navigation" aria-label="Lesson steps">
    {order.map((s) => {
      const disabled = s === "feedback" && !feedback;
      const active = s === step;
      return (
        <button
          key={s}
          type="button"
          disabled={disabled}
          onClick={() => {
            if (s === "check") {
              setCheckIndex(0);
              resetCheckDraft();
            }
            goTo(s);
          }}
          className={cn(
            "rounded-2xl px-2.5 py-1.5 text-[0.75rem] font-medium ring-1",
            active
              ? "bg-[#FFF0E8] text-[#C45D42] ring-[#FF8A6B]/35"
              : "bg-white text-[#6B6478] ring-[#EDE6E0]",
            disabled && "opacity-40",
          )}
        >
          {STEP_LABEL[s]}
        </button>
      );
    })}
  </div>
) : null}
```

Do **not** call `onFinished` from jumper.

- [ ] **Step 3: Manual verify**

Review lesson → jump to Check → Lesson reference present → jump to Write → draft empty OK → Back still walks reverse.

---

### Task 7: Contrast sweep (practice Learn surfaces)

**Files:**
- Modify muted `#8A8396` → `#6B6478` in:
  - `PracticeShell.tsx` (if any remain)
  - `QuizCard.tsx`
  - `LessonMiniUnit.tsx` (caption/eyebrow where used as body-adjacent)
  - `StepChips.tsx` upcoming text (already noted)

- [ ] **Step 1: Ripgrep and replace learner-facing secondary ink on cream/white**

Run: `rg -n '#8A8396' frontend/my-app/components/practice frontend/my-app/components/lesson/LessonMiniUnit.tsx`

Replace learner-visible secondary text; keep decorative/atmosphere alone.

- [ ] **Step 2: Optional browser detect**

If Playwright available: open practice Learn, inject impeccable detect; expect fewer `low-contrast` on muted captions. Do not churn coral CTA contrast in this task.

---

### Task 8: End-to-end acceptance + critique note

**Files:** none required (optional comment in critique file or leave archive as-is)

- [ ] **Step 1: Manual checklist (desktop + ~390px)**

| # | Check | Pass? |
|---|--------|-------|
| 1 | QuizCard Promova + human type label | |
| 2 | Subtitle without `≥` | |
| 3 | Chip Learn/Practice/Path jumps gated correctly | |
| 4 | Single title on Learn | |
| 5 | Try again on wrong Check | |
| 6 | Suggestions hidden on first step only | |
| 7 | Review jumper works; no false complete | |
| 8 | P1 Back + Lesson reference not regressed | |
| 9 | Pack label still `Review` when reviewing | |

- [ ] **Step 2: Optional re-critique**

Run `/impeccable critique` on the same practice page path and compare trend score vs **20/40**.

---

## Self-review (plan vs spec)

| Spec § | Task |
|--------|------|
| Quiz Promova + labels | Task 1 |
| Shell subtitle | Task 2 |
| Chips + single title | Task 3 |
| Try again | Task 4 |
| QaDock suggestions delay | Task 5 |
| Review scrub | Task 6 |
| Contrast | Task 7 |
| Acceptance / verify | Task 8 |
| P1 items | Baseline — no task |

No TBD placeholders. Commit steps omitted (user rule: commit only when asked).

---

## Execution handoff

Plan complete and saved to:

- Spec: `docs/superpowers/specs/2026-08-06-practice-critique-followups-design.md`
- Plan: `docs/superpowers/plans/2026-08-06-practice-critique-followups.md`

**Two execution options:**

1. **Subagent-Driven (recommended)** — fresh subagent per task, review between tasks  
2. **Inline Execution** — this session, `executing-plans`, checkpoints after Tasks 3 and 6
