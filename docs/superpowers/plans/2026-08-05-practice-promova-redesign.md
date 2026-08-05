# Practice Promova Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Redesign `/dashboard/practice/[skillId]` to Promova UI with Approach B shells — Learn split (lesson + Q&A dock), Practice focused quiz — without changing Learn/Practice APIs.

**Architecture:** Keep orchestration in `page.tsx`. Extract `PracticeShell`, `StepChips`, `QuizCard`, `QaDock`. Restyle `LessonQaPanel` (add `variant="dock"`) and `LessonMiniUnit` to `DESIGN.md` tokens. Remove modal Learn chrome on this route.

**Tech Stack:** Next.js App Router, React client components, Tailwind, shadcn Button/Input/Badge, existing `@/lib/lesson` + `@/lib/quiz` + `@/lib/lesson-qa`.

**Spec:** `docs/superpowers/specs/2026-08-05-practice-promova-redesign-design.md`

## Global Constraints

- Tokens and type ramp from repo-root `DESIGN.md` (EnglishFlow Promova) — no Duolingo green `#58CC02` / `#346538` success chrome
- Taste dials: VARIANCE 6 / MOTION 5 / DENSITY 5
- Preserve mastery threshold `MASTERY_PASS = 0.7` and all fetch/submit handlers
- Q&A only in Learn phase; Practice hides Q&A
- Learn: inline (no `LessonContentWindow` on this route); desktop split; mobile stack
- Do **not** commit unless the user explicitly asks
- Prefer `text-[0.9375rem]`-style rem literals from the type ramp (Impeccable-friendly)

---

## File map

| File | Responsibility |
|------|----------------|
| Create `frontend/my-app/components/practice/PracticeShell.tsx` | Canvas, atmosphere, chrome slots, Learn/Practice layout grid |
| Create `frontend/my-app/components/practice/StepChips.tsx` | Learn / Practice / Path chips |
| Create `frontend/my-app/components/practice/QuizCard.tsx` | Presentational quiz UI (controlled) |
| Create `frontend/my-app/components/practice/QaDock.tsx` | Dock / stacked wrapper around LessonQaPanel |
| Modify `frontend/my-app/components/lesson/LessonQaPanel.tsx` | Promova styles + `variant?: "floating" \| "dock"` |
| Modify `frontend/my-app/components/lesson/LessonMiniUnit.tsx` | Promova styles for embedded lesson |
| Modify `frontend/my-app/src/app/dashboard/practice/[skillId]/page.tsx` | Wire shells; drop modal Learn |
| Leave `LessonContentWindow.tsx` | Still used by `LessonContentPreview` — do not delete |

---

### Task 1: `StepChips`

**Files:**
- Create: `frontend/my-app/components/practice/StepChips.tsx`
- Test: visual / TypeScript compile only (no unit harness required)

**Interfaces:**
- Produces:
```ts
export type StepChipId = "learn" | "practice" | "path";

export type StepChipState = "upcoming" | "active" | "done";

export type StepChip = {
  id: StepChipId;
  label: string;
  state: StepChipState;
  detail?: string; // e.g. "1/3" for learn pack
};

export function StepChips({ steps }: { steps: StepChip[] }): JSX.Element;
```

- [ ] **Step 1: Add component**

```tsx
"use client";

import { Check } from "lucide-react";
import { cn } from "@/lib/utils";

export type StepChipId = "learn" | "practice" | "path";
export type StepChipState = "upcoming" | "active" | "done";

export type StepChip = {
  id: StepChipId;
  label: string;
  state: StepChipState;
  detail?: string;
};

export function StepChips({ steps }: { steps: StepChip[] }) {
  return (
    <nav aria-label="Lesson progress" className="mt-3 flex flex-wrap gap-2">
      {steps.map((step, i) => (
        <span
          key={step.id}
          className={cn(
            "inline-flex min-h-9 items-center gap-1.5 rounded-2xl px-3 text-[0.75rem] font-medium ring-1",
            step.state === "active" &&
              "bg-[#FFF0E8] text-[#C45D42] ring-[#FF8A6B]/35",
            step.state === "done" &&
              "bg-[#E8F4FB] text-[#3D7FA0] ring-[#8CC6E8]/40",
            step.state === "upcoming" &&
              "bg-white/70 text-[#8A8396] ring-[#2A2438]/06",
          )}
        >
          <span className="tabular-nums text-[#B0A9B8]">{i + 1}.</span>
          {step.label}
          {step.detail ? ` ${step.detail}` : ""}
          {step.state === "done" ? (
            <Check className="h-3.5 w-3.5" aria-hidden strokeWidth={2.5} />
          ) : null}
        </span>
      ))}
    </nav>
  );
}
```

