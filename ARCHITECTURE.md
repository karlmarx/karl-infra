# Architecture Deep-Dive

## System Overview

Karl's infrastructure spans three deployment targets: **Vercel** (web apps), **Windows 11 workstation** (local automation + AI), and **ultra.cc seedbox** (planned remote automation). All source lives on GitHub under the `karlmarx` org.

## Deployment Targets

### Vercel (Free Tier)

All web applications deploy to Vercel with custom domains via Cloudflare DNS.

| Project | Framework | Database | Domain |
|---------|-----------|----------|--------|
| nwb-plan | Single-file HTML PWA | None (client-side) | nfit.93.fyi, 93.fyi |
| nwb-yoga | Single-file HTML PWA | None (client-side) | nyoga.93.fyi |
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
- Future: other periodic automation tasks currently running on Windows

## Data Stores

### Supabase (TrickAdvisor)

Used exclusively by TrickAdvisor (frontend + API):
- **Postgres**: users, profiles, encounters, ratings, photos
- **Auth**: email/password registration, session management
- **Storage**: user profile photos with admin moderation pipeline

### Client-Side Only

nwb-plan and nwb-yoga are single-file HTML PWAs with no backend:
- Exercise data embedded in HTML
- Service worker for offline access
- localStorage for user preferences

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
| Frontend | React (Vite), single-file HTML PWAs |
| Backend | Node/Express (Vercel Functions), Python scripts |
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

openclaw-watchdog ──monitors──→ OpenClaw gateway

claude-pipeline ──watches──→ Nextcloud/inbox/
                 ──routes──→ OpenClaw sub-agent

find-hub-tracker ──polls──→ Google Find Hub API
                 ──alerts──→ Discord webhook
```
