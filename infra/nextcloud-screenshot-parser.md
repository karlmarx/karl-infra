# Nextcloud Screenshot Parser

Hourly job that pulls Android screenshots off Nextcloud, runs each one through MLX-VLM for classification + date extraction, files them by category on the X9 SSD, and creates Todoist tasks for time-sensitive items (returns, deadlines, tickets, warranties, receipts).

## Status

**DEAD as of 2026-04-22 — same `EX_CONFIG (78)` bugs as `nextcloud-android-sync`.** See [nextcloud-android-sync.md](nextcloud-android-sync.md#known-issues--outage-2026-04-22) for the fix recipe. Both plists need the same two edits (uv path + real password).

## Components

| Piece | Path |
|-------|------|
| Script | `~/karl-infra/services/nextcloud-screenshot-parser.py` |
| LaunchAgent | `~/Library/LaunchAgents/com.karlmarx.screenshot-parser.plist` |
| Label | `com.karlmarx.screenshot-parser` |
| Schedule | `StartInterval: 3600` (hourly) + `RunAtLoad: true` |
| Logs | `~/.local/share/nextcloud-sync/screenshot-{stdout,stderr,parser}.log` |
| Catalog | `~/.local/share/nextcloud-sync/document-catalog.json` |

## What it does

1. **Pull**: WebDAV `PROPFIND` on `/InstantUpload/Screenshots/` → list image files (`.jpg/.jpeg/.png/.gif/.webp`).
2. **Download** each to `/Volumes/Crucial X9/photos/incoming/screenshots/`.
3. **Classify** via MLX-VLM (`mlx_vlm.generate.generate_image_description`) into one of:
   - `return_label` — shipping return, RMA, barcode
   - `receipt` — purchase receipt, invoice
   - `warranty` — warranty info, guarantee card
   - `ticket` — event, appointment, confirmation
   - `deadline` — bill, payment due, deadline notice
   - `other` — anything else worth keeping
4. **Extract dates** via a second MLX-VLM call (return deadlines, expiry, event dates).
5. **File** by category to `/Volumes/Crucial X9/documents/<category>/<filename>`.
6. **Catalog** the result in `document-catalog.json` (timestamp, path, type, dates).
7. **Create Todoist task** by appending to `~/karl-todo/todo.md` (which the karl-todo cron pushes to Todoist within 15 min). One task per categorized screenshot, except `other`. Due-date is whatever MLX-VLM extracted, if any.
8. **DELETE** `/InstantUpload/Screenshots/` on Nextcloud after the batch.

## MLX-VLM dependency

Each screenshot triggers two `python3 -c '... mlx_vlm.generate ...'` subprocess calls. There is **no shared server** — the script spawns mlx-vlm cold per call (60 s timeout each). For a backlog of 20 screenshots that's ~40 cold starts at ~5–15 s each.

This is the slow path. If/when this is rebuilt, route through the `mlx-vlm` provider on `:8080` (already running for openclaw + workout pipeline) instead of the bare `mlx_vlm.generate` import. See `infra/local-ai.md` for the shared server pattern.

## Failure modes

- **MLX-VLM import fails** → all screenshots get classified `other`, no TODOs created (graceful but silent — check logs).
- **PROPFIND timeout** (10 s curl, 15 s subprocess) → log warning, return empty list.
- **karl-todo missing** → log warning, skip TODO creation, file the screenshot anyway.
- **DELETE timeout** (5 s curl, 10 s subprocess) → log warning, files stay on Nextcloud (next run will re-download — duplicate-detected by filename, so it's a no-op).

## Manual run

```bash
export NEXTCLOUD_PASSWORD='<real-password>'
/Users/kmx/.local/bin/uv run ~/karl-infra/services/nextcloud-screenshot-parser.py
```

## Cross-references

- [nextcloud-android-sync.md](nextcloud-android-sync.md) — sibling job, same plist bugs, same fix.
- [local-ai.md](local-ai.md) — MLX-VLM server pattern this script *should* be using.
- [openclaw.md](openclaw.md) — would be the right routing layer once the screenshot parser switches to the shared `:8080` server.
- `~/karl-todo/CLAUDE.md` — the Todoist mirror contract this script appends to.
- [../ARCHITECTURE.md](../ARCHITECTURE.md)