- [ ] **Step 2: Sanity check**

Run: `cd frontend/my-app && npx tsc --noEmit -p tsconfig.json 2>&1 | head -40`  
Expected: no errors from `StepChips.tsx` (ignore unrelated pre-existing errors if any).

---

### Task 2: `PracticeShell`

**Files:**
- Create: `frontend/my-app/components/practice/PracticeShell.tsx`

**Interfaces:**
- Consumes: `StepChips` from Task 1
- Produces:
```ts
export function PracticeShell(props: {
  title: string;
  subtitle?: string;
  masteryPct: number | null;
  readyToComplete: boolean;
  steps: StepChip[];
  showSteps?: boolean;
  phase: "learn" | "practice";
  lesson: React.ReactNode;
  quiz: React.ReactNode;
  qa: React.ReactNode | null;
  loading?: boolean;
  loadingLabel?: string;
  banner?: React.ReactNode;
}): JSX.Element;
```

- [ ] **Step 1: Implement shell**

```tsx
"use client";

import type { ReactNode } from "react";
import Link from "next/link";
import { ArrowLeft, Loader2 } from "lucide-react";
import AppHeader from "@/components/AppHeader";
import { StepChips, type StepChip } from "@/components/practice/StepChips";
import { cn } from "@/lib/utils";

type Props = {
  title: string;
  subtitle?: string;
  masteryPct: number | null;
  readyToComplete: boolean;
  steps: StepChip[];
  showSteps?: boolean;
  phase: "learn" | "practice";
  lesson: ReactNode;
  quiz: ReactNode;
  qa: ReactNode | null;
  loading?: boolean;
  loadingLabel?: string;
  banner?: ReactNode;
};

export function PracticeShell({
  title,
  subtitle = "Learn the skill, then practice until mastery ≥ 70%.",
  masteryPct,
  readyToComplete,
  steps,
  showSteps = true,
  phase,
  lesson,
  quiz,
  qa,
  loading,
  loadingLabel,
  banner,
}: Props) {
  return (
    <div className="relative min-h-screen overflow-hidden bg-[#FFF8F4] text-[#2A2438]">
      <div
        aria-hidden
        className="pointer-events-none absolute inset-0"
        style={{
          background:
            "radial-gradient(ellipse 60% 40% at 10% 0%, rgba(255,164,140,0.28), transparent 55%), radial-gradient(ellipse 50% 35% at 90% 10%, rgba(140,198,232,0.22), transparent 50%)",
        }}
      />
      <div className="relative">
        <AppHeader />
        <main className="mx-auto max-w-6xl px-5 py-8 sm:px-6 lg:px-8">
          <div className="mb-6 flex flex-wrap items-start justify-between gap-3">
            <div className="min-w-0">
              <Link
                href="/dashboard"
                className="inline-flex min-h-11 items-center gap-1.5 text-[0.875rem] font-medium text-[#7B6EF6] transition-colors hover:text-[#6758E8] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#FF8A6B]"
              >
                <ArrowLeft className="h-4 w-4" aria-hidden />
                Back to path
              </Link>
              <h1 className="mt-2 text-[1.75rem] font-semibold tracking-tight text-[#2A2438]">
                {title}
              </h1>
              <p className="mt-1 text-[0.875rem] leading-relaxed text-[#8A8396]">
                {subtitle}
              </p>
              {showSteps ? <StepChips steps={steps} /> : null}
            </div>
            {masteryPct != null ? (
              <span
                className={cn(
                  "inline-flex min-h-9 items-center rounded-2xl px-3.5 text-[0.8125rem] font-semibold",
                  readyToComplete
                    ? "bg-[#FF8A6B] text-white shadow-[0_8px_20px_rgba(255,138,107,0.28)]"
                    : "bg-white text-[#6B6478] ring-1 ring-[#2A2438]/06",
                )}
              >
                Mastery {masteryPct}%
              </span>
            ) : null}
          </div>

          {banner}

          {loading ? (
            <div className="flex items-center justify-center gap-2 py-20 text-[0.875rem] text-[#8A8396]">
              <Loader2 className="h-5 w-5 animate-spin" aria-hidden />
              {loadingLabel ?? "Loading…"}
            </div>
          ) : phase === "learn" ? (
            <div className="grid gap-5 lg:grid-cols-[minmax(0,1.4fr)_minmax(280px,1fr)] lg:items-start">
              <div className="min-w-0 rounded-[1.75rem] bg-white p-5 shadow-[0_12px_40px_rgba(42,36,56,0.06)] ring-1 ring-[#2A2438]/06 sm:p-7">
                {lesson}
              </div>
              {qa ? <div className="min-w-0 lg:sticky lg:top-4">{qa}</div> : null}
            </div>
          ) : (
            <div className="mx-auto max-w-xl">{quiz}</div>
          )}
        </main>
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Typecheck** file compiles with Task 1.

---

### Task 3: `QuizCard`

**Files:**
- Create: `frontend/my-app/components/practice/QuizCard.tsx`

**Interfaces:**
- Consumes: question shape from `@/lib/quiz` `SkillQuizQuestion`
- Produces controlled quiz surface:

```ts
export function QuizCard(props: {
  question: SkillQuizQuestion;
  index: number;
  total: number;
  answer: string;
  onAnswerChange: (value: string) => void;
  feedback: {
    correct: boolean;
    explanation: string | null;
  } | null;
  submitting: boolean;
  error: string | null;
  readyToComplete: boolean;
  onSubmit: () => void;
  onNext: () => void;
  onBackToPath: () => void;
}): JSX.Element;
```

- [ ] **Step 1: Move presentational quiz markup** from `page.tsx` (lines ~254–434) into `QuizCard`, replace green success classes with:

```tsx
// correct feedback
"border-[#8CC6E8]/45 bg-[#E8F4FB] text-[#3D7FA0]"
// incorrect
"border-[#FF8A6B]/30 bg-[#FFF0EE] text-[#C24B3A]"
// selected option
"border-[#FF8A6B] bg-[#FFF0E8] text-[#2A2438]"
// primary buttons
"h-11 rounded-2xl bg-[#FF8A6B] font-semibold text-white hover:bg-[#F47A5A]"
```

Include MCQ / cloze / fix_grammar branches exactly as today (same labels and placeholders).

- [ ] **Step 2: Empty / error outside card** remain page-level banners inside `PracticeShell.banner` — do not bury load errors only inside QuizCard.

---

### Task 4: `QaDock` + `LessonQaPanel` dock variant

**Files:**
- Create: `frontend/my-app/components/practice/QaDock.tsx`
- Modify: `frontend/my-app/components/lesson/LessonQaPanel.tsx`

**Interfaces:**
- Produces:
```ts
// QaDock
export function QaDock(props: {
  skillId: number;
  lessonTitle?: string;
}): JSX.Element;

