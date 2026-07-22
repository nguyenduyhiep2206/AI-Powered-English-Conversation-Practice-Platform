# Frontend Light Theme (Minimalist) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Convert `frontend/my-app` from forced dark UI to a permanent warm-bone light theme (minimalist-ui), with no theme toggle.

**Architecture:** Update CSS design tokens in `globals.css` `:root`, remove every page-level `className="dark"` wrapper, then replace hardcoded dark-only colors (`text-white`, `ef-grad-hero`, translucent white badges, low-contrast emerald) with semantic light-readable classes. No `next-themes`, no API changes.

**Tech Stack:** Next.js 16 App Router, React 19, Tailwind CSS 4, shadcn/ui tokens, project skill `.cursor/skills/minimalist-ui/SKILL.md`.

**Spec:** `docs/superpowers/specs/2026-07-22-frontend-light-theme-design.md`

## Global Constraints

- Visual-only — no backend, API, or auth logic changes.
- No theme toggle / `next-themes`.
- Palette: canvas `#F7F6F3`, surfaces `#FFFFFF`, text `#111111`, muted `#787774`, borders `#EAEAEA`, primary CTA `#111111` on `#FFFFFF`.
- No gradients on heroes/logos; flat borders only.
- Prefer semantic tokens (`bg-background`, `text-foreground`, `border-border`, `bg-card`) over one-off hex in JSX.
- Keep `ef-fade-up` motion utilities unchanged.
- `.dark` CSS block may remain unused; do not apply it as default.

---

## File map

| File | Responsibility |
|------|----------------|
| `frontend/my-app/src/app/globals.css` | Minimalist light `:root` tokens |
| `frontend/my-app/src/app/login/page.tsx` | Remove `dark` wrapper |
| `frontend/my-app/src/app/register/page.tsx` | Remove `dark` wrapper |
| `frontend/my-app/src/app/dashboard/page.tsx` | Remove `dark`; fix `text-white` |
| `frontend/my-app/src/app/dashboard/practice/[skillId]/page.tsx` | Remove `dark`; fix correct-feedback colors |
| `frontend/my-app/src/app/dashboard/level-challenge/page.tsx` | Remove `dark` wrappers |
| `frontend/my-app/src/app/onboarding/page.tsx` | Remove `dark`; clean logo classes |
| `frontend/my-app/src/app/onboarding/placement/page.tsx` | Remove `dark`; clean logo classes |
| `frontend/my-app/src/app/start-onboarding/page.tsx` | Remove `dark`; restyle hero for light |
| `frontend/my-app/src/app/admin/layout.tsx` | Remove `dark` wrappers |
| `frontend/my-app/components/admin/AdminSidebar.tsx` | Light brand text + logo |
| `frontend/my-app/components/roadmap/WeekNode.tsx` | Pastel completed/mastery contrast on light |

---

### Task 1: Update light design tokens

**Files:**
- Modify: `frontend/my-app/src/app/globals.css` (`:root` block only)
- Test: grep + visual smoke (no unit test harness for CSS tokens)

**Interfaces:**
- Consumes: Spec token table
- Produces: `:root` CSS variables used by all `bg-background` / `text-foreground` / etc. consumers

- [ ] **Step 1: Replace the `:root` block** with minimalist light hex values (keep `.dark` block and `ef-fade-up` as-is):

```css
:root {
  --background: #F7F6F3;
  --foreground: #111111;
  --card: #FFFFFF;
  --card-foreground: #111111;
  --popover: #FFFFFF;
  --popover-foreground: #111111;
  --primary: #111111;
  --primary-foreground: #FFFFFF;
  --secondary: #F9F9F8;
  --secondary-foreground: #111111;
  --muted: #F9F9F8;
  --muted-foreground: #787774;
  --accent: #F9F9F8;
  --accent-foreground: #111111;
  --destructive: oklch(0.577 0.245 27.325);
  --border: #EAEAEA;
  --input: #EAEAEA;
  --ring: #787774;
  --chart-1: #111111;
  --chart-2: #787774;
  --chart-3: #346538;
  --chart-4: #1F6C9F;
  --chart-5: #956400;
  --radius: 0.625rem;
  --sidebar: #FFFFFF;
  --sidebar-foreground: #111111;
  --sidebar-primary: #111111;
  --sidebar-primary-foreground: #FFFFFF;
  --sidebar-accent: #F9F9F8;
  --sidebar-accent-foreground: #111111;
  --sidebar-border: #EAEAEA;
  --sidebar-ring: #787774;
}
```

