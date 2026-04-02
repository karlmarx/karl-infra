# Local Windows Workstation

## Overview

Windows 11 Pro workstation serving as the primary development machine and host for local automation services.

## Always-On Services

| Service | Runtime | Repo | Purpose |
|---------|---------|------|---------|
| OpenClaw | Claude Code (Node.js) | — | AI assistant gateway |
| openclaw-watchdog | Python (Rich + Playwright) | [karlmarx/openclaw-watchdog](https://github.com/karlmarx/openclaw-watchdog) | Monitors OpenClaw, prevents sleep, Discord alerts |
| claude-pipeline | Python (watchdog) | [karlmarx/claude-pipeline](https://github.com/karlmarx/claude-pipeline) | File watcher for Nextcloud -> OpenClaw routing |
| property-scout | Python (31KB, scheduled) | (in openclaw-watchdog) | Daily 8am ET South Florida MLS property alerts via email |

## On-Demand Tools

| Tool | Runtime | Repo | Purpose |
|------|---------|------|---------|
| gemini-auto | Playwright (JS) | [karlmarx/gemini-auto](https://github.com/karlmarx/gemini-auto) | Gemini UI automation via Chrome CDP (port 9222) |
| google-migration-toolkit | Python | [karlmarx/google-migration-toolkit](https://github.com/karlmarx/google-migration-toolkit) | Google account migration scripts |

## Key Filesystem Paths

| Path | Purpose |
|------|---------|
| `~/.openclaw/workspace/` | OpenClaw workspaces (per-project) |
| `~/Nextcloud/Documents/` | Nextcloud sync root |
| `~/Nextcloud/Documents/inbox/` | claude-pipeline watch directory |
| `~/Nextcloud/Documents/TODO.md` | Shared TODO list (syncs to all devices) |
| `~/Nextcloud/Documents/todo_dashboard.html` | TODO dashboard (opens on boot) |
| `~/Nextcloud/Documents/Passwords_clean.kdbx` | KeePass database |

## Development Environment

| Tool | Purpose |
|------|---------|
| Claude Code | Primary AI coding assistant |
| Gemini CLI | Secondary AI assistant |
| Tailscale | SSH remote access from phone/other devices |
| Git Bash | Shell environment |
| VS Code | Editor (when not using Claude Code) |

See [karlmarx/dev-setup](https://github.com/karlmarx/dev-setup) for the full dev environment configuration.

## Migration Plans

Several workstation-dependent tasks are planned for migration to dedicated infrastructure (ultra.cc seedbox or MacBook server):
- find-hub-tracker (already planned for ultra.cc)
- Other periodic automation ([find-hub-tracker#3](https://github.com/karlmarx/find-hub-tracker/issues/3))