// LessonQaPanel Props addition
variant?: "floating" | "dock"; // default "floating" for preview page
defaultOpen?: boolean; // when dock, default true and skip FAB
```

- [ ] **Step 1: Extend `LessonQaPanel`**

```ts
type Props = {
  skillId: number;
  lessonTitle?: string;
  demo?: DemoProps;
  variant?: "floating" | "dock";
};
```

When `variant === "dock"`:
- Render **panel only** (always open) — no FAB / no fixed bottom-right wrapper.
- Outer classes:
```tsx
"flex h-[min(70vh,640px)] w-full flex-col overflow-hidden rounded-[1.75rem] bg-white shadow-[0_12px_40px_rgba(42,36,56,0.06)] ring-1 ring-[#2A2438]/06"
```
- Restyle bubbles/header/composer to Promova ink/coral (replace `#2F3437`, `#EAEAEA`, `#F7F6F3`).
- Hide close button in dock (or keep Clear only).
- Composer control `min-h-11`.

When `variant === "floating"` (default): keep floating FAB behavior for `/dev/lesson-qa-preview`, but apply the same Promova color tokens.

- [ ] **Step 2: `QaDock`**

```tsx
"use client";

import LessonQaPanel from "@/components/lesson/LessonQaPanel";

export function QaDock({
  skillId,
  lessonTitle,
}: {
  skillId: number;
  lessonTitle?: string;
}) {
  return (
    <LessonQaPanel
      skillId={skillId}
      lessonTitle={lessonTitle}
      variant="dock"
    />
  );
}
```

