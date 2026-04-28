# Command Center (command.93.fyi)

Personal dashboard at https://command.93.fyi. Source: `~/karl-command-center` (Next.js 16 + React 19 + Tailwind 4 + framer-motion + lucide-react + better-sqlite3). Deployed via Vercel, gated by Cloudflare Access (9193 tenant).

This doc captures the design agreed 2026-04-26 for expanding the existing bento-grid home into a full command center.

**Status (2026-04-26):** Phase 0 live — bento home with 4 API-backed cells deployed at https://command.93.fyi behind Cloudflare Access. The `~/karl-command-center` repo has working `app/api/{ci-status,subdomains,github-prs,reminders}/route.ts` routes plus components feeding the home grid. Phases 1–6 (Status zone expansion, /control, /explore, weekly review, local FastAPI agent) per the **Build sequence** below are still pending.

## Purpose

Replace ad-hoc shell incantations and scattered status checks with one URL Karl opens every morning. Three jobs:

- **Glance** — what's new today, what needs me
- **Health** — what's running, what's broken, what's headed off the rails
- **Act** — kick off pipelines, restart services, capture quick notes — without dropping to a terminal

## Architecture

Layered routes (chose this over single-page bento or anchor-nav sections):

```
command.93.fyi/
  /         → Today + Status (read-only)
  /control  → Buttons & toggles
  /explore  → Deep data
```

Sticky top nav switches surfaces. Each route owns its loading skeleton and streaming. Home stays fast even as `/explore` grows heavy.

### Why routes, not one page

- Each surface has different ergonomics: morning glance wants <2s TTFB and zero scroll; explore wants room to breathe.
- Read-only home means it can be aggressively cached; control/explore can be dynamic.
- Next.js 16's per-route streaming makes the split nearly free.
- Risk: discoverability. Mitigation: keep nav always visible, sparse (3 items), labeled clearly.

## Routes

### `/` — Today + Status

Read-only. Two zones, top→bottom.

