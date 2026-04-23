# Karl's Infrastructure

> Auto-updated daily from GitHub commits. Last update: 2026-04-23

## Overview

```
+-------------------------------------------------------------------+
|                      Karl's Infrastructure                        |
+-------------------------------------------------------------------+
|                                                                   |
|  APPS (Vercel)              AUTOMATION (Local / ultra.cc / CI)    |
|  ---------------            ----------------------------          |
|  nfit.93.fyi                Windows 11 Workstation                |
|  +- nwb-plan ----------+   +- OpenClaw (AI assistant)             |
|  |  (Next.js + Claude   |   +- claude-pipeline (watcher)          |
|  |   API suggestions)   |   |  +- watches Nextcloud/inbox/        |
|  |                      |   +- property-scout (daily 8am)         |
|  nyoga.93.fyi           |   |  +- MLS scrape -> email report      |
|  +- nwb-yoga ------+   |   |                                      |
|  |  (Canvas anims)  |   |   ultra.cc seedbox                      |
|  |                  |   |   +- find-hub-tracker                   |
|  foodr-app.vercel   |   |   |  +- Google Find Hub -> Postgres     |
|  +- foodr           |   |   |  +- Discord alerts                  |
|  |                  |   |   +- Nextcloud (WebDAV + file mirror)   |
|  ta.93.fyi          |   |                                         |
|  +- TrickAdvisor    |   |   GitHub Actions                        |
|     + TA-API        |   |   +- karl-todo (Todoist ->              |
|                     |   |                 todo.md + Nextcloud)    |
|  Supabase (DB) -----+   |                                         |
|                         |   INFRA                                 |
|  93.fyi ----------------+   ------                                |
|  (Cloudflare DNS)           Dynadot (.fyi registrar)              |
|  k@93.fyi -> Gmail          Cloudflare (DNS + email routing)      |
|                             GitHub (all repos + Actions)          |
|                             Vercel (all deployments)              |
|                             Anthropic (Claude API)                |
+-------------------------------------------------------------------+
```

See [ARCHITECTURE.md](ARCHITECTURE.md) for the full deep-dive.

## Live Services

| Service | URL | Stack | Repo |
|---------|-----|-------|------|
| NWB Fitness | [nfit.93.fyi](https://nfit.93.fyi) | Next.js 16 + React 19 + Claude API | [karlmarx/nwb-plan](https://github.com/karlmarx/nwb-plan) |
| NWB Yoga | [nyoga.93.fyi](https://nyoga.93.fyi) | React 18 + Vite + Canvas | [karlmarx/nwb-yoga](https://github.com/karlmarx/nwb-yoga) |
| foodr | [foodr-app.vercel.app](https://foodr-app.vercel.app) | Next.js 16 + React 19 | [karlmarx/foodr](https://github.com/karlmarx/foodr) |
| TrickAdvisor | [trickadvisor.cc](https://trickadvisor.cc) | React 19 + Supabase | [karlmarx/TrickAdvisor](https://github.com/karlmarx/TrickAdvisor) |
| TrickAdvisor API | (serverless) | Node/Express + Vercel Functions | [karlmarx/TrickAdvisor-API](https://github.com/karlmarx/TrickAdvisor-API) |
| Blazing Paddles | [blazingpaddles.org](https://blazingpaddles.org) | React (Vite) | [karlmarx/blazing-paddles-react](https://github.com/karlmarx/blazing-paddles-react) |

## Automation

| Service | Runs On | Status | Repo |
|---------|---------|--------|------|
| Find Hub Tracker | ultra.cc (systemd) | Deploying | [karlmarx/find-hub-tracker](https://github.com/karlmarx/find-hub-tracker) |
| Property Scout | Windows workstation (daily 8am ET) | Running | (in openclaw-watchdog) |
| Claude Pipeline | Windows workstation | Building | [karlmarx/claude-pipeline](https://github.com/karlmarx/claude-pipeline) |
| OpenClaw Watchdog | Windows workstation | Running | [karlmarx/openclaw-watchdog](https://github.com/karlmarx/openclaw-watchdog) |
| Gemini Auto | Windows workstation | Running | [karlmarx/gemini-auto](https://github.com/karlmarx/gemini-auto) |
| Amex Claims Automator | TBD | Scaffolded | [karlmarx/amex-claims-automator](https://github.com/karlmarx/amex-claims-automator) |
| karl-todo sync | GitHub Actions (on push to main) | Running | [karlmarx/karl-todo](https://github.com/karlmarx/karl-todo) |

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
| `ta.93.fyi` | CNAME | TrickAdvisor (deprecated, use trickadvisor.cc) |
| `k@93.fyi` | Email routing | karlmarx9193@gmail.com (Cloudflare) |

See [infra/domain-93fyi.md](infra/domain-93fyi.md) for full DNS details.

## Recent Changes

<!-- RECENT_CHANGES_START -->
### nwb-plan
- Merge pull request #78 from karlmarx/claude/add-prone-hip-extension-2K4jK (2026-04-20)
- Add-exercise picker: pull any catalog exercise into a workout (2026-04-18)
- Exercise card gear icon + render supersets as sibling cards (2026-04-18)
- Progress clock: tap to open detail panel with phases + timeline (2026-04-18)
- Simpler tab icons: barbell, up/down arrows, abs outline (2026-04-18)

### karl-infra
- chore: daily update 2026-04-22 (2026-04-22)
- chore: daily update 2026-04-21 (2026-04-21)
- chore: daily update 2026-04-20 (2026-04-20)
- chore: daily update 2026-04-19 (2026-04-19)
- chore: daily update 2026-04-18 (2026-04-18)

### 93-fyi
- fix: add middleware to route hot.93.fyi subdomain to /hot gallery (2026-04-21)
- feat: add hot.93.fyi aesthetic fitness gallery + private link (2026-04-21)
- fix: point sign-in link to me.93.fyi/login directly (2026-04-16)
- UI polish, a11y, and Next.js 16 housekeeping (#1) (2026-04-16)
- fix: add NWB Yoga to public links (2026-04-05)

### login-93fyi
- feat: branded login landing page (2026-04-20)

### progress-dashboard
- progress: Stage 3: 42579/109058 captions | Stage 4: 42575/109058 faces (2026-04-20)
- progress: Stage 3: 42579/109058 captions | Stage 4: 42575/109058 faces (2026-04-20)
- progress: Stage 3: 42579/109058 captions | Stage 4: 42575/109058 faces (2026-04-20)
- progress: Stage 3: 42579/109058 captions | Stage 4: 42575/109058 faces (2026-04-20)
- progress: Stage 3: 42579/109058 captions | Stage 4: 42575/109058 faces (2026-04-20)

### status-93fyi
- UX, a11y, and polling polish for status page (#1) (2026-04-16)
- docs: add deploy result (2026-04-03)
- init: status.93.fyi uptime page (2026-04-03)
- feat: add main status page with polling and components (2026-04-03)
- feat: add root layout with dark theme and Inter font (2026-04-03)
<!-- RECENT_CHANGES_END -->

## Future Plans

See [FUTURE.md](FUTURE.md) for the full roadmap.
