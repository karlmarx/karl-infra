# NWB Fitness (nwb-plan)

> Femur fracture fitness PWA — exercise guide for non-weight-bearing recovery

## Overview

| Field | Value |
|-------|-------|
| **Repo** | [karlmarx/nwb-plan](https://github.com/karlmarx/nwb-plan) |
| **URLs** | [nfit.93.fyi](https://nfit.93.fyi), [93.fyi](https://93.fyi) (temp) |
| **Stack** | Single-file HTML PWA |
| **Hosting** | Vercel (free tier) |
| **Database** | None (fully client-side) |

## Architecture

- **Single HTML file** with all exercises, SVG diagrams, and styling embedded
- **Service Worker** for offline PWA support (cache versioned, currently v5)
- **No backend** — all data is static, embedded in HTML
- Animated SVG exercise diagrams (17+ core exercises)
- Responsive desktop scaling for readability
- Shared lotus flower SVG icon with nwb-yoga

## Recent Activity

- Added 17 core/arm/balance exercises with animated SVG diagrams
- Responsive desktop scaling
- Lotus flower SVG icon synced from nwb-yoga
- Service worker cache bumps for new content

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