**Top — "Today" (the glance):**
- **Now**: time, weather, sunrise/sunset (Oakland Park, FL)
- **Calendar**: next 3 events from Google Calendar
- **Todoist**: top 5 items due today from `karl-todo` project
- **PRs awaiting Karl**: open PRs across `karlmarx/*` repos requesting his review
- **Inbox triage** (#4 from extras): Gmail unread by label (`important`, `karl-todo`, etc.) with one-click "send to Todoist" or "snooze"
- **Weekly review** (#6 from extras): Sunday-only auto-generated one-pager — what shipped, what slipped, what's open, suggested cuts

**Bottom — "Status" (the health board):**
- **Pipelines**: Nextcloud sync, screenshot parser, return scanner, photo memory — last run, next run, ⚡/✓/❌ (mirrors process-monitor)
- **Mac**: free RAM, free disk on `/`, free disk on Crucial X9, MLX server up/down
- **Sites**: ping status for *.93.fyi (auto, command, others)
- **Voice clones**: latest build status (Karl-v2, Brian-v1, Mom) — pulled from a JSON the voice scripts write
- **Seedbox**: Nextcloud version, disk usage, Wireguard up/down

Cells shift from "info" to "alert" past per-module thresholds (e.g. Nextcloud sync >24h stale → red).

### `/control` — Buttons & toggles

Grid of action cards. Click → confirm → run. Status streams back inline. Every card shows last-run timestamp and outcome.

- **Pipelines**: Run Nextcloud sync · Run screenshot parser · Run return scanner · Trigger photo memory
- **Local AI**: Restart MLX server · Restart Qwen :8082 · Free model RAM · Pull a model
- **Quick capture**: Add Todoist task · Add reminder · Append to TODO.md · Append to `.remember/now.md`
- **Domains**: Purge Cloudflare cache for *.93.fyi · Re-deploy command/auto on Vercel
- **Seedbox**: SSH-run `app-nextcloud version` · `app-nextcloud upgrade` · check disk

RAM-aware actions (anything starting MLX/Ollama) check free RAM first and refuse below 1 GB with a clear message rather than silently failing. Follows the multi-session memory coordination rules in `~/.claude/CLAUDE.md`.

**Destructive actions require a second confirm.** Cloudflare Access already gates the whole site, but anything that mutates state (re-deploy, restart, `app-nextcloud upgrade`, free model RAM, purge cache) must show a modal "type the action name to confirm" before executing. Read-only actions (check disk, ping seedbox) are one-click.

### `/explore` — Deep data

Investigation surface. Left nav column, right content pane.

- **Photos**: browse Crucial X9 catalog (folder tree → thumbs → metadata, EXIF, VLM caption if present)
- **Voices**: speakers, embeddings count, sample player, ElevenLabs voice IDs
- **Memory inspector** (#2 from extras): live view + edit-in-place of `~/.claude/projects/-Users-kmx/memory/MEMORY.md` and each linked file. Full-text search across `.remember/` (today, recent, archive, core-memories) with date filter.
- **openclaw runs**: history, model used, output, errors
- **Repos**: recent commits across all `karlmarx/*` repos (last 7 days), grouped by repo
- **Activity timeline**: unified chronological feed of pipeline runs + commits + Todoist completions + voice builds. The killer feature — the only place "ran photo pipeline at 3pm, committed at 3:15, finished a Todoist at 3:30" becomes one narrative.

## Data sources

| Module | Source | Mechanism |
|---|---|---|
| Calendar | Google Calendar API | OAuth, server-side cache 5min |
| Todoist | Todoist Sync API, project=`karl-todo` | Token, server-side cache 1min |
| GitHub PRs | `gh` API or Octokit | PAT, cache 2min |
| Gmail labels | Gmail API | OAuth, cache 2min |
| Pipelines status | `~/.local/share/<service>/sync.log` tail + launchd state | File read + `launchctl list` |
| Mac stats | `top -l1`, `df`, `pgrep mlx` | Local exec |
| Sites ping | HTTP HEAD to each *.93.fyi | Server-side fetch, cache 30s |
| Voice clones | `~/karl-infra/voice-corpus/status.json` (to be written) | File read |
| Seedbox | SSH `karlmarx@tofino.usbx.me` | Cached SSH command result, 5min TTL |
| Photos | Crucial X9 catalog SQLite | better-sqlite3 read |
| Memory | `~/.claude/projects/-Users-kmx/memory/` | File read + write (edit-in-place) |
| openclaw | `~/.openclaw/runs/` (or wherever logs land) | File read |
| Repos | `gh` API for commits | PAT, cache 5min |
| Activity timeline | Aggregator that reads all of the above | In-memory join |
| Weekly review | Background job runs Sundays, writes JSON the home reads | Cron or scheduled action |

The dashboard runs on Vercel — most local data (Mac stats, log tails, SSH) needs a tiny local agent on the Mac Studio that exposes a JSON endpoint the Vercel app fetches via Cloudflare tunnel.

**Local agent stack: FastAPI** (Python 3.14, `uv run`, `uvicorn` worker). Chosen over Node/Bun because Karl's existing pipelines are all Python — same RAM-awareness helpers, same `subprocess` patterns, same `.remember/` and `~/.openclaw/` parsing already in the toolbox. Agent endpoints mirror the data sources table above; deployed as a launchd agent on the Mac Studio so it restarts on boot.

## Build sequence

Suggested order, each phase shippable on its own:

1. **Local agent** — small Node/Python service on Mac Studio that exposes `/stats`, `/pipelines`, `/voices`, etc. as JSON. Exposed via Cloudflare tunnel.
2. **Home Status zone** — pipelines + Mac + sites + voice clones + seedbox cards. Tests the agent end-to-end.
3. **Home Today zone** — calendar + Todoist + PRs + inbox + weather. All read-only API integrations.
4. **`/control`** — action cards. Each card is a POST to the local agent (or directly to Vercel for cloud actions).
5. **`/explore`** — most expensive surface, save for last. Photos browser + memory inspector + activity timeline.
6. **Weekly review** — scheduled job + Sunday card on home.

## Open questions

- **Husband module** (was #5 in extras, deferred) — Bogotá? Medellín? If Karl wants this later, needs Colombia city + relationship dates.
- **Deferred to later sub-projects** — sexy Mac desktop app, sleek Android app. Web dashboard is the foundation; native apps consume the same local agent JSON.

## Resolved (2026-04-26)

- Weather location → Oakland Park, FL
- Local agent stack → FastAPI on the Mac Studio
- Destructive `/control` actions → all require a typed-confirm modal

## Cross-references

- `~/karl-infra/infra/auto-dashboard.md` — sibling project at auto.93.fyi (xyflow automation map). Stays as-is; command center is the daily-driver companion.
- `~/karl-infra/infra/process-monitor-dashboard.md` — terminal version of the Status zone. Will coexist; command center is the GUI equivalent.
- `~/karl-infra/infra/local-ai.md` — RAM-awareness rules `/control` enforces.
- `~/karl-infra/infra/domain-93fyi.md` — domain config command center lives under.
- `~/karl-infra/infra/vercel.md` — deployment platform.
- `~/.claude/CLAUDE.md` — multi-session memory coordination rules baked into `/control` RAM checks.
