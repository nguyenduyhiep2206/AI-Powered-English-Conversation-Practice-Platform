---
version: alpha
name: EnglishFlow Promova
description: Friendly language-learning product UI — soft pastels, coral accent, warm canvas. Not Duolingo gamification.
colors:
  canvas: "#FFF8F4"
  surface: "#FFFFFF"
  surface-soft: "#FFFCF9"
  ink: "#2A2438"
  ink-muted: "#6B6478"
  ink-subtle: "#8A8396"
  primary: "#FF8A6B"
  primary-hover: "#F47A5A"
  primary-soft: "#FFF0E8"
  secondary: "#8CC6E8"
  tertiary: "#7B6EF6"
  tertiary-hover: "#6758E8"
  lilac: "#C4B0E8"
  peach: "#FFD3A8"
  border: "#EDE6E0"
  border-strong: "#D9D0C8"
  error: "#C24B3A"
  error-soft: "#FFF0EE"
  atmosphere-coral: "rgba(255, 138, 107, 0.26)"
  atmosphere-sky: "rgba(140, 198, 232, 0.2)"
  atmosphere-coral-soft: "rgba(255, 164, 140, 0.35)"
  atmosphere-sky-soft: "rgba(140, 198, 232, 0.32)"
  atmosphere-lilac: "rgba(196, 176, 232, 0.18)"
  field-error: "#E07060"
  strength-mid: "#FFB38A"
  on-primary-soft: "#C45D42"
  on-secondary: "#3D7FA0"
  on-lilac: "#6B5B9A"
  locked: "#B0A9B8"
  ink-soft: "#5C5468"
typography:
  display-lg:
    fontFamily: "Plus Jakarta Sans, system-ui, sans-serif"
    fontSize: "2.75rem"
    fontWeight: 600
    lineHeight: 1.15
    letterSpacing: "-0.02em"
  display:
    fontFamily: "Plus Jakarta Sans, system-ui, sans-serif"
    fontSize: "2rem"
    fontWeight: 600
    lineHeight: 1.15
    letterSpacing: "-0.02em"
  headline:
    fontFamily: "Plus Jakarta Sans, system-ui, sans-serif"
    fontSize: "1.75rem"
    fontWeight: 600
    lineHeight: 1.2
    letterSpacing: "-0.01em"
  title:
    fontFamily: "Plus Jakarta Sans, system-ui, sans-serif"
    fontSize: "1.25rem"
    fontWeight: 600
    lineHeight: 1.3
  body:
    fontFamily: "Plus Jakarta Sans, system-ui, sans-serif"
    fontSize: "0.9375rem"
    fontWeight: 400
    lineHeight: 1.55
  label:
    fontFamily: "Plus Jakarta Sans, system-ui, sans-serif"
    fontSize: "0.8125rem"
    fontWeight: 500
    lineHeight: 1.4
  eyebrow:
    fontFamily: "Plus Jakarta Sans, system-ui, sans-serif"
    fontSize: "0.875rem"
    fontWeight: 500
    lineHeight: 1.3
  caption:
    fontFamily: "Plus Jakarta Sans, system-ui, sans-serif"
    fontSize: "0.75rem"
    fontWeight: 500
    lineHeight: 1.35
rounded:
  sm: "8px"
  md: "12px"
  lg: "16px"
  xl: "22px"
  2xl: "28px"
spacing:
  xs: "4px"
  sm: "8px"
  md: "16px"
  lg: "24px"
  xl: "36px"
  2xl: "48px"
components:
  button-primary:
    backgroundColor: "{colors.primary}"
    textColor: "#FFFFFF"
    rounded: "{rounded.xl}"
    height: "44px"
    padding: "0 24px"
  button-primary-hover:
    backgroundColor: "{colors.primary-hover}"
    textColor: "#FFFFFF"
  button-secondary:
    backgroundColor: "{colors.primary-soft}"
    textColor: "#C45D42"
    rounded: "{rounded.xl}"
    height: "40px"
  input-default:
    backgroundColor: "{colors.surface-soft}"
    textColor: "{colors.ink}"
    rounded: "{rounded.xl}"
    height: "44px"
    padding: "0 14px"
  card-surface:
    backgroundColor: "{colors.surface}"
    rounded: "{rounded.2xl}"
  chip-neutral:
    backgroundColor: "rgba(255,255,255,0.8)"
    textColor: "{colors.ink-muted}"
    rounded: "{rounded.xl}"
  path-node-active:
    backgroundColor: "{colors.primary}"
    textColor: "#FFFFFF"
    rounded: "{rounded.xl}"
  path-node-done:
    backgroundColor: "{colors.secondary}"
    textColor: "#FFFFFF"
    rounded: "{rounded.xl}"
  path-node-locked:
    backgroundColor: "{colors.surface}"
    textColor: "#B0A9B8"
    rounded: "{rounded.xl}"
