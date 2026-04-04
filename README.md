# Karl's Infrastructure

> Auto-updated daily from GitHub commits. Last update: 2026-04-04

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
### now-93fyi
- copy: cut yoga line (2026-04-03)
- copy: cut humidity line (2026-04-03)
- copy: tighter voice, less explaining (2026-04-03)
- copy: grounded building section — real backstory, less manifesto (2026-04-03)
- copy: remove 'The light is good' (2026-04-03)

### 93-fyi
- fix: correct SSO cookie name, add sign in link for logged-out state (2026-04-03)
- feat: new favicon from gemini (2026-04-03)
- redesign: calm minimal homepage with serif/mono typography (2026-04-03)
- fix: move TrickAdvisor to private (auth-gated), remove footer quote (2026-04-03)
- redesign: sleek link hub with SVG icons, auth-gated private links (2026-04-03)

### status-93fyi
- docs: add deploy result (2026-04-03)
- init: status.93.fyi uptime page (2026-04-03)
- feat: add main status page with polling and components (2026-04-03)
- feat: add root layout with dark theme and Inter font (2026-04-03)
- feat: add IncidentHistory component (2026-04-03)

### nwb-plan
- fix: move superset cards to top of expanded exercise via supplementSlot prop (#48) (2026-04-03)
- fix: superset system — exercise name mismatches, render order, equipment awareness (#48) (2026-04-03)
- fix: show superset badges in both collapsed and expanded exercise tiles (2026-04-03)
- Merge pull request #46 from karlmarx/diagram-gallery (2026-04-02)
- merge: resolve lotus icon conflict with main (take main's single-path version) (2026-04-02)

### karl-infra
- chore: daily update 2026-04-03 (2026-04-03)
- feat: update infra docs with current project state (2026-04-02)
- chore: daily update 2026-04-02 (2026-04-02)
- chore: daily update 2026-04-01 (2026-04-01)
- chore: daily update 2026-03-31 (2026-03-31)

### tui-dashboard
- fix: %-d strftime not supported on Windows (2026-04-02)
- refactor: strip to placeholder skeleton — get it running first (2026-04-02)
- feat: initial Textual dashboard — projects, lights, seedbox, agent, clock (2026-04-02)
- init: dashboard vision, panels, and ideas from session history (2026-04-02)

### find-hub-tracker
- Add selenium, undetected-chromedriver, setuptools deps for auth flow (2026-04-02)
- Merge pull request #6 from karlmarx/claude/add-healthchecks-ping-DlWgs (2026-04-02)
- fix: handle empty DEVICES_TO_TRACK in .env without JSON parse error (2026-03-31)
- Merge pull request #5 from karlmarx/claude/add-healthchecks-ping-DlWgs (2026-03-31)
- feat: add ultra.cc deploy script and fix systemd user service (2026-03-31)

### nwb-yoga
- fix: add PNG icon variants for favicon and PWA install support (2026-04-01)
- feat: lotus flower SVG icon with warm terracotta and dark green mono version (2026-03-29)
- Merge pull request #1 from karlmarx/docs/readme (2026-03-28)
- Add comprehensive README (2026-03-28)
- improve: self-contained descriptions, better animations (2026-03-26)

### foodr
- Merge pull request #1 from karlmarx/docs/readme (2026-03-28)
- Add comprehensive README (2026-03-28)
- Build Foodr: fast food rating app with chain-specific scales (2026-03-26)

### openclaw-watchdog
- fix: swap AI order — Gemini first, DeepSeek fallback (2026-03-25)
- feat: Playwright JS rendering, DeepSeek scoring, Discord webhook notifications (2026-03-25)
- fix: absolute paths everywhere, semicolon as separate token, claude.exe direct call (2026-03-25)
- fix: use WT Preview exe path, fix stale PID singleton via tasklist check (2026-03-25)
- feat: add Claude Linux (WSL) profile, fix tab emoji via tabTitle+suppressApplicationTitle (2026-03-25)

### todo-dashboard
- Initial commit: TODO Dashboard system (2026-03-17)

### dev-setup
- Initial setup: Tailscale SSH + Claude Code MCPs + phone access guides (2026-03-17)
<!-- RECENT_CHANGES_END -->

## Future Plans

See [FUTURE.md](FUTURE.md) for the full roadmap.
