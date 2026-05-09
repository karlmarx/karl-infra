# System Overview

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
|  id.93.fyi          |   |   +- find-hub-tracker                  |
|  +- Social ID       |   |      +- polls Google Find Hub          |
|     + SIV-API       |   |         +- Discord alerts              |
|                     |   |                                         |
|  contact.93.fyi ----+   |   INFRA                                |
|  +- Contact Form        |   ------                                |
|     + Turnstile CAPTCHA |   Dynadot (.fyi registrar)              |
|     + Resend email      |   Cloudflare (DNS + email routing)      |
|                         |   GitHub (all repos + Actions)          |
|  layover.93.fyi         |   Vercel (all deployments)            |
|  +- Flight Connection   |                                         |
|     Confidence          |                                         |
|     + Mobile reassurance |                                         |
|                         |                                         |
|  mom.93.fyi             |                                         |
|  +- Mom's Reassurance   |                                         |
|     Hub (letter-style)  |                                         |
|     + framer-motion     |                                         |
|                         |                                         |
|  Supabase (DB) -----+   |                                         |
|                         |                                         |
|  progress.93.fyi -------+   Nextcloud (Takeout, TODO, logs)       |
|  +- Progress Dashboard  |                                         |
|     (status monitor)    |                                         |
|     + local system polling                                       |
|     + email notifications                                         |
|                         |                                         |
|  command.93.fyi --------+   Cloudflare Access (zero-trust)        |
|  +- Karl Command Center |   +- gates command.93.fyi               |
|     (Next.js 16)        |                                         |
|     /        Today + Status (read-only)                           |
|     /control Buttons + toggles (typed-confirm modal)              |
|     /explore Photos · voices · memory · activity timeline         |
|     + Mac Studio FastAPI agent for local data                     |
|                         |                                         |
|  auto.93.fyi -----------+                                         |
|  +- Automation Map      |                                         |
|     (xyflow graph)      |                                         |
|                         |                                         |
|  (no subdomain yet)     |                                         |
|  +- house-tracker (S. FL property tracker, *.vercel.app)          |
|                            | Nextcloud (Takeout, TODO, logs)     |
|  93.fyi ----------------+  |                                     |
|  (Cloudflare DNS)           |                                     |
|  k@93.fyi -> Gmail          |                                     |
+-------------------------------------------------------------------+
```

## Deployment Topology

```
                    GitHub (karlmarx)
                         |
              +----------+-----------+
              |                      |
         Push to main          GitHub Actions
              |                      |
              v                      v
           Vercel              daily-update.yml
        (auto-deploy)          (karl-infra refresh)
              |
    +---------+---------+---------+
    |         |         |         |
 nwb-plan  nwb-yoga   SIV     SIV-API
    |         |         |         |
    v         v         v         v
nfit.93.fyi nyoga.    id.93   Serverless
            93.fyi    .fyi    Functions
