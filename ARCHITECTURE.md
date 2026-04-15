# Architecture Deep-Dive

## System Overview

Karl's infrastructure spans three deployment targets: **Vercel** (web apps), **Windows 11 workstation** (local automation + AI), and **ultra.cc seedbox** (planned remote automation). All source lives on GitHub under the `karlmarx` org.

## Deployment Targets

### Vercel (Free Tier)

All web applications deploy to Vercel with custom domains via Cloudflare DNS.

| Project | Framework | Database | Domain |
|---------|-----------|----------|--------|
| nwb-plan | Next.js 16 + React 19 + TypeScript + Claude API | None (client-side, localStorage) | nfit.93.fyi, 93.fyi |
| nwb-yoga | React 18 + Vite + Canvas animations | None (client-side) | nyoga.93.fyi |
| foodr | Next.js 16 + React 19 + TypeScript | None (localStorage) | foodr-app.vercel.app |
| TrickAdvisor | React (Vite) | Supabase (Postgres + Auth + Storage) | ta.93.fyi |
| TrickAdvisor-API | Node/Express on Vercel Functions | Supabase | (serverless, called by TA frontend) |
| blazing-paddles-react | React (Vite) | None | blazingpaddles.org |

**Vercel configuration:**
- All projects on free tier
- Automatic deploys from `main` branch
- Preview deploys on PRs
- No custom build infrastructure needed (static HTML or Vite builds)

### Windows 11 Workstation

The primary development machine runs several always-on or on-demand automation services:

| Service | Runtime | Purpose |
|---------|---------|---------|
| OpenClaw | Claude Code (Node.js) | AI assistant gateway |
| openclaw-watchdog | Python (Rich + Playwright) | Keeps OpenClaw alive, screen awake |
| claude-pipeline | Python | Watches Nextcloud/inbox/ for .md files, routes to OpenClaw |
| gemini-auto | Playwright (JS) | Gemini UI automation for image generation via CDP |

**Key paths:**
- OpenClaw workspace: `~/.openclaw/workspace/`
- Nextcloud sync: `~/Nextcloud/Documents/`
- TODO dashboard: `~/Nextcloud/Documents/todo_dashboard.html`

### ultra.cc Seedbox (Planned)

A remote Linux server for running automation that needs to be always-on without depending on the workstation:

- **find-hub-tracker**: Polls Google Find Hub API for device location/battery, sends Discord alerts
- **Nextcloud** (`https://karlmarx.tofino.usbx.me/nextcloud`): Personal Nextcloud 27 on Ultra.cc's managed hosting, subpath install. Mobile app syncs `~/Nextcloud/` to the macOS desktop client. Receives `todo.md` uploads from karl-todo CI.
- Future: other periodic automation tasks currently running on Windows

### GitHub Actions (CI-driven automation)

Automation where the runner itself does the work — no always-on host required. Triggered by push to `main` or scheduled cron.

| Service | Trigger | Purpose |
|---------|---------|---------|
| karl-todo sync | `*/15 * * * *` + `push` to `main` | **Todoist is source of truth.** Cron pulls `karl-todo` project → regenerates `todo.md` → commits with `[skip ci]` → mirrors to Nextcloud. Push path additionally runs a forward sync (`todo.md` → Todoist) before the pull, as an escape hatch for bulk markdown edits. |

Repo: [karlmarx/karl-todo](https://github.com/karlmarx/karl-todo). Secrets (`TODOIST_API_TOKEN`, `NEXTCLOUD_URL`, `NEXTCLOUD_USER`, `NEXTCLOUD_APP_PASSWORD`) live in Actions Secrets. The workflow has a `forward` job (skipped on schedule), a `pull-and-mirror` job that always runs, and a gating `report` job that fails only if the pull leg failed — a Nextcloud outage doesn't block the Todoist → git leg.

## Data Stores

### Supabase (TrickAdvisor)

Used exclusively by TrickAdvisor (frontend + API):
- **Postgres**: users, profiles, encounters, ratings, photos
- **Auth**: email/password registration, session management
- **Storage**: user profile photos with admin moderation pipeline

### Client-Side Only

nwb-plan, nwb-yoga, and foodr have no backend:
- **nwb-plan**: Next.js 16 PWA with 67+ exercises, Claude API for AI suggestions, equipment-aware superset system
- **nwb-yoga**: React 18 + Vite with Canvas 2D pose animations, Web Audio API bell cues
- **foodr**: Next.js 16 PWA with chain-relative ratings for 12 fast food chains
- All use service workers for offline access and localStorage for user preferences

## Domain & DNS Architecture

```
Dynadot (registrar)
  93.fyi ──> Cloudflare (nameservers)
               ├── nfit.93.fyi  CNAME ──> cname.vercel-dns.com (nwb-plan)
               ├── nyoga.93.fyi CNAME ──> cname.vercel-dns.com (nwb-yoga)
               ├── ta.93.fyi    CNAME ──> cname.vercel-dns.com (TrickAdvisor)
               ├── 93.fyi       CNAME ──> cname.vercel-dns.com (nwb-plan, temp)
               └── Email routing: k@93.fyi ──> karlmarx9193@gmail.com
```

## Communication Channels

- **Discord**: find-hub-tracker alerts, openclaw-watchdog notifications
- **Email**: k@93.fyi routed through Cloudflare to Gmail
- **GitHub**: Issues for task tracking, PRs for code review, Actions for CI

## Tech Stack Summary

| Layer | Technology |
|-------|-----------|
| Frontend | Next.js 16, React 19, React 18 + Vite, Canvas 2D |
| Backend | Node/Express (Vercel Functions), Python scripts |
| AI | Anthropic Claude API (nwb-plan exercise suggestions) |
| Database | Supabase (Postgres + Auth + Storage) |
| Hosting | Vercel (free tier) |
| DNS | Cloudflare (free tier) |
| Domain | Dynadot (93.fyi) |
| AI | Claude Code (OpenClaw), Gemini (gemini-auto) |
| Automation | Python (watchdog, pipeline), Playwright |
| Dev Environment | Windows 11, Claude Code, Gemini CLI, Tailscale SSH |
| Version Control | GitHub (karlmarx org) |

## Repo Dependency Graph

```
TrickAdvisor (frontend)
  └── TrickAdvisor-API (backend)
        └── Supabase (database + auth + storage)

nwb-plan ←──sync──→ nwb-yoga  (shared lotus SVG icon)
nwb-plan ──calls──→ Anthropic Claude API (exercise suggestions)

openclaw-watchdog ──monitors──→ OpenClaw gateway
                  ──triggers──→ property-scout (daily 8am ET)

property-scout ──reads──→ Gmail IMAP (listing emails)
               ──scrapes──→ Matrix MLS portal
               ──sends──→ Gmail SMTP (HTML report)

claude-pipeline ──watches──→ Nextcloud/inbox/
                 ──routes──→ OpenClaw sub-agent

find-hub-tracker ──polls──→ Google Find Hub Nova API
                 ──stores──→ PostgreSQL / SQLite
                 ──alerts──→ Discord webhook
                 ──pings──→ Healthchecks.io
```
