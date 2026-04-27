# Karl's Infrastructure

> Auto-updated daily from GitHub commits. Last update: 2026-04-27

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
- docs: add PWB Phase 4 exercise list draft for PT review (#97) (2026-04-26)
- chore: redeploy after dev DB env split (2026-04-25)
- chore: remove personal medical info; expand to 8 weeks; drop Hevy CTA (2026-04-25)
- chore: redeploy after Neon Postgres provisioning (2026-04-25)
- feat(mcp): expose exercise library to Claude via MCP server (#92) (2026-04-25)

### tui-dashboard
- fix: %-d strftime not supported on Windows (2026-04-02)
- refactor: strip to placeholder skeleton — get it running first (2026-04-02)
- feat: initial Textual dashboard — projects, lights, seedbox, agent, clock (2026-04-02)
- init: dashboard vision, panels, and ideas from session history (2026-04-02)

### karl-command-center
- Dynamic infra updates: Cloudflare/GitHub/Vercel integration (2026-04-26)
- Implement API routes and components (2026-04-25)
- Initial commit from Create Next App (2026-04-25)

### foodr
- Merge pull request #2 from karlmarx/claude/foodr-app-backend-security-iE0LQ (2026-04-26)
- Add Rust ratings backend and overhaul frontend visuals (2026-04-26)
- Merge pull request #1 from karlmarx/docs/readme (2026-03-28)
- Add comprehensive README (2026-03-28)
- Build Foodr: fast food rating app with chain-specific scales (2026-03-26)

### progress-dashboard
- Merge pull request #1 from karlmarx/refactor/shared-auth-migration (2026-04-26)
- progress: Stage 3: 42579/109058 captions | Stage 4: 42575/109058 faces (2026-04-20)
- progress: Stage 3: 42579/109058 captions | Stage 4: 42575/109058 faces (2026-04-20)
- progress: Stage 3: 42579/109058 captions | Stage 4: 42575/109058 faces (2026-04-20)
- progress: Stage 3: 42579/109058 captions | Stage 4: 42575/109058 faces (2026-04-20)

### karl-infra
- chore: daily update 2026-04-26 (2026-04-26)
- chore: daily update 2026-04-25 (2026-04-25)
- chore: daily update 2026-04-24 (2026-04-24)
- chore: daily update 2026-04-23 (2026-04-23)
- chore: daily update 2026-04-22 (2026-04-22)

### 93-fyi
- feat(workoutgifs): add 5 new clips and PUSH/PULL/CARDIO sections (2026-04-25)
- fix: migrate subdomain rewrite to Next 16 proxy.ts (drop dead middleware.ts) (2026-04-25)
- fix: remove dead @site_url secret reference from vercel.json (2026-04-25)
- feat: add /workoutgifs route and workoutgifs.93.fyi subdomain rewrite (2026-04-25)
- revert: remove misplaced equipment-gifs directory (2026-04-22)

### mom-93fyi
- refactor: trim sentimental framing, sign as Ben, reframe ID4 as Ben's car, add Google search (2026-04-23)
- feat: initial mom.93.fyi with handwritten letter aesthetic and 10 worry cards (2026-04-23)

### layover-93fyi
- feat: editorial redesign with vintage travel magazine aesthetic (2026-04-23)
- style: add colorful interactive diagrams (probability viz, delay chart, timeline, airport map) with richer color palette (2026-04-23)
- style: improve visual design with colored cards, better spacing, and enhanced typography for elderly audience (2026-04-23)
- feat: replace task checklist with reassuring what-if scenarios (2026-04-23)
- deploy: add Vercel configuration for production deployment (2026-04-23)

### login-93fyi
- feat: branded login landing page (2026-04-20)
<!-- RECENT_CHANGES_END -->

## Future Plans

See [FUTURE.md](FUTURE.md) for the full roadmap.
