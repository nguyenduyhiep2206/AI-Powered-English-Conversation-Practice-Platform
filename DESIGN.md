---
version: alpha
name: EnglishFlow Lumingo Path
description: Warm peach learning-path UI inspired by Lumingo clear nodes — orange now, success green done, teal meta. Not Duolingo green gamification.
colors:
  canvas: "#FFF5EB"
  surface: "#FFFFFF"
  surface-soft: "#FFFAF5"
  ink: "#1F1B15"
  ink-muted: "#6B6258"
  ink-subtle: "#8A8178"
  primary: "#E85D04"
  primary-hover: "#D04F00"
  primary-soft: "#FFE8D6"
  on-primary-soft: "#9A3412"
  secondary: "#0D9488"
  secondary-soft: "#CCFBF1"
  on-secondary: "#115E59"
  success: "#2F9E44"
  success-soft: "#D8F3DC"
  border: "#E9D7C9"
  border-strong: "#D4C0AE"
  error: "#BE123C"
  error-soft: "#FFE4E6"
  atmosphere-orange: "rgba(232, 93, 4, 0.16)"
  atmosphere-teal: "rgba(13, 148, 136, 0.12)"
  locked: "#A89F94"
  locked-fill: "#F3EBE3"
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
  panel: "40px"
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
    rounded: "{rounded.lg}"
    height: "44px"
    padding: "0 24px"
  button-primary-hover:
    backgroundColor: "{colors.primary-hover}"
    textColor: "#FFFFFF"
  button-secondary:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.on-primary-soft}"
    rounded: "{rounded.lg}"
    height: "40px"
  input-default:
    backgroundColor: "{colors.surface-soft}"
    textColor: "{colors.ink}"
    rounded: "{rounded.xl}"
    height: "44px"
    padding: "0 14px"
  card-surface:
    backgroundColor: "{colors.surface}"
    rounded: "{rounded.panel}"
  chip-neutral:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.ink-muted}"
    rounded: "{rounded.xl}"
  path-node-active:
    backgroundColor: "{colors.primary}"
    textColor: "#FFFFFF"
    rounded: "999px"
  path-node-done:
    backgroundColor: "{colors.success}"
    textColor: "#FFFFFF"
    rounded: "999px"
  path-node-locked:
    backgroundColor: "{colors.locked-fill}"
    textColor: "{colors.locked}"
    rounded: "999px"
---

# EnglishFlow — Lumingo Path visual system

## Overview

EnglishFlow roadmap borrows **Lumingo's clear-node path**: warm peach canvas, vertical timeline with markers on the left and labels on the right, orange for the current step, success green for completed, teal for adaptive/meta chips. Keep Plus Jakarta Sans (not Inter). Not Duolingo green `#58CC02`, XP fire, or mascot-game chrome.

Stack: Next.js + shadcn/ui + Tailwind.

Taste dials for this surface: variance 7 / density 5 / motion 4.

## Colors

- **Canvas `#FFF5EB`:** Warm peach page wash.
- **Ink `#1F1B15`:** Near-black warm brown.
- **Primary orange `#E85D04`:** Current node + primary CTAs.
- **Success green `#2F9E44`:** Completed nodes + completed spine (not Duo green).
- **Teal `#0D9488`:** Adapted / ready / next-band chips.
- **Border `#E9D7C9`:** Soft warm panel edges.

## Layout

Product: header + `max-w-2xl` main. Roadmap lives in a large rounded panel (`~40px`). Path rows are `marker | copy` grids. Spine connects markers; green through completed stretch, warm border ahead.

## Components

- Circular path nodes with soft offset shadow.
- Active lesson opens a light warm sheet under the row label (not a dark dock).
- Badges: CEFR indigo-ish avoided; use teal/orange soft washes with readable ink.
- Secondary button: white with rust text `#9A3412`.

## Don't

- Snake/zigzag Duo path as default composition.
- Cool teal-slate Cool Atlas monoculture.
- Inter as the brand typeface.
- Exact Duolingo `#58CC02`.
