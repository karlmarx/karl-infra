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
| Identity Verification | React 19 + Vite + TypeScript | Supabase (Postgres + Auth + Storage) | id.93.fyi |
| ID API | Node/Express on Vercel Functions | Supabase | (serverless, called by ID frontend) |
| Contact Form | Next.js 16 + React 19 + TypeScript + Turnstile | Supabase (Postgres + rate limits) | contact.93.fyi |
| Flight Connection Confidence | Next.js 16 + React 19 + TypeScript | None (client-side analysis) | layover.93.fyi |
| Mom's Reassurance Hub | Next.js 16 + React 19 + TypeScript + framer-motion | None (static content) | mom.93.fyi |
| blazing-paddles-react | React (Vite) | None | blazingpaddles.org |
| auto-dashboard | React 19 + Vite + TypeScript + @xyflow/react | None (static) | auto.93.fyi |
| orthoappt | Next.js 16 + React 19 + TypeScript + Tailwind 4 + PWA | None (localStorage; build-time MD parse) | ortho.93.fyi |
| progress-dashboard | Next.js 16 + React 19 + TypeScript + NextAuth | SQLite (milestone tracking) | progress.93.fyi |
| karl-command-center | Next.js 16 + React 19 + Tailwind 4 + framer-motion + better-sqlite3 | SQLite (local) + Mac Studio FastAPI agent | command.93.fyi (Cloudflare Access gated) |
| house-tracker | React 19 + Vite 8 + react-router 7 + Tailwind 4 | None (static JS export) | (no custom domain — `*.vercel.app`) |

**Vercel configuration:**
- All projects on free tier
- Automatic deploys from `main` branch
- Preview deploys on PRs
- No custom build infrastructure needed (static HTML or Vite builds)

## Services

### Flight Connection Confidence (layover.93.fyi)
- **Purpose**: Data-backed reassurance for elderly travelers anxious about tight flight connections
- **Tech**: Next.js 16 + React 19 + TypeScript, Tailwind CSS light mode, no database
- **Features**: Connection success probability calculator, expandable detail cards, pre-trip checklist, research references
- **Audience**: Non-technical, mobile-first, light mode with large fonts
- **Docs**: [services/layover.md](services/layover.md)

### Mom's Reassurance Hub (mom.93.fyi)
- **Purpose**: Personal, handwritten-letter-style answers to the everyday things Mom worries about (phone hacks, car AC, stove, scam texts, etc.)
- **Tech**: Next.js 16 + React 19 + TypeScript, Tailwind v4, framer-motion
- **Design**: "Letter from your son" aesthetic — Caveat/Lora/Newsreader fonts, paper/ink/rose/sage palette
- **Audience**: Mom specifically; written in son's voice, expandable cards, tel: links to call him
- **Docs**: [services/mom.md](services/mom.md)

## Deployment Targets (continued)

### Windows 11 Workstation

The primary development machine runs several always-on or on-demand automation services:

| Service | Runtime | Purpose |
|---------|---------|---------|
| OpenClaw | Claude Code (Node.js) | AI assistant gateway |
| openclaw-watchdog | Python (Rich + Playwright) | Keeps OpenClaw alive, screen awake |
| claude-pipeline | Python | Watches Nextcloud/inbox/ for .md files, routes to OpenClaw |
| gemini-auto | Playwright (Python) | **Ported to Mac** — see Mac Studio section. May still run on Windows historically. |
| process-monitor-dashboard | Python 3 | Real-time terminal UI: processes, Ollama models, Claude sessions |

**Key paths:**
- OpenClaw workspace: `~/.openclaw/workspace/`
- Nextcloud sync: `~/Nextcloud/Documents/`
- TODO dashboard: `~/Nextcloud/Documents/todo_dashboard.html`

### Mac Studio M4 Max (Local AI + Automation)

Apple Silicon-native machine (36 GB unified memory) running compute-intensive automation:

