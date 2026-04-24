# Workout Video Analysis Pipeline

## Purpose

Continuous background pipeline that watches for new workout videos uploaded from Karl's phone, processes each video with local Gemma (MLX-VLM, Apple Silicon native) to extract frames and generate per-frame analysis, then periodically sends the Gemma-generated observations to the same MLX-VLM Gemma model for safety and form feedback synthesis. The system creates a daily digest email with no API costs.

**Why this architecture?** Cost efficiency: Gemma runs locally on unified memory (no CPU↔GPU copy overhead), and both watcher + digest share the same MLX-VLM server instance. Zero API costs while getting nuanced form analysis.

## Components

### 1. **workout_watcher.py** — Gemma Video Processing Service

- **Location**: `~/karl-infra/services/workout_watcher.py`
- **Schedule**: LaunchAgent `com.kmx.workout-ingest` fires every 15 minutes (`StartInterval: 900`)
- **Input**: Watches `/Volumes/Crucial X9/photos/incoming/` recursively for `.mp4` files
- **Filter criteria**:
  - File size: 5 MB to 2 GB (excludes thumbnails and pathological cases)
  - Modified time: within 30 days (new files; handles ~144-file Nextcloud backlog on first run)
  - Not already in state DB (by SHA256 of first 1 MiB)
- **Processing per video**:
  - Compute SHA256 of first 1 MiB (idempotency key)
  - Call `process_video.process(video_path)` from local-vlm-analysis project
  - Frames are extracted via ffmpeg (scene-change detection + uniform sampling)
  - Per-frame analysis: triage → universal → workout (3-layer Gemma pipeline via `http://localhost:8080`)
  - Output: `data/videos/<sha>.json` with full frame-by-frame metadata
- **State tracking**: Updates SQLite `~/.local/share/workout-pipeline/state.db` with `gemma_done_at` timestamp
- **Limits**:
  - Process max 5 videos per run (configurable via `MAX_PER_RUN` env var) to prevent OOM
  - RAM guard: exits cleanly if available RAM < 200 MB (LaunchAgent retries in 15 min)
- **Dependencies**: `psutil` (added to `local-vlm-analysis/pyproject.toml`)
- **Error handling**: retries up to 3 times on failure, logs error to state DB, continues with next video

### 2. **workout_digest.py** — MLX-VLM Gemma Analysis + Email Service

- **Location**: `~/karl-infra/services/workout_digest.py`
- **Schedule**: LaunchAgent `com.kmx.workout-digest` fires daily at 07:00 UTC (`StartCalendarInterval: {Hour: 7, Minute: 0}`)
- **Input**: All rows in state DB WHERE `gemma_done_at IS NOT NULL AND claude_done_at IS NULL`
- **Processing**:
  - Load each video's `data/videos/<sha>.json`
  - Extract `workout_summary` dict (exercises, equipment, body focus, intensity, environment)
  - Collect up to 5 unique `form_notes` from individual frames
  - Only include videos where `is_workout == true` (filters out rest frames, non-workouts)
- **MLX-VLM call**:
  - Model: `mlx-community/gemma-4-26b-a4b-it-8bit` (same as watcher, reuses running server)
  - Endpoint: `http://localhost:8080/v1` (OpenAI-compatible)
  - Prompt: comprehensive daily digest request with all videos in one call
  - Max tokens: 2048 (accommodates ~10-50 videos per digest, typical for daily)
- **Alert detection**: Scans Claude response for keywords (`injury risk`, `dangerous`, `avoid`, `pain`, `strain`, `hyperextend`, `improper form`)
  - If found: email subject becomes `[ALERT] Workout Form Digest — {date}`
  - Red warning banner in HTML email
- **Email delivery**:
  - Via Gmail SMTP SSL (port 465)
  - To: `karlmarx9193@gmail.com` (configurable via env var)
  - HTML + plain-text multipart message
  - App Password required (not account password; see credentials section)
- **State tracking**: Updates DB with `claude_done_at` and `emailed_at` timestamps
- **Skip conditions**:
  - No pending videos → exit 0 (no email)
  - RAM state `tight` or `critical` → exit 0 (no email, retry next day)
  - No workout videos in pending set → exit 0

### 3. **Nextcloud Integration**

The existing `nextcloud-ingest.sh` LaunchAgent (runs every 30 min, `com.kmx.nextcloud-ingest`) already handles the phone→Mac piece:

- Polls Nextcloud `InstantUpload/Camera/` via rclone
- Moves new `.mp4` files to `/Volumes/Crucial X9/photos/incoming/Camera/`
- **No changes needed** — this pipeline watches the X9 destination after ingest

Current state: 144 `.mp4` files exist in Nextcloud but have not yet been moved to X9. First run of `workout_watcher.py` will process them in batches over ~7 hours (5 videos/run × ~15-30 min per Gemma run).

### 4. **Shared State Database**

