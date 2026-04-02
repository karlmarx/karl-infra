# NWB Fitness (nwb-plan)

> AI-powered femur fracture fitness PWA — exercise guide for non-weight-bearing recovery

## Overview

| Field | Value |
|-------|-------|
| **Repo** | [karlmarx/nwb-plan](https://github.com/karlmarx/nwb-plan) |
| **URLs** | [nfit.93.fyi](https://nfit.93.fyi), [93.fyi](https://93.fyi) (temp) |
| **Stack** | Next.js 16 + React 19 + TypeScript 6 + Tailwind CSS v4 |
| **Hosting** | Vercel (free tier) |
| **Database** | None (fully client-side, localStorage for preferences) |
| **AI** | Anthropic Claude API (`@anthropic-ai/sdk`) for exercise suggestions |
| **Auth** | NextAuth v5 (beta) |

## Architecture

- **Next.js 16 App Router** with Turbopack dev server (migrated from single-file HTML PWA)
- **67+ exercises** with safety constraints (zero active left hip flexor recruitment)
- **35+ animated SVG exercise diagrams** with inline animations
- **Claude API integration** for AI exercise suggestions (feature-flagged)
- **Equipment-aware superset system** — machine picker + nearby equipment detection
- **Service Worker** for offline PWA support
- **6-day PPL split** (Push/Pull/Legs) with A/B variants across 3 progression phases (Foundation / Build / Peak)
- Shared lotus flower SVG icon with nwb-yoga

## Recent Activity

- Migrated from single-file HTML to full Next.js 16 + React 19 + TypeScript stack
- Integrated Anthropic Claude API for AI exercise suggestions
- Built equipment-aware superset system with nearby picker
- Expanded from 17 to 67+ exercises with animated SVG diagrams
- Equipment picker logic fixes (PR #45)
- Wording improvements across codebase (PR #44)

## Open Issues

| # | Title |
|---|-------|
| [#34](https://github.com/karlmarx/nwb-plan/issues/34) | About modal with disclaimer |
| [#31](https://github.com/karlmarx/nwb-plan/issues/31) | Visual regression testing |
| [#21](https://github.com/karlmarx/nwb-plan/issues/21) | Migrate to Vite + React |
| [#20](https://github.com/karlmarx/nwb-plan/issues/20) | Dark/light theme toggle |
| [#19](https://github.com/karlmarx/nwb-plan/issues/19) | Share workout |
| [#18](https://github.com/karlmarx/nwb-plan/issues/18) | Phase timeline widget |
| [#17](https://github.com/karlmarx/nwb-plan/issues/17) | Cross-education progress tracker |
| [#16](https://github.com/karlmarx/nwb-plan/issues/16) | Volume tracker |
| [#15](https://github.com/karlmarx/nwb-plan/issues/15) | Workout log |
