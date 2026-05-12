# Karl's Infrastructure

> Auto-updated daily from GitHub commits. Last update: 2026-05-12

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
### mom-93fyi
- chore: add Twilio opt-in proof PNG (#26) (2026-05-10)
- feat: SMS link in bedbug shell + /consent page (#25) (2026-05-10)
- feat(bedbug): tap-to-text "Text Ben a question" link in app shell footer (#23) (2026-05-10)
- Add detail Mom can read on her own — morning, worried, why, timetable, bites, bigger Q&A (#22) (2026-05-10)
- chore: gitignore .env*.local (auto-added by vercel env pull) (2026-05-09)

### nwb-plan
- ci: auto-alias preview.nfit.93.fyi to latest non-main/non-dev branch deploy (#120) (2026-05-10)
- chore: trigger preview rebuild for AUTH_TRUST_HOST + NEXTAUTH_URL fix (2026-05-10)
- chore: trigger preview redeploy to pick up HEVY_API_KEY (2026-05-10)
- fix(hevy): server-side api key + admin auth gate (lost in PR #118 race) (#119) (2026-05-10)
- feat: picker copy + pwbpb link + hevy exercise audit tab (#118) (2026-05-10)

### karl-command-center
- data: vlm-status 2026-05-11T03:46 (2026-05-11)
- feat(status): VLM pipeline card with worker status + log tail (2026-05-10)
- data: vlm-status 2026-05-10T05:12 (2026-05-10)
- feat(status): priority-tiered grid order (2026-05-10)
- feat(status): per-app emoji + human label (2026-05-10)

### karl-infra
- chore: daily update 2026-05-11 (2026-05-11)
- chore: daily update 2026-05-10 (2026-05-10)
- docs: sync 93.fyi DNS state + command-center /status PWA (2026-05-09)
- infra(finflow): document hourly Teller sync LaunchAgent (staged, not loaded) (2026-05-09)
- feat: add pickleball-drills for pwbpb.93.fyi (2026-05-09)

### blazing-paddles-react
- ci: add Playwright regression suite, CI gate, and auto-merge (#18) (2026-05-10)
- Merge pull request #24 from karlmarx/Robb-Dev (2026-05-05)
- chore: update robots.txt to disallow access to /dl/ directory (2026-05-05)
- Merge pull request #23 from karlmarx/Robb-Dev (2026-05-05)
- chore: remove deprecated API endpoints and configuration files (2026-05-05)

### 93-fyi
- feat: add operator info to footer for Twilio TFV verification (2026-05-08)
- feat: link mom.93.fyi from apex (twilio review) (#2) (2026-05-01)
- feat(workoutgifs): add 5 new clips and PUSH/PULL/CARDIO sections (2026-04-25)
- fix: migrate subdomain rewrite to Next 16 proxy.ts (drop dead middleware.ts) (2026-04-25)
- fix: remove dead @site_url secret reference from vercel.json (2026-04-25)

### closet-bro
- feat: add concise mode (~half the tokens, same persona) (#2) (2026-05-07)
- Initial frat-bro plugin scaffold (#1) (2026-05-07)
- Initial commit (2026-05-07)
<!-- RECENT_CHANGES_END -->

## Future Plans

See [FUTURE.md](FUTURE.md) for the full roadmap.