- **Path**: `~/.local/share/workout-pipeline/state.db`
- **Format**: SQLite with WAL mode (safe concurrent access)
- **Schema**:
  ```sql
  CREATE TABLE videos (
      sha TEXT PRIMARY KEY,
      source_path TEXT NOT NULL,
      file_name TEXT NOT NULL,
      size_bytes INTEGER NOT NULL,
      discovered_at TEXT DEFAULT (datetime('now')),
      gemma_done_at TEXT,
      gemma_json_path TEXT,
      claude_done_at TEXT,
      emailed_at TEXT,
      gemma_error TEXT,
      retry_count INTEGER DEFAULT 0
  );
  ```
- **Flow**: watcher populates `discovered_at`, writes `gemma_done_at`. Digest reads and writes `claude_done_at`, `emailed_at`.

## Data Flow

```
[Phone Camera] 
    ↓ (Nextcloud auto-upload)
[Nextcloud: InstantUpload/Camera/VID_*.mp4]
    ↓ (com.kmx.nextcloud-ingest, rclone moveto every 30 min)
[/Volumes/Crucial X9/photos/incoming/Camera/VID_*.mp4]
    ↓ (com.kmx.workout-ingest every 15 min)
[workout_watcher.py]
    │─ discover_videos(): walk X9, filter size/age/dedup
    │─ process_one(): call process_video.process()
    │     ├─ extract frames via ffmpeg
    │     ├─ per-frame Gemma (triage→universal→workout)
    │     └─ write data/videos/<sha>.json
    │─ update state.db: gemma_done_at
    │
[data/videos/<sha>.json] (immutable Gemma output)
    ↓ (com.kmx.workout-digest daily at 07:00)
[workout_digest.py]
    │─ load pending videos from state.db
    │─ build_video_summary(): extract workout_summary + form_notes
    │─ build_prompt(): compose digest prompt
    │─ call MLX-VLM Gemma: one batched call for all videos
    │─ detect alerts: scan response for injury keywords
    │─ render_html_email(): create multipart message
    │─ send via Gmail SMTP
    │─ update state.db: claude_done_at, emailed_at
    │
[Email: [Workout] Daily Form Digest — {date}] → karlmarx9193@gmail.com
```

## MLX-VLM Server Dependency

The watcher requires `http://localhost:8080/v1/models` to be up and responding. This is a **prerequisite**, not managed by the pipeline.

**Start MLX-VLM manually** (before LaunchAgents):
```bash
mlx_vlm.server --model mlx-community/gemma-4-26b-a4b-it-8bit --host 127.0.0.1 --port 8080
```

The watcher checks at startup and exits cleanly if MLX-VLM is down (LaunchAgent retries in 15 min).

## Credentials

One LaunchAgent plist contains a placeholder that must be filled in before the service runs:

### `com.kmx.workout-ingest.plist`
- No credentials needed (reads from X9 SSD only)

### `com.kmx.workout-digest.plist`
Must fill in before first run:
```xml
<key>GMAIL_APP_PASSWORD</key>
<string>xxxx xxxx xxxx xxxx (16 chars, from KeePass Gmail SMTP entry)</string>
```

**Gmail App Password**: Retrieve from KeePass → Search for "Gmail" → Look for "SMTP" or "App Password" entry. Standard Google account setting, different from account password.

**MLX-VLM Dependency**: MLX-VLM server must be running (same process used by watcher). The script checks for availability at startup and exits cleanly if MLX-VLM is down. Start with: `mlx_vlm.server --model mlx-community/gemma-4-26b-a4b-it-8bit --host 127.0.0.1 --port 8080`

## RAM Management

Both scripts integrate RAM guards per `~/karl-infra/infra/local-ai.md`:

### workout_watcher.py (Gemma)
- **Startup**: Check MLX-VLM and RAM. Exit if critical.
- **Per-video**: Check RAM before `process_one()`
  - `< 200 MB`: log + exit (LaunchAgent retries in 15 min)
  - `200–500 MB`: sleep 5 min, recheck once, then exit if still tight
  - `≥ 500 MB`: proceed (with caution log if 500–1 GB)
- **Mid-run**: Stop processing videos if RAM hits critical threshold mid-run
- **Max per run**: 5 videos (configurable via `MAX_PER_RUN` env var)

### workout_digest.py (Claude API)
- **Startup**: Skip if RAM is tight or critical (no email, retry next day)
- **Runtime**: Pure API call + SMTP, no local inference, minimal RAM overhead

## Logs

Both services write rotating logs:

| Service | Log Path | Rotation |
|---------|----------|----------|
| watcher | `~/.local/share/workout-pipeline/ingest-stdout.log` | 5 MB max, 3 backups |
| digest | `~/.local/share/workout-pipeline/digest-stdout.log` | 5 MB max, 3 backups |

