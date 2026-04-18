# Quick Start Guide

## Process Monitor Dashboard

Launch the real-time monitoring dashboard:

```bash
python3 ~/karl-infra/services/process-monitor-dashboard.py
```

### What You'll See

Three-column dashboard updating every 5 seconds:

1. **PROCESSES** (left)
   - Nextcloud Photo Sync, Screenshot Parser, Return Receipt Scanner, Photo Memory Pipeline
   - Status: 🔥 Running | ✓ Idle | ❌ Error | ⊙ Pending
   - Shows: last run time, error count

2. **LOCAL LLM** (center)
   - Ollama models and VRAM usage
   - Status: 💤 Idle | 🔥 Loaded
   - Shows: model size, total available

3. **CLAUDE SESSIONS** (right)
   - Recent active Claude Code sessions (past 7 days)
   - Activity: 🔥 Hot (< 5 min) | 🟡 Busy (< 1 hr) | 💤 Idle (> 1 hr)
   - Shows: session size, time since last change

### How to Interpret Status

**Processes:**
- Green check mark = healthy, running on schedule
- Yellow warning = currently executing
- Red X = error on last run
- Gray circle = not yet run or missing log

**Ollama Models:**
- Fire emoji = consuming VRAM (in use)
- Sleep emoji = installed but not loaded
- Shows: model size in GB, inference capability

**Claude Sessions:**
- Red fire = very recent activity (snapshot of work in progress)
- Yellow circle = recently worked on
- Gray sleep = idle session, could unload to free memory

### Terminal Requirements

- **Minimum**: 120 chars wide, 30 lines tall
- **Recommended**: 140+ chars wide, 40+ lines tall
- Must support ANSI colors and Unicode (all modern terminals do)

### Memory Context

Use the total Claude session size to estimate context usage:
- Rough estimate: ~400 tokens per MB
- e.g., 45 MB session ≈ 18,000 tokens

Use the Ollama VRAM to avoid OOM:
- Gemma4-26b = 17 GB
- Gemma4-latest = 9.6 GB
- Llama3.2:1b = 1.3 GB
- Available on Mac Studio: 28.1 GB (minus safety margin)

### Running in Background

Keep the dashboard running in a persistent terminal:

```bash
# Option 1: tmux
tmux new-session -d -s monitor 'python3 ~/karl-infra/services/process-monitor-dashboard.py'
tmux attach -t monitor  # to view

# Option 2: screen
screen -d -m -S monitor python3 ~/karl-infra/services/process-monitor-dashboard.py
screen -r monitor  # to view

# Option 3: plain background
python3 ~/karl-infra/services/process-monitor-dashboard.py &
# (Ctrl+C in that terminal to stop, or pkill -f process-monitor-dashboard)
```

## Troubleshooting

**No Ollama models shown?**
- Ensure Ollama app is running: `ollama ps`
- Check installed models: `ollama list`

**No Claude sessions shown?**
- Must have used Claude Code recently (creates session cache)
- Sessions older than 7 days are filtered out
- Check: `ls -lah ~/.claude/projects/` for session dirs

**Wrong terminal size?**
- The dashboard should auto-fit to your terminal width
- For best experience, expand to 140+ chars and 40+ lines
- Content truncates gracefully on smaller screens

**Processes showing 'Pending'?**
- Log files don't exist yet (first run state)
- Run the process once, then refresh the dashboard
- Check log paths: `~/.local/share/*/logs`

## Related Documentation

- `/karl-infra/infra/process-monitor-dashboard.md` — Full technical details
- `/karl-infra/infra/local-ai.md` — Ollama config & memory management
- `~/.claude/CLAUDE.md` — Claude Code instructions & coordination rules
- `/karl-infra/ARCHITECTURE.md` — System overview

## Source Code

Location: `~/karl-infra/services/process-monitor-dashboard.py`

Implementation:
- Pure Python 3 (stdlib only)
- ANSI color codes for cross-terminal compatibility
- Unicode box drawing for visual structure
- Real-time data via `subprocess` calls to `ollama` CLI
- Filesystem scanning for Claude sessions
- ~500 lines, well-documented

## Performance

- Memory usage: < 50 MB
- CPU usage: minimal (sleeps between refreshes)
- Network: none (local only)
- Disk I/O: light (process logs + Claude session dirs)

Safe to run 24/7 without performance impact.
