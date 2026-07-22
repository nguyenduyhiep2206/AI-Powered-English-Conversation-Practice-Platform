# Frontend Light Theme (Minimalist) Design

**Date:** 2026-07-22  
**Status:** Approved  
**Scope:** `frontend/my-app` visual theme only — no API or business-logic changes

## Goal

Replace the forced dark UI with a permanent light theme following the project minimalist-ui skill: warm bone canvas, flat surfaces, semantic tokens, no gradients, no theme toggle.

## Decision

| Option | Description | Chosen |
|--------|-------------|--------|
| A | Strip `dark` only; keep default shadcn light tokens | No |
| B | Light + minimalist-ui palette (warm bone, `#EAEAEA` borders, muted pastels) | **Yes** |
| C | Light default + dark/light toggle (`next-themes`) | No |

## Design

### 1. CSS tokens (`src/app/globals.css`)

Update `:root` to minimalist light values:

| Token role | Value |
|------------|-------|
| Canvas / `--background` | `#F7F6F3` (warm bone) |
| Surfaces / `--card`, `--popover`, `--sidebar` | `#FFFFFF` |
| Foreground / primary text | `#111111` |
| Muted foreground | `#787774` |
| Borders / `--border`, `--input`, `--sidebar-border` | `#EAEAEA` |
| Primary (CTA fill) | `#111111` with foreground `#FFFFFF` |
| Secondary / muted / accent fills | Near-white warm grays (e.g. `#F9F9F8`) |
| Destructive | Keep existing readable red on light |

Rules:

- Do not force `.dark` as the app default.
- Keep existing `ef-fade-up` motion utilities.
- `.dark` block may remain unused for now (no toggle); do not wire it as the default theme.

### 2. Remove forced dark wrappers

Remove `className="dark"` (and loading-state equivalents) from page/layout roots, including:

- `src/app/login/page.tsx`
- `src/app/register/page.tsx`
- `src/app/dashboard/page.tsx`
- `src/app/dashboard/practice/[skillId]/page.tsx`
- `src/app/dashboard/level-challenge/page.tsx`
- `src/app/onboarding/page.tsx`
- `src/app/onboarding/placement/page.tsx`
- `src/app/start-onboarding/page.tsx`
- `src/app/admin/layout.tsx`

After this, pages rely on `:root` tokens via `bg-background` / `text-foreground`.

### 3. Replace hardcoded dark-only colors

Audit and replace hardcodes that break on light:

| Pattern | Replacement |
|---------|-------------|
| `text-white` on titles/brand | `text-foreground` |
| `ef-grad-hero` logo/hero blocks (undefined / dark-oriented) | Flat surface: white or primary `#111`, `border border-border`, no gradient |
| Translucent white badges on dark heroes | Semantic badge / outline styles readable on light |
| Admin sidebar brand `text-white` | `text-foreground` (or inverse only if sidebar stays dark — prefer light sidebar) |

Roadmap nodes (`WeekNode`, `RoadmapPath`): keep status semantics (completed / in progress / locked) but ensure contrast on light canvas (e.g. completed uses pale green pastel + dark green text per minimalist-ui, not low-opacity emerald on near-black).

### 4. Out of scope

- Theme toggle / `next-themes`
- Redesigning layout structure or copy
- Changing fonts beyond what tokens already use
- Backend, API, or auth changes

## Success criteria

1. App loads light by default on all major routes (auth, onboarding, dashboard, admin).
2. No root `className="dark"` wrappers remain on those routes.
3. Brand/headings remain readable (no white-on-bone text).
4. Borders and cards follow flat minimalist rules (≈`1px` light border, no heavy shadows/gradients).
5. Existing interactions (login, roadmap, practice, admin) still work; visual-only change.

## Implementation notes

- Prefer semantic Tailwind tokens (`bg-background`, `text-foreground`, `border-border`, `bg-card`) over one-off hex in JSX.
- Follow `.cursor/skills/minimalist-ui/SKILL.md` for palette and flat component constraints.
- Verify key screens visually after token + class updates: login, dashboard roadmap, start-onboarding hero, admin sidebar.
