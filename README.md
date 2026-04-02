# Karl's Infrastructure

> Auto-updated daily from GitHub commits. Last update: 2026-04-02

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
### nwb-plan
- fix: replace generic yoga icon with lotus silhouette in bottom nav (2026-04-02)
- Merge pull request #45 from karlmarx/claude/fix-equipment-picker-logic-7fiFp (2026-04-01)
- fix: equipment picker logic — machine type drives instructions, superset fixes (2026-04-01)
- Merge pull request #44 from karlmarx/claude/improve-wording-bN8xi (2026-04-01)
- Replace "non-negotiable" wording across codebase (2026-04-01)

### nwb-yoga
- fix: add PNG icon variants for favicon and PWA install support (2026-04-01)
- feat: lotus flower SVG icon with warm terracotta and dark green mono version (2026-03-29)
- Merge pull request #1 from karlmarx/docs/readme (2026-03-28)
- Add comprehensive README (2026-03-28)
- improve: self-contained descriptions, better animations (2026-03-26)

### karl-infra
- chore: daily update 2026-04-01 (2026-04-01)
- chore: daily update 2026-03-31 (2026-03-31)
- feat: initial infrastructure documentation (2026-03-30)

### find-hub-tracker
- Merge pull request #5 from karlmarx/claude/add-healthchecks-ping-DlWgs (2026-03-31)
- feat: add ultra.cc deploy script and fix systemd user service (2026-03-31)
- docs: add healthchecks.io config vars to .env.example (2026-03-30)
- feat: initial scaffold — Google Find Hub tracker with Discord integration (2026-03-30)
- chore: add .gitignore before any other files (2026-03-30)

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