---

# EnglishFlow — Promova visual system

## Overview

EnglishFlow is a **consumer language-learning product** (roadmap, practice, AI tutor). The visual world is Promova-inspired: warm cream canvas, coral primary, soft sky / lilac accents, generous radii, quiet soft elevation. It should feel friendly and approachable — not a Notion/Linear document tool, and **not** Duolingo green gamification (no XP bars, streak fire, or `#58CC02` as brand primary).

Stack: Next.js + **shadcn/ui + Tailwind**. Prefer restyling tokens and patterns over adding a second design system.

Agent workflow: use **Taste** (`design-taste-frontend`) when exploring/redesigning a screen’s vibe; use **Impeccable** (`/audit`, `/normalize`, `/polish`) to keep screens aligned with this file. Project rule: `.cursor/rules/promova-frontend-ui.mdc` (Taste dials 6 / 5 / 5).

Shipped reference surfaces: `/login`, `/register`, `/dashboard` (roadmap + `AppHeader`).

## Colors

Color strategy: **Restrained neutrals + committed coral accent**, with sky and violet as secondary/tertiary helpers.

- **Canvas (`#FFF8F4`):** Warm page background; soft coral/sky radial washes OK (not purple mesh AI defaults).
- **Surface (`#FFFFFF` / `#FFFCF9`):** Cards and form panels.
- **Ink (`#2A2438`):** Primary text; muted/subtle for secondary copy.
- **Primary coral (`#FF8A6B` / hover `#F47A5A`):** Brand mark, primary CTAs, in-progress path nodes, focus accents.
- **Sky (`#8CC6E8`):** Completed path nodes, “next level” chips, mastery-complete bars.
- **Violet (`#7B6EF6`):** Text links and secondary emphasis (not large purple gradients).
- **Lilac / peach:** Soft chips and decorative path accents only.
- **Error (`#C24B3A` on `#FFF0EE`):** Alerts and validation.

## Typography

**Plus Jakarta Sans** for UI and headlines (via `next/font`). No editorial serif heroes. Hierarchy leans on weight and size, not a second display family.

- Eyebrows/accents often use coral at ~14px medium.
- Page titles ~32px / 600; section titles ~20px / 600.
- Body ~15px with comfortable line-height (~1.55).

## Layout

Auth: split brand panel + form card on `md+`; stacked on mobile. Product: `AppHeader` + centered main (`max-w-3xl` roadmap). Roadmap path: vertical center rail with alternating node offset (left/right), current step centered.

Spacing rhythm ~8px base; section gaps ~36–48px. Density target: comfortable product density (Taste `VISUAL_DENSITY` 5).

## Elevation & Depth

Soft single-layer shadows, e.g. `0 18px 50px rgba(42,36,56,0.06–0.08)` on cards; coral CTA glow `0 10px 24px rgba(255,138,107,0.28)`. Prefer rings (`ring-1 ring-[#2A2438]/06`) over heavy multi-layer shadows. Atmosphere via soft radial washes on canvas, not glassmorphism everywhere.

## Shapes

Generous radii: inputs/buttons ~16–22px (`rounded-2xl`); cards/auth panels ~28px (`rounded-[1.75rem]` / `rounded-3xl`); path nodes soft **squircles** (`rounded-[1.35rem]`), not sharp rectangles. Avoid large pill chrome for primary marketing blocks; path nodes may stay rounded and friendly.

## Components

- **Primary button:** Coral fill, white text, height ~44px, soft coral shadow, slight `active:scale`.
- **Secondary / soft button:** Peach wash (`#FFF0E8`) with darker coral text.
- **Inputs:** Soft fill `#FFFCF9`, border `#EDE6E0`, focus border/ring coral.
- **Chips / badges:** White or pastel washes, large radius, light ring — CEFR / next-band metadata.
- **Header:** Coral “E” mark; active nav in coral; account menu soft violet/sky (no Duolingo green avatar).
- **Roadmap nodes:** Active coral + ring; done sky; locked white + muted icon. Mastery bar coral until ≥70%, then sky.
- **Errors:** Soft coral-tinted panels, not stark red rectangles with heavy borders.

## Do's and Don'ts

**Do**

- Match login / register / dashboard token language when adding product screens.
- Prefer transform + opacity motion; honor `prefers-reduced-motion`.
- Keep CTAs coral; links soft violet.
- Audit-first on redesigns: preserve flows, restyle chrome.

**Don't**

- Use Duolingo primary green `#58CC02`, XP/streak gamification chrome, or mascot-game heroes.
- Revive bone-flat minimalist/editorial (serif heroes, monochrome `#F7F6F3` + charcoal-only brand).
- Ship AI-default purple-to-indigo mesh heroes or three equal generic feature cards as the system.
- Mix Material / Fluent / Carbon into the tree alongside shadcn.