Error output also goes to `*-stderr.log`. LaunchAgent stderr redirects to `StandardErrorPath` in plist.

Check logs when debugging:
```bash
tail -f ~/.local/share/workout-pipeline/ingest-stdout.log
```

## Manual Testing

### Test watcher (discovery only, no Gemma)
```bash
WORKOUT_SCAN_ROOT=/Volumes/Crucial\ X9/photos/incoming \
  WORKOUT_DATA_ROOT=/Users/kmx/projects/local-vlm-analysis \
  uv run --project /Users/kmx/projects/local-vlm-analysis \
  ~/karl-infra/services/workout_watcher.py --list-only
```

Expected output: logs of discovered `.mp4` files with SHAs and sizes.

### Test digest (dry run, no email send)
```bash
# Make sure MLX-VLM is running first: mlx_vlm.server --model ... &
WORKOUT_DATA_ROOT=/Users/kmx/projects/local-vlm-analysis \
  uv run ~/karl-infra/services/workout_digest.py --dry-run
```

Expected output: HTML email body printed to stdout (Gemma-synthesized form feedback).

### Manually trigger digest
```bash
launchctl start com.kmx.workout-digest
```

### Manual list state DB
```bash
sqlite3 ~/.local/share/workout-pipeline/state.db "SELECT file_name, gemma_done_at, claude_done_at, emailed_at FROM videos;"
```

## Known Limitations & Future Work

1. **No video file cleanup**: Processed videos remain on X9 SSD. Manual cleanup or a separate retention policy needed.
2. **No retries on transient failures**: If MLX-VLM or Gmail SMTP is temporarily down, the digest skips that day (no retry queue). Consider Vercel Queues or similar for durable delivery.
3. **Form feedback specificity**: Gemma receives frame-level observations but no video playback or slow-motion analysis. May miss subtle form issues.
4. **No form archive**: Digests are emailed but not permanently stored in a queryable database. Consider archiving digests to SQLite or email archive.

## Operational Runbook

### First-time setup

1. MLX-VLM must be running (same server used by watcher for frame extraction)
2. Fill in credentials in digest plist (Gmail App Password only)
3. Load LaunchAgents:
   ```bash
   launchctl load ~/Library/LaunchAgents/com.kmx.workout-ingest.plist
   launchctl load ~/Library/LaunchAgents/com.kmx.workout-digest.plist
   ```
4. Verify with `launchctl list | grep workout` — should show both agents loaded
5. Monitor logs: `tail -f ~/.local/share/workout-pipeline/*.log`
6. Expect first digest email after 07:00 UTC the next morning (if videos are pending)

### Troubleshooting

**No videos discovered:**
- Check X9 SSD is mounted: `ls /Volumes/Crucial\ X9`
- Check Nextcloud files exist: `rclone lsjson nextcloud:InstantUpload/Camera/ | head`
- Check state DB for prior runs: `sqlite3 ~/.local/share/workout-pipeline/state.db "SELECT COUNT(*) FROM videos;"`

**Gemma failures:**
- Check MLX-VLM is running: `curl http://localhost:8080/v1/models`
- Check logs for error: `tail -20 ~/.local/share/workout-pipeline/ingest-stdout.log`
- Check RAM: `top -l1 | grep PhysMem`

**MLX-VLM not available:**
- Check MLX-VLM is running: `curl http://localhost:8080/v1/models`
- Start MLX-VLM: `mlx_vlm.server --model mlx-community/gemma-4-26b-a4b-it-8bit --host 127.0.0.1 --port 8080`
- Check digest logs: `tail -20 ~/.local/share/workout-pipeline/digest-stdout.log`

**Email not sending:**
- Check credentials in plist are filled in (not `FILL_IN_*`)
- Test Gmail app password manually: `python3 -c "import smtplib; s=smtplib.SMTP_SSL('smtp.gmail.com'); s.login('karlmarx9193@gmail.com', 'xxxx xxxx xxxx xxxx'); s.quit(); print('OK')"`
- Check digest logs: `tail -20 ~/.local/share/workout-pipeline/digest-stdout.log`

**RAM guard stopping watcher:**
- Check available RAM: `psutil.virtual_memory().available / 1024**3` (should be > 1 GB)
- Check for other heavy processes: `top -n 5 -o vsize` (sorted by virtual memory)
- Increase free RAM or adjust `MAX_PER_RUN=3` in ingest plist EnvironmentVariables

## Related Infrastructure

- **Local VLM analysis**: `/Users/kmx/projects/local-vlm-analysis/` (Gemma pipeline reused)
- **Nextcloud phone sync**: `~/karl-infra/services/nextcloud-ingest.sh` (file ingestion, no changes needed)
- **RAM coordination**: `~/.claude/coordination.md` (multi-session RAM guard protocol)
- **Background process monitor**: `~/karl-infra/services/process-monitor-dashboard.py` (can add workout pipeline to it)