| Service | Schedule | Purpose |
|---------|----------|---------|
| MLX-VLM `:8080` (analysis) | Always-on (watched) | Heavy vision/text. Watchdog config = `gemma-4-26b-a4b-it-4bit`; live process as of 2026-04-26 = `Qwen3.5-27B-4bit` (verify which is intended) |
| MLX-VLM `:8081` (fast) | Always-on (NOT watched) | Default chat — `Qwen3.5-9B-MLX-4bit`, 32k ctx |
| MLX-VLM `:8082` (long-ctx) | Always-on (NOT watched) | Reasoning — `Qwen3.5-9B-MLX-4bit`, 262k ctx (currently DOWN per 2026-04-26 audit) |
| workout_watcher | Every 15 min | Watch Nextcloud for new workout videos, process via MLX-VLM, extract frames & analysis |
| workout_digest | Daily 07:00 | Synthesize workout form feedback via MLX-VLM, email digest (migrated off Claude API) |
| Nextcloud photo sync | Every 1 hour | Poll Nextcloud `/InstantUpload/Camera/`, download to external SSD. **Currently dead — see [infra/nextcloud-android-sync.md](infra/nextcloud-android-sync.md)** |
| Nextcloud screenshot parser | Every 1 hour | Poll `/InstantUpload/Screenshots/`, MLX-VLM classify, file by category, append Todoist tasks. **Currently dead — same plist bugs** |
| Nextcloud video ingest | Every 30 min | Move phone videos from Nextcloud to X9 SSD via rclone |
| process-monitor-dashboard | On-demand | Terminal UI: background process status, RAM usage, MLX model load |
| command-agent (FastAPI) | Always-on | Exposes `/stats`, `/pipelines`, `/voices`, etc. as JSON for command.93.fyi via Cloudflare tunnel |
| openclaw gateway/node | Always-on (4 LaunchAgents) | Local model gateway/router; `:18789` loopback; routes to MLX/Ollama/Google. See [infra/openclaw.md](infra/openclaw.md) |
| gemini CLI | Interactive | Secondary AI assistant. OAuth `karlmarx9193@gmail.com`. 5 MCP extensions. See [infra/gemini-cli.md](infra/gemini-cli.md) |
| gemini-auto | On-demand | Playwright/CDP image-gen via Gemini UI, 3-account rotation. Originally Windows; ported to Mac (hardcoded paths still in source). See [infra/gemini-auto.md](infra/gemini-auto.md) |

**Key characteristics:**
- All background processes use LaunchAgents (`~/Library/LaunchAgents/*.plist`)
- Heavy compute (VLM inference) uses MLX framework for native Apple Silicon performance (no GPU copy overhead)
- RAM coordination across up to 9 concurrent Claude Code sessions via `~/.claude/coordination.md`
- SQLite state tracking for video pipeline at `~/.local/share/workout-pipeline/state.db`
- External SSD: `/Volumes/Crucial X9/photos/incoming/` for video storage and derivatives

**Key paths:**
- Infra services: `~/karl-infra/services/`
- Local VLM analysis: `/Users/kmx/projects/local-vlm-analysis/`
- Photos/video staging: `/Volumes/Crucial X9/photos/incoming/`
- Nextcloud desktop sync: `~/Nextcloud/`

**Docs**: [infra/workout-pipeline.md](infra/workout-pipeline.md), [infra/local-ai.md](infra/local-ai.md), [infra/local-vlm-analysis.md](infra/local-vlm-analysis.md), [infra/openclaw.md](infra/openclaw.md), [infra/gemini-cli.md](infra/gemini-cli.md), [infra/gemini-auto.md](infra/gemini-auto.md), [infra/nextcloud-android-sync.md](infra/nextcloud-android-sync.md), [infra/nextcloud-screenshot-parser.md](infra/nextcloud-screenshot-parser.md)

### ultra.cc Seedbox (Planned)

A remote Linux server for running automation that needs to be always-on without depending on the workstation:

- **find-hub-tracker**: Polls Google Find Hub API for device location/battery, sends Discord alerts. See [infra/find-hub-tracker.md](infra/find-hub-tracker.md)
- **Nextcloud** (`https://karlmarx.tofino.usbx.me/nextcloud`): Personal Nextcloud 27 on Ultra.cc's managed hosting, subpath install. Mobile app syncs `~/Nextcloud/` to the macOS desktop client. Receives `todo.md` uploads from karl-todo CI.
- Future: other periodic automation tasks currently running on Windows

### Local repos (manual / WIP)

Standalone repos that aren't yet wired into LaunchAgents, GHA crons, or Vercel custom domains. Documented separately from running services.

| Repo | Purpose | Status | Doc |
|------|---------|--------|-----|
| photo-memory | Local VLM pipeline over Google Takeout (1.1 TB → searchable catalog, future `photos.93.fyi`) | Phase 1 in progress | [infra/photo-memory.md](infra/photo-memory.md) |
| finflow | Personal finance aggregator (Teller + DuckDB + Polars + FastAPI) | Working alpha, manual run | [infra/finflow.md](infra/finflow.md) |
| amex-claims-automator | Playwright bot for Amex Return/Loss Protection claims | Phase 1 reconnaissance | [infra/amex-claims-automator.md](infra/amex-claims-automator.md) |
| tui-dashboard | Textual TUI for global status (vs. process-monitor-dashboard which is local-only) | Skeleton — only clock works | [infra/tui-dashboard.md](infra/tui-dashboard.md) |
| house-tracker | South Florida property comparison + Gemini renders | Active personal use, no domain | [infra/house-tracker.md](infra/house-tracker.md) |

