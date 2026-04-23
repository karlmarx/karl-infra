# Flight Connection Confidence (layover.93.fyi)

> Mobile-first tool for understanding flight layovers with data-backed reassurance

## Overview

| Field | Value |
|-------|-------|
| **URL** | [layover.93.fyi](https://layover.93.fyi) |
| **Tech** | Next.js 16 + React 19 + TypeScript, Tailwind CSS (light mode) |
| **Hosting** | Vercel (free tier, auto-deploy from main) |
| **Database** | None (static analysis + markdown research) |
| **Audience** | Elderly travelers anxious about tight connections |

## Features

- Interactive connection assessment (input airports + layover time)
- Success probability calculation (92–95% typical)
- Expandable detail cards (airport logistics, delay distributions, airline protections)
- Pre-trip action checklist (wheelchair assistance, TSA Cares, etc.)
- Full research references linked to primary sources
- Light mode, large fonts, mobile-first design
- Works offline after first load

## Architecture

**Frontend:** Single-page React app (no backend needed) with Tailwind CSS light mode. Mobile-first responsive design. Large touch targets (48px minimum) for accessibility.

**Data:** Analysis logic in `lib/analysis.ts` uses hardcoded delay distribution data and airport specs. Research markdown stored in `public/research.md`.

**Deployment:** Next.js auto-deploys from main branch. Vercel Functions (serverless) for any future API needs.

## Research Source

Full research document included in `/public/research.md`. Originally written by Claude analyzing Charlotte Douglas connections.
