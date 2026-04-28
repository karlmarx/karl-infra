# tui-dashboard

A Textual-based terminal dashboard intended as Karl's single-pane "global status" view: deploys, seedbox, lights, agent, clock. **Distinct from `process-monitor-dashboard`** — see comparison below.

## Purpose

One `python dashboard.py` that opens a TUI showing live state for everything Karl runs across the surface area: Vercel deploys, GitLab repos, Ultra.cc seedbox, WiZ bulbs, OpenClaw cron jobs, Supabase stats, the agent. Vision is "global remote control" rather than "what is my Mac doing right now."

## Stack

| Layer | Tech |
|-------|------|
| Runtime | Python 3 |
| TUI | Textual ≥ 0.52 |
| HTTP | httpx ≥ 0.27 (planned data fetches) |

Dependencies live in `requirements.txt`, not `pyproject.toml`. No `uv` integration yet.

## How it runs

Manual on-demand. No LaunchAgent, no schedule.

```bash
cd ~/tui-dashboard
pip install -r requirements.txt   # or: uv venv && uv pip install -r requirements.txt
python dashboard.py
```

Bindings: `q` quit, `r` refresh (currently a no-op `notify`).

## Layout

Two columns, four panels:

| Panel | Source | Wired? |
|-------|--------|--------|
| 🚀 Projects (TrickAdvisor, nwbfit, nwb-yoga, nwb-plan) | Hardcoded list | Static text only |
| 🖥️ Seedbox (`tofino.usbx.me`) | SSH / ruTorrent HTTP | Not wired |
| 💡 Lights | WiZ UDP (`192.168.68.255:38899`) | Not wired |
| 🤖 Agent (193) | OpenClaw API | Not wired |
| 🕐 Clock | Local datetime, 1 s tick | ✅ working |

## vs. process-monitor-dashboard

These are different products that should not be merged:

| | **`tui-dashboard`** | **`process-monitor-dashboard`** ([infra/process-monitor-dashboard.md](process-monitor-dashboard.md)) |
|---|---|---|
| Scope | "Everything Karl cares about" — projects, seedbox, lights, agent, deploys | Mac Studio local state — background processes, Ollama models, Claude sessions |
| Framework | Textual (rich widgets, CSS, reactive) | Pure stdlib Python (ANSI escapes, `print`) |
| Data sources | Remote: Vercel API, GitLab API, ruTorrent, WiZ UDP, OpenClaw, Supabase | Local: log files, `ollama list/ps`, `~/.claude/projects/` directory walk |
| Refresh | Manual `r` keypress (planned) | Auto every 5 seconds |
| Where it runs | Anywhere with network access to the data sources | Mac Studio only (reads local launchd-managed logs) |
| Status | Skeleton — only the clock works | Production — used as the iTerm2 "Process Monitor" profile |
| Dependencies | `textual`, `httpx` | None (stdlib only) |

If `tui-dashboard` ever ships, the natural division of labor is: `process-monitor-dashboard` for "is the Mac OK," `tui-dashboard` for "is the surface area OK."

## Status

**Skeleton — only the clock works.** Last meaningful change: `2026-04-02` (`4539423 fix: %-d strftime not supported on Windows`). Four commits; the most recent commit before that was `8458920 refactor: strip to placeholder skeleton — get it running first`.

Every panel except the clock is a `PlaceholderPanel` with hardcoded `"[dim]not yet wired[/dim]"` lines.

`IDEAS.md` is the working backlog (high/medium/low value items, with API hints per source).

## Open questions / known issues

- **A GitLab PAT is committed in `IDEAS.md`** (`glpat-…`). Treat as compromised; rotate before the repo ever goes public.
- WiZ control only works on Karl's `asdfjkl` Wi-Fi network (Deco subnet `192.168.68.x`). Won't function from Tailscale or remote.
- WiZ control script referenced is the Windows path `C:\Users\50420\.openclaw\workspace\wiz_lights.py`. Mac-side script lives at `~/.openclaw/workspace/wiz_lights.py` per IDEAS.md notes.
- Stack choice (Python+Textual) was tentatively settled but `IDEAS.md`/README still list "TBD" with Node+ink and Go+bubbletea as alternatives.
- No CI, no tests, no `pyproject.toml`.

## Cross-references

- [process-monitor-dashboard.md](process-monitor-dashboard.md) — the sibling/complementary local TUI
- [openclaw.md](openclaw.md) — agent panel data source (when wired)
- WiZ control script: `~/.openclaw/workspace/wiz_lights.py`
- [../ARCHITECTURE.md](../ARCHITECTURE.md)
