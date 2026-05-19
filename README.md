# Karl's Infrastructure

> Auto-updated daily from GitHub commits. Last update: 2026-05-19

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
### karl-infra
- chore: daily update 2026-05-18 (2026-05-18)
- chore: daily update 2026-05-17 (2026-05-17)
- chore: daily update 2026-05-16 (2026-05-16)
- chore: daily update 2026-05-15 (2026-05-15)
- chore: daily update 2026-05-14 (2026-05-14)

### suspect-game
- Initial commit: SUSPECT word bluffing game (2026-05-17)

### 93-fyi
- feat(hot): top-3 model comparison gallery (2026-05-16)
- revert: restore mailto link and drop phone from footer (2026-05-13)
- fix(footer): un-obfuscate email + add phone for Twilio TFV verifier (2026-05-12)
- feat: add operator info to footer for Twilio TFV verification (2026-05-08)
- feat: link mom.93.fyi from apex (twilio review) (#2) (2026-05-01)

### karl-command-center
- feat(triage): /triage dashboard reads from Supabase (#2) (2026-05-12)
- data: vlm-status 2026-05-12T04:31 (2026-05-12)
- data: vlm-status 2026-05-11T03:46 (2026-05-11)
- feat(status): VLM pipeline card with worker status + log tail (2026-05-10)
- data: vlm-status 2026-05-10T05:12 (2026-05-10)

### mom-93fyi
- feat(proxy): serve karlmarxindustries.com landing from Vercel (2026-05-15)
- chore(bedbug): drop picture-sending refs, route everything to chat (2026-05-13)
- chore(bedbug): stop telling mom to text Ben — route to chat + email (2026-05-13)
- chore(bedbug): remove unused sms import from AppShell (2026-05-13)
- fix(ask): include actual content changes lost in the previous rename (2026-05-13)

### karlmarx.github.io
- Add .nojekyll to skip Jekyll on static-HTML deploy (2026-05-15)
- Replace SPA shell with Karl Marx Industries landing page (2026-05-15)
- Create CNAME (2024-05-06)
- Updates (2024-03-31)
- Updates (2024-03-06)

### nwb-plan
- ci: run Playwright on every push (not just main/dev) (#128) (2026-05-13)
- fix(swap): group machine variants by own equipment, not parent's (#127) (2026-05-13)
- ci: auto-alias preview.nfit.93.fyi to latest non-main/non-dev branch deploy (#120) (2026-05-10)
- chore: trigger preview rebuild for AUTH_TRUST_HOST + NEXTAUTH_URL fix (2026-05-10)
- chore: trigger preview redeploy to pick up HEVY_API_KEY (2026-05-10)
<!-- RECENT_CHANGES_END -->

## Future Plans

See [FUTURE.md](FUTURE.md) for the full roadmap.