- [ ] **Step 2: Verify tokens are present**

Run from repo root:

```bash
rg -n -- "--background: #F7F6F3|--muted-foreground: #787774|--border: #EAEAEA" frontend/my-app/src/app/globals.css
```

Expected: three matching lines inside `:root`.

- [ ] **Step 3: Commit**

```bash
git add frontend/my-app/src/app/globals.css
git commit -m "$(cat <<'EOF'
style: set minimalist warm-bone light design tokens

EOF
)"
```

---

### Task 2: Remove forced `dark` wrappers from all routes

**Files:**
- Modify: `frontend/my-app/src/app/login/page.tsx`
- Modify: `frontend/my-app/src/app/register/page.tsx`
- Modify: `frontend/my-app/src/app/dashboard/page.tsx`
- Modify: `frontend/my-app/src/app/dashboard/practice/[skillId]/page.tsx`
- Modify: `frontend/my-app/src/app/dashboard/level-challenge/page.tsx`
- Modify: `frontend/my-app/src/app/onboarding/page.tsx`
- Modify: `frontend/my-app/src/app/onboarding/placement/page.tsx`
- Modify: `frontend/my-app/src/app/start-onboarding/page.tsx`
- Modify: `frontend/my-app/src/app/admin/layout.tsx`

**Interfaces:**
- Consumes: Task 1 `:root` light tokens
- Produces: Pages that inherit light theme without `.dark` ancestor

- [ ] **Step 1: Strip `dark` from each root/loading wrapper**

In every file above, change wrappers like:

```tsx
<div className="dark min-h-screen bg-background text-foreground">
```

and

```tsx
<div className="dark flex min-h-screen items-center justify-center bg-background">
```

to the same classes **without** the `dark` token, e.g.:

```tsx
<div className="min-h-screen bg-background text-foreground">
```

```tsx
<div className="flex min-h-screen items-center justify-center bg-background">
```

Exact current occurrences to edit (one pass with search-replace is fine):

| File | Pattern count |
|------|---------------|
| `login/page.tsx` | 1 |
| `register/page.tsx` | 1 |
| `dashboard/page.tsx` | 1 |
| `dashboard/practice/[skillId]/page.tsx` | 1 |
| `dashboard/level-challenge/page.tsx` | 2 |
| `onboarding/page.tsx` | 2 |
| `onboarding/placement/page.tsx` | 2 |
| `start-onboarding/page.tsx` | 1 |
| `admin/layout.tsx` | 2 |

- [ ] **Step 2: Verify no route-level forced dark remains**

```bash
rg -n 'className="[^"]*\bdark\b' frontend/my-app/src/app --glob '*.tsx'
```

Expected: **no matches** (shadcn `dark:` utility variants inside `components/ui/*` are OK and are outside this path).

- [ ] **Step 3: Commit**

```bash
git add \
  frontend/my-app/src/app/login/page.tsx \
  frontend/my-app/src/app/register/page.tsx \
  frontend/my-app/src/app/dashboard/page.tsx \
  frontend/my-app/src/app/dashboard/practice/\[skillId\]/page.tsx \
  frontend/my-app/src/app/dashboard/level-challenge/page.tsx \
  frontend/my-app/src/app/onboarding/page.tsx \
  frontend/my-app/src/app/onboarding/placement/page.tsx \
  frontend/my-app/src/app/start-onboarding/page.tsx \
  frontend/my-app/src/app/admin/layout.tsx
git commit -m "$(cat <<'EOF'
style: remove forced dark class wrappers from app routes

EOF
)"
```

---

### Task 3: Fix hardcoded brand / hero colors for light

