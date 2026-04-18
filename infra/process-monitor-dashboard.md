# Process Monitor Dashboard

## Overview

Real-time terminal dashboard for monitoring local infrastructure on Mac Studio M4 Max:
- **Background processes** (Nextcloud sync, screenshot parser, etc.)
- **Local LLM activity** (Ollama models, VRAM, loaded status)
- **Claude session tracking** (recent sessions, memory usage, activity level)

Single-pane, three-column layout with ANSI colors and Unicode box drawing. Refreshes every 5 seconds. Pure Python (no external dependencies).

## Location

`~/karl-infra/services/process-monitor-dashboard.py`

## Sections

### Column 1: Processes
Monitors background automation tasks:
- **Nextcloud Photo Sync** (hourly)
- **Screenshot Parser** (hourly)
- **Return Receipt Scanner** (6h)
- **Photo Memory Pipeline** (on-demand)

Status indicators:
- `🔥 RUNNING` (red) — task currently executing
- `✓ Idle` (green) — completed, waiting for next interval
- `❌ ERROR` (red) — last run failed
- `⊙ Pending` (gray) — never run or log missing

Shows: last run time (relative), error count, summary stats.

### Column 2: Local LLM (Ollama)
Real-time inventory of Ollama models:
- Model name, size (GB), status
- `💤 idle` (gray) — installed, not loaded
- `🔥 LOADED` (yellow) — currently consuming VRAM

Summary: Total VRAM in use, total available.

Source: `ollama list` and `ollama ps` commands.

### Column 3: Claude Sessions
Recent active Claude Code sessions from `~/.claude/projects/`:
- Session path (truncated display name)
- Size (MB), last activity (relative time)
- Activity level: 
  - `🔥` (red) — modified in last 5 minutes
  - `🟡` (yellow) — modified in last hour
  - `💤` (gray) — idle > 1 hour

Shows top 5 sessions from past 7 days (by recency).

Rough token estimate: ~400 tokens per MB (useful for context budgeting).

## Running the Dashboard

```bash
python3 ~/karl-infra/services/process-monitor-dashboard.py
```

The script runs in an infinite loop (Ctrl+C to exit). Terminal must support ANSI colors and Unicode box drawing (all modern terminals do).

### Terminal Dimensions
- **Recommended**: 140+ chars wide, 40+ lines tall
- **Minimum**: 120 chars wide, 30+ lines
- Columns adjust to available width; content truncates gracefully

## Design Rationale

### Why Pure Python + No Deps?
- Runs on any Mac with Python 3.x (no pip install needed)
- No rich/colorama/etc. to maintain
- Fast startup, lightweight memory
- Direct integration with `ollama` and filesystem

### Why Three Columns?
- **Holistic view** of the three layers of local work:
  1. Scheduled automation (processes)
  2. AI inference (Ollama)
  3. Development sessions (Claude)
- Fits one logical screen; no scrolling needed

### Why 5-Second Refresh?
- Fast enough to catch state changes (model loads, session activity)
- Slow enough to be readable and not CPU-heavy
- Matches typical human attention span for a monitoring dashboard

## Implementation Details

### Ollama Stats (`get_ollama_stats()`)
- Parses `ollama list` output (name, size, modified time)
- Queries `ollama ps` for running models (determines "loaded" status)
- Extracts size: handles "9.6 GB", "1.3 GB", "500 MB" via regex
- Result: `List[OllamaModel]` sorted by loaded state + size

### Claude Sessions (`get_claude_sessions()`)
- Scans `~/.claude/projects/` for directories
- Filters: only sessions modified in past 7 days
- Calculates size via recursive file traversal
- Token estimate: `size_mb * 400` (rough heuristic from observation)
- Result: `List[ClaudeSession]` top 5 by recency

### Process Status (`update_process_status()`)
- Reads last line of process log file
- Regex: extract ISO timestamp from `[2026-04-18T12:22:32...]` format
- Keywords: "ERROR" → error state, "successfully"/"complete" → idle, "Starting"/"Processing" → running
- Calculates next run: last_run + interval
- Graceful fallback: if no log exists, status = "pending"

### Color & Style
```
✓ Green (#92m)     — healthy, idle, good
⚡ Yellow (#93m)   — running, busy, caution
❌ Red (#91m)      — error, critical
💤 Gray (#90m)     — idle/dormant, low priority
🔥 Accent           — high activity, hot spot
```

ANSI escape codes work across SSH, iTerm2, Terminal.app, VS Code.

## Future Enhancements

- **Sparklines**: `render_sparkline()` stub ready for VRAM trend visualization
- **Log tailing**: `[l]` key to show last N lines of any process log
- **Error drill-down**: `[e]` key to jump to most recent error
- **Interactive**: could add model unload/reload, session open commands
- **Persistence**: could log dashboard history (CPU, memory, uptime) to SQLite
- **Remote**: could report to monitoring service (Healthchecks.io, etc.)

## Related Docs

- `/karl-infra/infra/local-ai.md` — Ollama config, MLX-VLM, memory management rules
- `~/.claude/CLAUDE.md` — Global Claude Code instructions, coordination rules
- `/karl-infra/ARCHITECTURE.md` — System overview, deployment targets