- [ ] **Step 3: Verify preview** still works: open `/dev/lesson-qa-preview` — floating entry should remain available.

---

### Task 5: Restyle `LessonMiniUnit`

**Files:**
- Modify: `frontend/my-app/components/lesson/LessonMiniUnit.tsx`

**Interfaces:**
- Consumes / Produces: same `Props` as today (`embedded`, `onFinished`, etc.)

- [ ] **Step 1: Token pass** — replace gray Notion-like colors with Promova:
  - Body text `#2A2438` / muted `#6B6478` / subtle `#8A8396`
  - Borders `#EDE6E0`
  - Primary actions coral `#FF8A6B`
  - Secondary accents sky/violet sparingly
  - Keep step machine (`hook` → … → `exit`) unchanged

- [ ] **Step 2: When `embedded`**, show a compact title/objective at top of unit (shell no longer uses modal title bar):

```tsx
{embedded ? (
  <div className="mb-5 border-b border-[#EDE6E0] pb-4">
    {packLabel ? (
      <p className="text-[0.75rem] font-medium text-[#FF8A6B]">
        Part {packLabel}
      </p>
    ) : null}
    <h2 className="text-[1.25rem] font-semibold tracking-tight text-[#2A2438]">
      {title}
    </h2>
    {objective ? (
      <p className="mt-1 text-[0.875rem] text-[#8A8396]">{objective}</p>
    ) : null}
  </div>
) : null}
```

(Adjust if non-embedded already renders title — avoid duplicate headings.)

---

### Task 6: Wire `page.tsx`

**Files:**
- Modify: `frontend/my-app/src/app/dashboard/practice/[skillId]/page.tsx`

**Interfaces:**
- Consumes: `PracticeShell`, `QuizCard`, `QaDock`, `LessonMiniUnit`
- Does **not** import `LessonContentWindow`

- [ ] **Step 1: Keep all state + handlers** (`load`, `openPractice`, `handleLessonFinished`, `handleSubmit`, `goNext`, etc.) unchanged in behavior.

- [ ] **Step 2: Build `steps` array**

```ts
const steps: StepChip[] = hasLearn
  ? [
      {
        id: "learn",
        label: "Learn",
        detail:
          lessonMeta?.pack_total && lessonMeta.pack_total > 1
            ? `${lessonMeta.pack_completed_count ?? 0}/${lessonMeta.pack_total}`
            : undefined,
        state:
          phase === "learn" ? "active" : learnDone ? "done" : "upcoming",
      },
      {
        id: "practice",
        label: "Practice quiz",
        state: phase === "practice" ? "active" : "upcoming",
      },
      {
        id: "path",
        label: "Path",
        state: readyToComplete ? "done" : "upcoming",
      },
    ]
  : [
      {
        id: "practice",
        label: "Practice quiz",
        state: phase === "practice" ? "active" : "upcoming",
      },
      {
        id: "path",
        label: "Path",
        state: readyToComplete ? "done" : "upcoming",
      },
    ];
```

- [ ] **Step 3: Render with shell**

