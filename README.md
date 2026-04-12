# Karl's Infrastructure

> Auto-updated daily from GitHub commits. Last update: 2026-04-12

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
|  |  (Next.js + Claude   |   +- claude-pipeline (watcher)          |
|  |   API suggestions)   |   |  +- watches Nextcloud/inbox/       |
|  |                      |   +- property-scout (daily 8am)         |
|  nyoga.93.fyi           |   |  +- MLS scrape -> email report     |
|  +- nwb-yoga ------+   |   |                                     |
|  |  (Canvas anims)  |   |   ultra.cc seedbox                     |
|  |                  |   |   +- find-hub-tracker                  |
|  foodr-app.vercel   |   |      +- Google Find Hub -> Postgres    |
|  +- foodr           |   |         +- Discord alerts              |
|  |                  |   |         +- healthchecks.io              |
|  ta.93.fyi          |   |                                         |
|  +- TrickAdvisor    |   |   INFRA                                |
|     + TA-API        |   |   ------                                |
|                     |   |   Dynadot (.fyi registrar)              |
|  Supabase (DB) -----+   |   Cloudflare (DNS + email routing)      |
|                         |   GitHub (all repos + Actions)          |
|  93.fyi ----------------+   Vercel (all deployments)              |
|  (Cloudflare DNS)           Anthropic (Claude API)                |
|  k@93.fyi -> Gmail                                                |
+-------------------------------------------------------------------+
```

See [ARCHITECTURE.md](ARCHITECTURE.md) for the full deep-dive.

## Live Services

| Service | URL | Stack | Repo |
|---------|-----|-------|------|
| NWB Fitness | [nfit.93.fyi](https://nfit.93.fyi) | Next.js 16 + React 19 + Claude API | [karlmarx/nwb-plan](https://github.com/karlmarx/nwb-plan) |
| NWB Yoga | [nyoga.93.fyi](https://nyoga.93.fyi) | React 18 + Vite + Canvas | [karlmarx/nwb-yoga](https://github.com/karlmarx/nwb-yoga) |
| foodr | [foodr-app.vercel.app](https://foodr-app.vercel.app) | Next.js 16 + React 19 | [karlmarx/foodr](https://github.com/karlmarx/foodr) |
| TrickAdvisor | [ta.93.fyi](https://ta.93.fyi) | React + Supabase | [karlmarx/TrickAdvisor](https://github.com/karlmarx/TrickAdvisor) |
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
### blazing-paddles-react
- chore: clean up DatePicker.tsx — remove dead code, fix types (#16) (2026-04-11)
- chore: test deploy after removing duplicate Vercel project (2026-03-17)
- Merge pull request #9 from karlmarx/add-claude-github-actions-1773782965672 (2026-03-17)
- "Claude Code Review workflow" (2026-03-17)
- "Claude PR Assistant workflow" (2026-03-17)

### nwb-plan
- Merge pull request #64 from karlmarx/claude/add-supersets-focus-mode-NWm83 (2026-04-10)
- feat: add supersets and supplements to Focus Mode overlay (2026-04-10)
- fix: replace yoga lotus favicon with NWB dumbbell mark (2026-04-08)
- Merge branch 'main' into dev (2026-04-07)
- feat(ui-v2): enable new UI by default (2026-04-07)

### karl-infra
- chore: daily update 2026-04-11 (2026-04-11)
- chore: daily update 2026-04-10 (2026-04-10)
- chore: daily update 2026-04-09 (2026-04-09)
- chore: daily update 2026-04-08 (2026-04-08)
- chore: daily update 2026-04-07 (2026-04-07)

### house-tracker
- feat: add kitchen renovation concept renders for 3497 NE 20th Ave (2026-04-06)
- feat: add Gemini-generated pool concept renders (2026-04-06)
- fix: improve site plan readability on mobile (2026-04-05)
- feat: add interactive pool site plans and deeper analysis sections (2026-04-05)
- feat: house-tracker — South Florida property comparison dashboard (2026-04-05)

### 93-fyi
- fix: add NWB Yoga to public links (2026-04-05)
- fix: sign-in redirects to me.93.fyi after CF Access login (2026-04-05)
- remove debug endpoint (2026-04-05)
- add debug endpoint (2026-04-05)
- server component with personalized links via X-User-Email header (2026-04-05)
<!-- RECENT_CHANGES_END -->

## Future Plans

See [FUTURE.md](FUTURE.md) for the full roadmap.
