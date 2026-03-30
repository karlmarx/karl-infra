# Karl's Infrastructure

> Auto-updated daily from GitHub commits. Last update: 2026-03-30

## Overview

```
+-------------------------------------------------------------------+
|                      Karl's Infrastructure                        |
+-------------------------------------------------------------------+
|                                                                   |
|  APPS (Vercel)              AUTOMATION (Local / ultra.cc)         |
|  ---------------            ----------------------------          |
|  nfit.93.fyi                Windows 11 Workstation                |
|  +- nwb-plan ----------+   +- OpenClaw (AI assistant)            |
|  |                      |   +- claude-pipeline (watcher)          |
|  nyoga.93.fyi           |   |  +- watches Nextcloud/inbox/       |
|  +- nwb-yoga ------+   |   |                                     |
|  |                  |   |   ultra.cc seedbox (planned)            |
|  ta.93.fyi          |   |   +- find-hub-tracker                  |
|  +- TrickAdvisor    |   |      +- polls Google Find Hub          |
|     + TA-API        |   |         +- Discord alerts              |
|                     |   |                                         |
|  Supabase (DB) -----+   |   INFRA                                |
|                         |   ------                                |
|  93.fyi ----------------+   Dynadot (.fyi registrar)              |
|  (Cloudflare DNS)           Cloudflare (DNS + email routing)      |
|  k@93.fyi -> Gmail          GitHub (all repos + Actions)          |
|                             Vercel (all deployments)              |
+-------------------------------------------------------------------+
```

See [ARCHITECTURE.md](ARCHITECTURE.md) for the full deep-dive.

## Live Services

| Service | URL | Stack | Repo |
|---------|-----|-------|------|
| NWB Fitness | [nfit.93.fyi](https://nfit.93.fyi) | Single-file HTML PWA | [karlmarx/nwb-plan](https://github.com/karlmarx/nwb-plan) |
| NWB Yoga | [nyoga.93.fyi](https://nyoga.93.fyi) | Single-file HTML PWA | [karlmarx/nwb-yoga](https://github.com/karlmarx/nwb-yoga) |
| TrickAdvisor | [ta.93.fyi](https://ta.93.fyi) | React + Supabase | [karlmarx/TrickAdvisor](https://github.com/karlmarx/TrickAdvisor) |
| TrickAdvisor API | (serverless) | Node/Express + Vercel Functions | [karlmarx/TrickAdvisor-API](https://github.com/karlmarx/TrickAdvisor-API) |
| Blazing Paddles | [blazingpaddles.org](https://blazingpaddles.org) | React (Vite) | [karlmarx/blazing-paddles-react](https://github.com/karlmarx/blazing-paddles-react) |

## Automation

| Service | Runs On | Status | Repo |
|---------|---------|--------|------|
| Find Hub Tracker | planned: ultra.cc | Building | [karlmarx/find-hub-tracker](https://github.com/karlmarx/find-hub-tracker) |
| Claude Pipeline | Windows workstation | Building | [karlmarx/claude-pipeline](https://github.com/karlmarx/claude-pipeline) |
| OpenClaw Watchdog | Windows workstation | Running | [karlmarx/openclaw-watchdog](https://github.com/karlmarx/openclaw-watchdog) |
| Gemini Auto | Windows workstation | Running | [karlmarx/gemini-auto](https://github.com/karlmarx/gemini-auto) |
| Amex Claims Automator | TBD | Scaffolded | [karlmarx/amex-claims-automator](https://github.com/karlmarx/amex-claims-automator) |

## Tooling & Docs

| Repo | Description |
|------|-------------|
| [karl-infra](https://github.com/karlmarx/karl-infra) | This repo — master architecture reference |
| [dev-setup](https://github.com/karlmarx/dev-setup) | Dev environment: Claude Code + Gemini CLI + Tailscale SSH |
| [todo-dashboard](https://github.com/karlmarx/todo-dashboard) | Dark-themed TODO dashboard (single HTML, opens on boot) |
| [google-migration-toolkit](https://github.com/karlmarx/google-migration-toolkit) | Google account migration scripts and tracking |

## Domain: 93.fyi

| Record | Type | Target |
|--------|------|--------|
| `93.fyi` | CNAME | nwb-plan (Vercel) — temporary |
| `nfit.93.fyi` | CNAME | nwb-plan (Vercel) |
| `nyoga.93.fyi` | CNAME | nwb-yoga (Vercel) |
| `ta.93.fyi` | CNAME | TrickAdvisor (Vercel) |
| `k@93.fyi` | Email routing | karlmarx9193@gmail.com (Cloudflare) |

See [infra/domain-93fyi.md](infra/domain-93fyi.md) for full DNS details.

## Recent Changes

<!-- RECENT_CHANGES_START -->
### TrickAdvisor
- feat: LoadRating component with splat icons (2026-03-29)
- Load rating icon assets: SVG + PNG variants (2026-03-28)
- Add CLAUDE.md for AI context (2026-03-28)

### TrickAdvisor-API
- Add CLAUDE.md for AI context (2026-03-28)
- Fire-and-forget admin photo email to avoid timeout (2026-03-27)
- Email user when photo is approved or rejected (2026-03-27)

### nwb-plan
- feat: lotus flower SVG icon (synced from nwb-yoga) (2026-03-29)
- feat: responsive desktop scaling for readability (2026-03-29)
- feat: wire up animated SVG diagrams for all 17 new core exercises (2026-03-29)

### nwb-yoga
- feat: lotus flower SVG icon with warm terracotta and dark green mono version (2026-03-29)
- improve: self-contained descriptions, better animations (2026-03-26)

### find-hub-tracker
- feat: initial scaffold — Google Find Hub tracker with Discord integration (2026-03-30)

### claude-pipeline
- feat: initial claude-pipeline implementation (2026-03-30)

### openclaw-watchdog
- fix: swap AI order — Gemini first, DeepSeek fallback (2026-03-25)
- feat: Playwright JS rendering, DeepSeek scoring, Discord webhook notifications (2026-03-25)
<!-- RECENT_CHANGES_END -->

## Future Plans

See [FUTURE.md](FUTURE.md) for the full roadmap.