```

## Local Services

```
  Mac Studio M4 Max (36 GB unified memory)
  +--------------------------------------------------------+
  |                                                        |
  |  OpenClaw (Claude Code gateway)                        |
  |    ^                                                   |
  |    | monitors                                          |
  |  openclaw-watchdog (Python/Rich)                       |
  |    +- keeps gateway alive                              |
  |    +- screen awake                                     |
  |    +- Discord notifications                            |
  |                                                        |
  |  claude-pipeline (Python)                              |
  |    +- watches ~/Nextcloud/Documents/inbox/             |
  |    +- routes .md files to OpenClaw sub-agent           |
  |                                                        |
  |  gemini-auto (Playwright)                              |
  |    +- CDP connection to Chrome:9222                    |
  |    +- Gemini UI automation for image gen               |
  |                                                        |
  |  process-monitor-dashboard (Python 3)                  |
  |    +- real-time terminal UI (3 columns)                |
  |    +- monitors background processes                    |
  |    +- tracks Ollama models & VRAM usage                |
  |    +- displays recent Claude sessions                  |
  |    +- refreshes every 5 seconds                        |
  |                                                        |
  |  Ollama (local LLM inference)                          |
  |    +- gemma4:26b (17 GB)                               |
  |    +- gemma4:latest (9.6 GB)                           |
  |    +- llama3.2:1b (1.3 GB)                             |
  |                                                        |
  |  MLX-VLM Servers (always-on, loopback only)            |
  |    +- :8080 watchdog=gemma-4-26b-4bit / live=Qwen3.5-27B
  |       (only :8080 is restarted by mac-watchdog.sh)     |
  |    +- :8081 Qwen3.5-9B-MLX-4bit (fast chat, primary)   |
  |    +- :8082 Qwen3.5-9B-MLX-4bit (262k reasoning, DOWN) |
  |                                                        |
  |  Nextcloud Photo Sync (every 1 hour) -- DEAD 04-22     |
  |    +- polls Nextcloud /InstantUpload/Camera/           |
  |    +- downloads to /Volumes/Crucial X9/photos/         |
  |    +- bug: plist /opt/homebrew/bin/uv (use ~/.local)   |
  |    +- bug: NEXTCLOUD_PASSWORD = placeholder            |
  |                                                        |
  |  Screenshot Parser (every 1 hour) -- DEAD same bugs    |
  |    +- polls Nextcloud /InstantUpload/Screenshots/      |
  |    +- MLX-VLM classifies: receipt/return/warranty/etc  |
  |    +- files by category, appends Todoist tasks         |
  |                                                        |
  |  local-vlm-analysis (library)                          |
  |    +- 3-layer Gemma pipeline: triage → universal       |
  |       → workout                                        |
  |    +- shared by workout_watcher and photo-memory       |
  |    +- routes to MLX-VLM :8080                          |
  |                                                        |
  |  OpenClaw gateway (4 LaunchAgents, :18789 loopback)    |
  |    +- routes to MLX/Ollama/Google providers            |
  |    +- mac-watchdog.sh restarts :8080 (RAM-gated)       |
  |    +- runs.sqlite at ~/.openclaw/tasks/                |
  |                                                        |
  |  Gemini CLI (interactive AI, secondary to Claude Code) |
  |    +- OAuth karlmarx9193@gmail.com                     |
  |    +- 5 MCP extensions                                 |
  |    +- ~/.gemini/projects.json scopes per directory     |
  |                                                        |
  |  gemini-auto (Playwright/CDP image gen, on-demand)     |
  |    +- Chrome :9222 primary, Edge :9224/:9225 fallback  |
  |    +- 3-account rotation (40 imgs/day each)            |
  |    +- moved from Windows; hardcoded paths in source    |
  |                                                        |
  |  workout_watcher (every 15 min)                        |
  |    +- watches X9 SSD for new .mp4 videos               |
  |    +- runs Gemma pipeline: extract frames → analyze    |
  |    +- outputs data/videos/<sha>.json                   |
  |    +- updates state.db with gemma_done_at              |
  |                                                        |
  |  workout_digest (daily at 07:00 UTC)                   |
  |    +- reads Gemma outputs from state.db                |
  |    +- calls Claude API for synthesis & safety review   |
  |    +- sends HTML email digest                          |
  |    +- alerts on form/safety concerns                   |
  |                                                        |
  |  command-agent (FastAPI, always-on)                    |
  |    +- launchd: ~/Library/LaunchAgents/                 |
  |    +- exposes /stats, /pipelines, /voices, /memory,    |
  |       /openclaw, /repos, /timeline as JSON             |
  |    +- consumed by command.93.fyi via Cloudflare tunnel |
  |    +- RAM-aware (refuses heavy actions <1GB free)      |
  |                                                        |
  +--------------------------------------------------------+


## Local Repos (manual / WIP)

```
  Standalone repos not yet wired into LaunchAgents or CI
  +--------------------------------------------------------+
  |                                                        |
  |  photo-memory          ── X9 SSD → MLX-VLM → catalog   |
  |    +- phase1_dedupe.py (SHA256 dedupe, RAM-aware)      |
  |    +- → photos.93.fyi (Cloudflare Worker, planned)     |
  |                                                        |
  |  finflow               ── Teller API → DuckDB → Polars |
  |    +- FastAPI on :8000 (interactive, Teller Connect)   |
  |    +- finflow.tasks.teller_pull (hourly LaunchAgent,   |
  |       staged 2026-05-09, awaiting load)                |
  |                                                        |
  |  amex-claims-automator ── Playwright → claims-center   |
  |    +- headed Chromium, human-in-loop for MFA           |
  |                                                        |
  |  tui-dashboard         ── Textual global TUI (skeleton)|
  |    +- distinct from process-monitor-dashboard          |
  |                                                        |
  |  house-tracker         ── S. FL property tracker SPA   |
  |    +- React 19 + Vite, Vercel, no custom domain yet    |
  |                                                        |
  +--------------------------------------------------------+
```

## Seedbox (planned)

```
  +--------------------------------------------------------+
  |  find-hub-tracker (PLANNED — not yet deployed)         |
  |    +- polls Google Find Hub Nova API                   |
  |    +- Discord alerts on anomalies                      |
  |    +- pings Healthchecks.io for liveness               |
  +--------------------------------------------------------+
```
```