**Files:**
- Modify: `frontend/my-app/src/app/dashboard/page.tsx`
- Modify: `frontend/my-app/src/app/start-onboarding/page.tsx`
- Modify: `frontend/my-app/src/app/onboarding/page.tsx`
- Modify: `frontend/my-app/src/app/onboarding/placement/page.tsx`
- Modify: `frontend/my-app/components/admin/AdminSidebar.tsx`

**Interfaces:**
- Consumes: Light tokens + pages without `.dark`
- Produces: Readable brand/hero on warm bone canvas

- [ ] **Step 1: Dashboard brand + title**

In `frontend/my-app/src/app/dashboard/page.tsx`, replace:

```tsx
<span className="font-semibold tracking-tight text-white">
  EnglishFlow
</span>
```

with:

```tsx
<span className="font-semibold tracking-tight text-foreground">
  EnglishFlow
</span>
```

and:

```tsx
<h1 className="mt-1.5 text-3xl font-semibold tracking-tight text-white">
  Weekly roadmap
</h1>
```

with:

```tsx
<h1 className="mt-1.5 text-3xl font-semibold tracking-tight text-foreground">
  Weekly roadmap
</h1>
```

Logo mark can stay `bg-white` + `text-black` icon, optionally add `border border-border`:

```tsx
<div className="flex h-8 w-8 items-center justify-center rounded-lg border border-border bg-white">
  <Sparkles className="h-4 w-4 text-black" />
</div>
```

- [ ] **Step 2: Start-onboarding header + hero**

In `frontend/my-app/src/app/start-onboarding/page.tsx`:

1. Header logo: remove `ef-grad-hero`; brand text `text-white` → `text-foreground`.
2. Replace the hero block (currently `ef-grad-hero` + `text-white`) with a flat light header:

```tsx
<div className="flex flex-col items-center gap-4 border-b border-border bg-card px-8 py-10 text-center md:px-12 md:py-12">
  <div className="flex h-16 w-16 items-center justify-center rounded-xl border border-border bg-secondary">
    <RouteIcon className="h-8 w-8 text-foreground" strokeWidth={2} />
  </div>
  <Badge variant="outline" className="gap-1.5">
    <Clock className="h-3 w-3" />
    ~5–7 min
  </Badge>
  <h1 className="max-w-xl text-3xl font-semibold tracking-tight text-foreground md:text-4xl">
    {isContinue ? "Continue your setup" : "Let's build your personalized English plan!"}
  </h1>
  <p className="max-w-lg text-sm text-muted-foreground md:text-base">
    {isContinue
      ? "Pick up right where you left off — we saved your progress."
      : "A quick survey, then a short placement test — so we can place you at the right CEFR level and generate your roadmap."}
  </p>
</div>
```

Also remove `shadow-md` from the outer card if present (`ef-card ... shadow-md`) — use `border border-border bg-card` only (minimalist flat).

- [ ] **Step 3: Onboarding + placement logos**

In `onboarding/page.tsx` and `onboarding/placement/page.tsx`, change logo marks from:

```tsx
<div className="ef-grad-hero flex h-8 w-8 items-center justify-center rounded-lg bg-white">
```

to:

```tsx
<div className="flex h-8 w-8 items-center justify-center rounded-lg border border-border bg-white">
```

(Brand text on these pages already uses default foreground — leave as-is.)

- [ ] **Step 4: Admin sidebar brand**

In `frontend/my-app/components/admin/AdminSidebar.tsx`:

```tsx
<div className="flex h-8 w-8 items-center justify-center rounded-lg border border-border bg-white">
  <Sparkles className="h-4 w-4 text-black" />
</div>
...
<p className="truncate text-sm font-semibold text-foreground">EnglishFlow</p>
```

- [ ] **Step 5: Verify hardcodes gone**

```bash
rg -n 'text-white|ef-grad-hero' frontend/my-app --glob '*.{tsx,css}'
```

Expected: **no matches**.

- [ ] **Step 6: Commit**