```tsx
return (
  <PracticeShell
    title={lessonMeta?.lesson?.title ?? "This week"}
    masteryPct={masteryPct}
    readyToComplete={readyToComplete}
    steps={steps}
    showSteps={hasLearn || questions.length > 0 || phase === "practice"}
    phase={phase === "learn" ? "learn" : "practice"}
    loading={loading}
    loadingLabel={
      phase === "learn" ? "Opening lesson…" : "Loading questions…"
    }
    banner={
      <>
        {error && !current && phase === "practice" ? (
          <div
            role="alert"
            className="mb-5 rounded-2xl bg-[#FFF0EE] px-4 py-3 text-[0.875rem] text-[#C24B3A] ring-1 ring-[#FF8A6B]/25"
          >
            {error}
          </div>
        ) : null}
        {showReviewLearn ? (
          <button
            type="button"
            className="mb-4 text-[0.875rem] font-medium text-[#7B6EF6] hover:text-[#6758E8]"
            onClick={() => setPhase("learn")}
          >
            Review lesson
          </button>
        ) : null}
        {phase === "learn" && lessonMeta?.can_skip ? (
          <button
            type="button"
            className="mb-4 text-[0.875rem] font-medium text-[#7B6EF6] hover:text-[#6758E8]"
            onClick={() => void openPractice()}
          >
            Skip to practice
          </button>
        ) : null}
      </>
    }
    lesson={
      phase === "learn" && lessonMeta?.lesson ? (
        completingLesson ? (
          <div className="flex items-center justify-center gap-2 py-16 text-[#8A8396]">
            <Loader2 className="h-5 w-5 animate-spin" />
            Saving progress…
          </div>
        ) : (
          <LessonMiniUnit
            key={`${lessonMeta.lesson.id}-${lessonMeta.lesson.pack_index ?? 0}`}
            skillId={skillId}
            title={lessonMeta.lesson.title}
            objective={lessonMeta.lesson.objective}
            content={lessonMeta.lesson.content}
            packIndex={lessonMeta.lesson.pack_index ?? 0}
            packLabel={
              lessonMeta.pack_total && lessonMeta.pack_total > 1
                ? `${(lessonMeta.pack_completed_count ?? 0) + 1}/${lessonMeta.pack_total}`
                : null
            }
            onFinished={() => void handleLessonFinished()}
            embedded
          />
        )
      ) : null
    }
    quiz={
      current ? (
        <QuizCard
          question={current}
          index={index}
          total={questions.length}
          answer={answer}
          onAnswerChange={(v) => {
            setAnswer(v);
            setError(null);
          }}
          feedback={
            feedback
              ? {
                  correct: feedback.correct,
                  explanation: feedback.explanation,
                }
              : null
          }
          submitting={submitting}
          error={error}
          readyToComplete={readyToComplete}
          onSubmit={() => void handleSubmit()}
          onNext={goNext}
          onBackToPath={() => router.push("/dashboard")}
        />
      ) : null
    }
    qa={
      phase === "learn" && lessonMeta?.lesson && !completingLesson ? (
        <QaDock
          skillId={skillId}
          lessonTitle={lessonMeta.lesson.title}
        />
      ) : null
    }
  />
);
```

- [ ] **Step 4: Manual verify**

1. Desktop `http://localhost:3000/dashboard/practice/270` — Learn: split columns; Q&A dock right; no modal overlay.
2. Finish / skip to practice — quiz Promova card; no Q&A.
3. Mobile 390px — stacked Learn then Q&A.
4. Mastery ≥70% — coral mastery pill + back to path CTA.
5. `/dev/lesson-qa-preview` — floating Q&A still usable.

---

### Task 7: Spec + light QC

**Files:**
- Modify: `docs/superpowers/specs/2026-08-05-practice-promova-redesign-design.md` status → Accepted
- Optional Playwright screenshots under ignored `.playwright-mcp/`

- [ ] **Step 1:** Mark spec Accepted; link this plan path in the spec header.
- [ ] **Step 2:** Spot-check against Impeccable craft floor mentally: no coral eyebrows as banned “marketing eyebrow” chips over h1; touch targets ≥ 44 on primary actions; fonts on ramp.
- [ ] **Step 3:** Do not commit unless user asks.

---

## Plan self-review

| Spec requirement | Task |
|------------------|------|
| Full UI + Q&A Promova | 3–6 |
| Desktop Learn split | 2, 6 |
| Mobile stack | 2 |
| Practice full-width quiz, hide Q&A | 2, 6 |
| Soft step chips + coral mastery | 1, 2 |
| Inline Learn / no modal on route | 6 |
| Approach B shells | 1–4 |
| Keep APIs / mastery 0.7 | 6 (handlers untouched) |
| Keep LessonContentWindow for preview | file map |

No TBD placeholders. Prop names: `StepChip`, `PracticeShell`, `QuizCard`, `QaDock`, `variant="dock"` consistent across tasks.

---

## Execution handoff

Plan complete and saved to `docs/superpowers/plans/2026-08-05-practice-promova-redesign.md`.

**Two execution options:**

1. **Subagent-Driven (recommended)** — fresh subagent per task, review between tasks  
2. **Inline Execution** — same session with executing-plans checkpoints  

Which approach?