### GitHub Actions (CI-driven automation)

Automation where the runner itself does the work — no always-on host required. Triggered by push to `main` or scheduled cron.

| Service | Trigger | Purpose |
|---------|---------|---------|
| karl-todo sync | `*/15 * * * *` + `push` to `main` | **Todoist is source of truth.** Cron pulls `karl-todo` project → regenerates `todo.md` → commits with `[skip ci]` → mirrors to Nextcloud. Push path additionally runs a forward sync (`todo.md` → Todoist) before the pull, as an escape hatch for bulk markdown edits. |

Repo: [karlmarx/karl-todo](https://github.com/karlmarx/karl-todo). Secrets (`TODOIST_API_TOKEN`, `NEXTCLOUD_URL`, `NEXTCLOUD_USER`, `NEXTCLOUD_APP_PASSWORD`) live in Actions Secrets. The workflow has a `forward` job (skipped on schedule), a `pull-and-mirror` job that always runs, and a gating `report` job that fails only if the pull leg failed — a Nextcloud outage doesn't block the Todoist → git leg.

## Data Stores

### Supabase (Identity Verification)

Used exclusively by Identity Verification (frontend + API):
- **Postgres**: users, profiles, encounters, ratings, photos
- **Auth**: email/password registration, session management
- **Storage**: user profile photos with admin moderation pipeline

### Client-Side Only

nwb-plan, nwb-yoga, and foodr have no backend:
- **nwb-plan**: Next.js 16 PWA with 67+ exercises, Claude API for AI suggestions, equipment-aware superset system
- **nwb-yoga**: React 18 + Vite with Canvas 2D pose animations, Web Audio API bell cues
- **foodr**: Next.js 16 PWA with chain-relative ratings for 12 fast food chains
- All use service workers for offline access and localStorage for user preferences

### Contact Form (contact.93.fyi)

Contact form with bot protection and rate limiting:
- **Database**: Supabase Postgres (contact_submissions, rate_limit_log tables)
- **CAPTCHA**: Cloudflare Turnstile (free tier)
- **Email**: Resend transactional email (confirmation + admin notification)
- **Features**: 5 submissions/hour per IP rate limit, form validation, IP tracking
- **Docs**: [services/contact.md](services/contact.md)

## Domain & DNS Architecture

```
Dynadot (registrar)
  93.fyi ──> Cloudflare (nameservers)
               ├── nfit.93.fyi     CNAME ──> cname.vercel-dns.com (nwb-plan)
               ├── nyoga.93.fyi    CNAME ──> cname.vercel-dns.com (nwb-yoga)
               ├── id.93.fyi       CNAME ──> cname.vercel-dns.com (Identity Verification)
               ├── contact.93.fyi  CNAME ──> cname.vercel-dns.com (Contact Form)
               ├── layover.93.fyi  CNAME ──> cname.vercel-dns.com (Flight Connection Confidence)
               ├── mom.93.fyi      CNAME ──> cname.vercel-dns.com (Mom's Reassurance Hub)
               ├── auto.93.fyi     CNAME ──> cname.vercel-dns.com (auto-dashboard)
               ├── ortho.93.fyi    CNAME ──> cname.vercel-dns.com (orthoappt)
               ├── command.93.fyi  CNAME ──> cname.vercel-dns.com (command-center, gated by Cloudflare Access)
               ├── progress.93.fyi CNAME ──> cname.vercel-dns.com (progress-dashboard)
               ├── 93.fyi          CNAME ──> cname.vercel-dns.com (nwb-plan, temp)
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

photo-memory ──reads──→ /Volumes/Crucial X9/google-takeout-2026-04-16/
             ──calls──→ MLX-VLM :8080 (Gemma/Qwen/PaliGemma) + MLX-Whisper
             ──writes─→ /Volumes/Crucial X9/photo-memory/catalog.db (planned)
             ──future─→ Cloudflare Worker @ photos.93.fyi (D1 + R2 + GitHub OAuth)

finflow ──mTLS──→ Teller API (api.teller.io)
        ──writes─→ ~/finflow/finflow.duckdb

amex-claims-automator ──drives──→ Chromium (Playwright, headed)
                       ──submits─→ claims-center.americanexpress.com

house-tracker ──static──→ properties.js + public/photos/ → Vercel

local-vlm-analysis ──called by──→ workout_watcher, photo-memory
                   ──routes to──→ MLX-VLM :8080
```