```bash
git add \
  frontend/my-app/src/app/dashboard/page.tsx \
  frontend/my-app/src/app/start-onboarding/page.tsx \
  frontend/my-app/src/app/onboarding/page.tsx \
  frontend/my-app/src/app/onboarding/placement/page.tsx \
  frontend/my-app/components/admin/AdminSidebar.tsx
git commit -m "$(cat <<'EOF'
style: replace dark-only brand and hero colors for light theme

EOF
)"
```

---

### Task 4: Light-friendly status / feedback pastels

**Files:**
- Modify: `frontend/my-app/components/roadmap/WeekNode.tsx`
- Modify: `frontend/my-app/src/app/dashboard/practice/[skillId]/page.tsx`

**Interfaces:**
- Consumes: Light canvas from Tasks 1–3
- Produces: Completed/mastery/correct states readable on warm bone

- [ ] **Step 1: WeekNode completed + mastery bar**

In `WeekNode.tsx`, replace completed node classes:

```tsx
week.status === "completed" &&
  "border-[#346538]/30 bg-[#EDF3EC] text-[#346538]",
```

and mastery fill when ≥ 70%:

```tsx
masteryPct >= 70 ? "bg-[#346538]" : "bg-primary",
```

Also prefer solid card surface on light:

```tsx
"mt-4 w-full rounded-xl border bg-card px-5 py-4 text-left transition-colors",
```

(and keep `border-primary/40` vs `border-border` status logic).

- [ ] **Step 2: Practice correct feedback**

In `practice/[skillId]/page.tsx`, replace correct branch:

```tsx
feedback.correct
  ? "border-[#346538]/30 bg-[#EDF3EC] text-[#346538]"
  : "border-destructive/40 bg-destructive/10 text-destructive"
```

- [ ] **Step 3: Verify no light-on-dark emerald leftovers in these files**

```bash
rg -n 'emerald-200|emerald-300|text-white' \
  frontend/my-app/components/roadmap/WeekNode.tsx \
  frontend/my-app/src/app/dashboard/practice
```

Expected: **no matches**. (`text-emerald-500` on register checkmarks is fine — already readable on light.)

- [ ] **Step 4: Commit**

```bash
git add \
  frontend/my-app/components/roadmap/WeekNode.tsx \
  frontend/my-app/src/app/dashboard/practice/\[skillId\]/page.tsx
git commit -m "$(cat <<'EOF'
style: use muted pastels for roadmap and practice status on light

EOF
)"
```

---

### Task 5: Visual verification checklist

**Files:** none (verification only)

- [ ] **Step 1: Static audit**

```bash
rg -n 'className="[^"]*\bdark\b' frontend/my-app/src/app --glob '*.tsx'
rg -n 'text-white|ef-grad-hero' frontend/my-app --glob '*.{tsx,css}'
rg -n '--background: #F7F6F3' frontend/my-app/src/app/globals.css
```

Expected: first two empty; third matches.

- [ ] **Step 2: Manual smoke (dev server)**

Run:

```bash
cd frontend/my-app && npm run dev
```

Open and confirm warm bone canvas + readable text on:

1. `/login`
2. `/dashboard` (brand + roadmap nodes)
3. `/start-onboarding` (hero no white-on-dark)
4. `/admin` (sidebar brand)

- [ ] **Step 3: Mark spec status** (optional small doc edit)

In `docs/superpowers/specs/2026-07-22-frontend-light-theme-design.md`, set `Status: Implemented` when smoke passes, then commit:

```bash
git add docs/superpowers/specs/2026-07-22-frontend-light-theme-design.md
git commit -m "$(cat <<'EOF'
docs: mark light theme design as implemented

EOF
)"
```

---

## Spec coverage self-check

| Spec requirement | Task |
|------------------|------|
| `:root` warm-bone tokens | Task 1 |
| Keep `ef-fade-up`; leave `.dark` unused | Task 1 |
| Remove `className="dark"` on listed routes | Task 2 |
| `text-white` → `text-foreground` | Task 3 |
| Flat `ef-grad-hero` / hero badges | Task 3 |
| Admin sidebar light brand | Task 3 |
| Roadmap pastel contrast | Task 4 |
| No toggle / no API changes | Global + all tasks |
| Success criteria verification | Task 5 |
