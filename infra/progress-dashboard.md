# Progress Dashboard

**Status:** In development (2026-04-18)  
**Owner:** Karl  
**Repo:** [karlmarx/progress-dashboard](https://github.com/karlmarx/progress-dashboard)  
**Deployment:** Vercel → `progress.93.fyi`

## Purpose

Real-time, gated status dashboard for Karl's parallel workloads (photo-memory pipeline, MLX-VLM reprocessor, Google Account Migration, etc.). Displays finished/in-flight/not-started work with email notifications on major milestones.

## Architecture

### Components

```
Next.js 16.2.2 (Vercel)
├── Pages
│   ├── / (dashboard, authenticated)
│   └── /api/auth/[...nextauth] (GitHub OAuth)
├── API Routes
│   ├── /api/status (status aggregation)
│   └── /api/milestones (milestone tracking + email trigger)
├── Data Sources
│   ├── ~/.claude/coordination.md (memory, process state)
│   ├── ~/Nextcloud/.../TODO.md (project progress)
│   └── Process monitoring (ps, logs)
├── Database
│   └── progress.db (SQLite, milestone tracking)
└── Email
    └── nodemailer → Gmail (milestone notifications)
```

### Data Flow

1. **Dashboard UI** (React): Polls `/api/status` every 30 seconds
2. **Status Aggregation** (`/api/status`):
   - Reads `coordination.md` for memory/process state
   - Parses `TODO.md` for project task counts
   - Checks running processes via `ps` and log files
   - Constructs section/task hierarchy
3. **Milestone Tracking** (`/api/milestones`):
   - POST: Create milestone when task completes
   - GET: Fetch unsent milestones
   - Email trigger: `/api/notify` sends emails + marks as sent
4. **Email** (nodemailer):
   - Sends HTML emails to karlmarx9193@gmail.com
   - Link back to dashboard for full status view

## Tech Stack

- **Framework:** Next.js 16.2.2 with App Router
- **Language:** TypeScript
- **Frontend:** React 19.2.4 + Tailwind CSS v4
- **Auth:** NextAuth.js 5 (GitHub OAuth)
- **Database:** SQLite (better-sqlite3)
- **Email:** nodemailer
- **Hosting:** Vercel (free tier)
- **Domain:** progress.93.fyi (Cloudflare DNS)

## Authentication

GitHub OAuth via NextAuth:
- User clicks "Sign in with GitHub" on `/api/auth/signin`
- Redirected to GitHub authorization
- Session created, user accessing dashboard
- Sign out clears session

**Authorized user:** karlmarx (github.com/karlmarx)

## Data Sources

### coordination.md
Location: `~/.claude/coordination.md`
- **Purpose:** Multi-session RAM coordination
- **Parsed:** RAM usage (total/free), memory consumption per workload (MLX, photo-memory)
- **Update frequency:** Manual (when new sessions start/stop), read-only by dashboard
- **Example:** `35/36 GB used (~1GB free)` → extracted as `totalUsedRam: 35`, `freeRam: 1`

### TODO.md
Location: `~/Nextcloud/Documents/TODO.md`
- **Purpose:** Long-form project tracking
- **Parsed:** Checkbox progress (`[x]` vs `[ ]`) by section (Google Account Migration, Blazing Paddles, Local VLM Analysis)
- **Update frequency:** As tasks are completed
- **Example:** `### Google Account Migration` with 60/80 items complete → `percentComplete: 75%`

### Process Status
- **MLX-VLM reprocessor:** Detect via `ps aux | grep mlx-vlm`, extract elapsed time
- **Photo-memory Phase 1:** Detect via `ps aux | grep phase1_dedupe`, read progress from log (`/Volumes/Crucial X9/photo-memory/logs/phase1.log`)

## Database Schema

```sql
CREATE TABLE milestones (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  task_id TEXT NOT NULL UNIQUE,
  task_name TEXT NOT NULL,
  completed_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  email_sent INTEGER DEFAULT 0,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

**Lifecycle:**
1. Task completes → external agent calls `POST /api/milestones` with `{task_id, task_name}`
2. Record inserted with `email_sent = 0`
3. Admin or cron calls `POST /api/notify`
4. Milestone fetched, email sent, `email_sent` set to 1

## Email Notifications

**Trigger:** Major milestones (when a task moves to "finished" status)

**Recipients:** karlmarx9193@gmail.com

**Template:**
```html
Subject: ✓ {task_name} Completed
Body:
  Heading: task_name + checkmark
  Body: "A major milestone has been completed"
  CTA: Button linking to progress.93.fyi
  Footer: "Progress Dashboard • Your parallel work tracker"
```

**Frequency:** On-demand via `/api/notify` endpoint (manual trigger or future: cron)

## Environment Variables

```
GITHUB_ID                 GitHub OAuth app ID
GITHUB_SECRET             GitHub OAuth app secret
NEXTAUTH_URL              https://progress.93.fyi
NEXTAUTH_SECRET           Random 32-byte secret
EMAIL_USER                karlmarx9193@gmail.com
EMAIL_PASS                Gmail app password (16-char)
```

## Deployment

**Platform:** Vercel (Free)
**Branch:** `main` (auto-deploy)
**Preview:** PRs generate preview URLs (standard Vercel behavior)

**Setup:**
1. Env vars added to Vercel project settings
2. Custom domain: `progress.93.fyi` added to project
3. Cloudflare CNAME: `progress` → `cname.vercel.com`

## Monitoring & Status

**Health checks:**
- Dashboard loads at `progress.93.fyi` (login page)
- Auth flow: Click login → GitHub → redirect → dashboard
- `/api/status` returns valid JSON (curl test)
- Email sends on milestone creation (test via `/api/notify`)

**Known limitations:**
- SQLite is local to Vercel instance (data lost on redeploy unless persisted via managed database)
- Process detection is Mac-specific (`ps aux` format) — would need adjustment for Linux
- Email rate-limited by Gmail (500/day for free account)

## Future Enhancements

1. **Persistent database:** Move SQLite to PostgreSQL on Vercel's managed tier
2. **Real-time updates:** Replace polling with WebSocket or Server-Sent Events
3. **Custom milestones:** API to define milestone thresholds (e.g., "60% complete") instead of only binary finish/not-finish
4. **Slack integration:** Post milestone updates to Slack channel instead of (or in addition to) email
5. **Historical dashboard:** Archive completed work, show velocity/burndown charts

## Cross-References

- **Karl-infra:** This document
- **Local AI:** `~/karl-infra/infra/local-ai.md` (coordination protocol for RAM-intensive work)
- **Vercel:** Standard deployment target for web apps
- **Nextcloud:** Source of TODO.md
- **Gmail:** Notification recipient
