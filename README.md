# Karl's Infrastructure

> Auto-updated daily from GitHub commits. Last update: 2026-10-05

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
|  id.93.fyi          |   |                                         |
|  +- Identity Verif  |   |   GitHub Actions                        |
|     + ID-API        |   |   +- karl-todo (Todoist ->              |
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
| Identity Verification | [id.93.fyi](https://id.93.fyi) | React 19 + Supabase | [karlmarx/identity-verification](https://github.com/karlmarx/TrickAdvisor) |
| ID Verification API | (serverless) | Node/Express + Vercel Functions | [karlmarx/id-api](https://github.com/karlmarx/TrickAdvisor-API) |
| Blazing Paddles | [blazingpaddles.org](https://blazingpaddles.org) | React (Vite) | [karlmarx/blazing-paddles-react](https://github.com/karlmarx/blazing-paddles-react) |
| Roadmachine Gear Picks | [auto.93.fyi/roadmachine](https://auto.93.fyi/roadmachine) | Static HTML (served from auto-dashboard) | [karlmarx/karl-infra](https://github.com/karlmarx/karl-infra) (`/auto-dashboard/public/roadmachine/`) |
| LT Pro 48 Ball Proposal | [balls.93.fyi](https://balls.93.fyi) | Static HTML (Cloudflare Worker static assets, public via Access bypass) | [karlmarx/lt-pickleball](https://github.com/karlmarx/lt-pickleball) |

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
| [closet-bro](https://github.com/karlmarx/closet-bro) | Claude Code plugin: closeted-gay-frat-bro persona. `/plugin marketplace add karlmarx/closet-bro && /plugin install frat-bro@frat-bro` |

## Domain: 93.fyi

| Record | Type | Target |
|--------|------|--------|
| `93.fyi` | CNAME | nwb-plan (Vercel) — temporary |
| `nfit.93.fyi` | CNAME | nwb-plan (Vercel) |
| `nyoga.93.fyi` | CNAME | nwb-yoga (Vercel) |
| `id.93.fyi` | CNAME | Identity Verification API (primary) |
| `k@93.fyi` | Email routing | karlmarx9193@gmail.com (Cloudflare) |

See [infra/domain-93fyi.md](infra/domain-93fyi.md) for full DNS details.

## Recent Changes

<!-- RECENT_CHANGES_START -->
### drill-93fyi
- Add initial HTML structure and styles for Drill app (2026-10-05)
- Create index.html (2026-10-05)
- Add files via upload (2026-10-05)
- Add rewrites configuration to vercel.json (2026-10-05)
- Initial commit (2026-10-05)

### karl-infra
- Add CLAUDE.md: new 93.fyi sites default to Vercel (#27) (2026-10-05)
- README: add balls.93.fyi to live services (#26) (2026-10-05)
- chore: daily update 2026-10-04 (2026-10-04)
- chore: daily update 2026-10-03 (2026-10-03)
- chore: daily update 2026-10-02 (2026-10-02)

### lt-pickleball
- Pin wrangler 4 in deploy action (#7) (2026-10-05)
- Auto-deploy to Cloudflare; send all purchase traffic to Pickleball Central (#6) (2026-10-05)
- Buy section: link only to Pickleball Central (#5) (2026-10-05)
- Remove Franklin X-40 buy link; buy section is LT Pro 48 only (#4) (2026-10-05)
- Merge pull request #1 from karlmarx/ccr-160bd685-0j1r7v (2026-10-05)

### 93-fyi
- Add public subdomains to homepage links (#4) (2026-10-05)
- feat(hot): top-3 model comparison gallery (2026-05-16)
- revert: restore mailto link and drop phone from footer (2026-05-13)
- fix(footer): un-obfuscate email + add phone for Twilio TFV verifier (2026-05-12)
- feat: add operator info to footer for Twilio TFV verification (2026-05-08)
<!-- RECENT_CHANGES_END -->

## Future Plans

See [FUTURE.md](FUTURE.md) for the full roadmap.
