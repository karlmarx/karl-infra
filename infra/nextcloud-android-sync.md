# Nextcloud Android Photo Sync

Hourly job that pulls Android camera uploads off Nextcloud, drops them on the X9 SSD, and deletes the originals. Distinct from `com.kmx.nextcloud-ingest` (rclone, video-only, 30 min) — this one is the Python/curl polling job for the `InstantUpload/Camera/` photo folder.

## Status

> **DEAD as of 2026-04-22 — `EX_CONFIG (78)` from launchd. See "Known Issues / Outage" below before touching anything else.**

When healthy: hourly poll, ~tens of MB per cycle, idempotent (skips files already on X9), logs to `~/.local/share/nextcloud-sync/`.

## Components

| Piece | Path |
|-------|------|
| Script | `~/karl-infra/services/nextcloud-android-sync.py` |
| LaunchAgent | `~/Library/LaunchAgents/com.karlmarx.nextcloud-sync.plist` |
| Label | `com.karlmarx.nextcloud-sync` |
| Schedule | `StartInterval: 3600` (hourly) + `RunAtLoad: true` |
| Logs | `~/.local/share/nextcloud-sync/{stdout,stderr,sync}.log` |

## Data flow

```
[Android Nextcloud app: auto-upload]
    ↓
[Nextcloud server: /InstantUpload/Camera/*.jpg]
    ↓ (com.karlmarx.nextcloud-sync, hourly, curl PROPFIND + GET)
[/Volumes/Crucial X9/photos/incoming/<filename>]
    ↓ (DELETE on /InstantUpload/Camera/ after successful download)
[Nextcloud folder cleared]
```

The downstream consumer is whatever else watches `/Volumes/Crucial X9/photos/incoming/` — currently `workout_watcher.py` (videos only, ignores images) and the photo-memory pipeline.

## How it works

`nextcloud-android-sync.py` is plain `curl` over WebDAV against `https://karlmarx.tofino.usbx.me/nextcloud`:

1. `PROPFIND` on `/remote.php/dav/files/karlmarx/InstantUpload/Camera/` → parse `<d:href>` entries.
2. For each file, skip if already on X9 (filename match), else `GET` it to `/Volumes/Crucial X9/photos/incoming/<filename>`.
3. After all downloads succeed, issue a single `DELETE` on the entire folder. This nukes everything in `InstantUpload/Camera/` — make sure all wanted files were downloaded first. (The Android app recreates the folder on next upload.)

Failure modes (handled):

- X9 not mounted → log error, exit non-zero, no cleanup.
- `NEXTCLOUD_PASSWORD` unset → log error, exit 1.
- PROPFIND non-200 → log warning, exit without cleanup.
- Per-file download failure → log warning, continue with rest, **still triggers cleanup** if the overall function returns True (it returns True on empty-folder case but not on PROPFIND failure — partial download losses are possible if individual GETs fail silently).

## Known Issues / Outage (2026-04-22)

**The pipeline has been dead since 2026-04-22.** launchd reports `EX_CONFIG (78)` and refuses to retry. Two root causes, both in the plist:

### Bug 1 — uv path is wrong

```xml
<string>/opt/homebrew/bin/uv</string>
```

Actual location of `uv` is `/Users/kmx/.local/bin/uv` (installed via the official `uv` installer, not Homebrew). launchd can't exec the binary, so the agent dies before the script even starts.

### Bug 2 — placeholder password

```xml
<key>NEXTCLOUD_PASSWORD</key>
<string>12345678aA</string>
```

That is the `app-nextcloud` install-time placeholder, not the real Nextcloud password. The real one is in KeePass at `~/Nextcloud/Documents/Passwords.kdbx` under "Ultra.cc seedbox" (verify the entry name with Karl before patching — there are several Ultra.cc entries).

> Note: `com.karlmarx.screenshot-parser.plist` has the **same two bugs** with the same root cause. Fix both at once.

### Why a simple `kickstart` won't work

`EX_CONFIG (78)` triggers launchd's permanent backoff state. `launchctl kickstart -k gui/$UID/com.karlmarx.nextcloud-sync` will keep returning `Could not find service` or refuse to fire. You must `unload` then `load` to clear the state.

### Fix recipe

```bash
# 1. Edit the plist
$EDITOR ~/Library/LaunchAgents/com.karlmarx.nextcloud-sync.plist
#    - change /opt/homebrew/bin/uv → /Users/kmx/.local/bin/uv
#    - replace NEXTCLOUD_PASSWORD value with the real password

# 2. Reload (NOT kickstart — the EX_CONFIG state is sticky)
launchctl unload ~/Library/LaunchAgents/com.karlmarx.nextcloud-sync.plist
launchctl load   ~/Library/LaunchAgents/com.karlmarx.nextcloud-sync.plist

# 3. Verify it actually started
launchctl list | grep com.karlmarx.nextcloud-sync
#    First column should be a PID (running) or 0 (last run succeeded), NOT 78.

# 4. Tail to confirm a real sync cycle
tail -f ~/.local/share/nextcloud-sync/sync.log
```

Repeat the same three steps for `com.karlmarx.screenshot-parser.plist`.

### Long-term fix

Move the password out of the plist entirely:

- Read it from `security find-generic-password -s nextcloud-sync -w` at script start.
- Or read from a `0600` file at `~/.config/nextcloud-sync/secret`.

Either keeps the plist diff-able / commit-able without leaking creds. (Same fix applies to the openclaw plaintext-secrets migration tracked in `infra/openclaw.md`.)

## Manual run

```bash
export NEXTCLOUD_PASSWORD='<real-password>'
/Users/kmx/.local/bin/uv run ~/karl-infra/services/nextcloud-android-sync.py
```

## Cross-references

- [nextcloud-screenshot-parser.md](nextcloud-screenshot-parser.md) — sibling job on the Screenshots folder; same plist bugs.
- [workout-pipeline.md](workout-pipeline.md) — downstream consumer of `/Volumes/Crucial X9/photos/incoming/` (videos only).
- [process-monitor-dashboard.md](process-monitor-dashboard.md) — surfaces this job's status in the terminal dashboard.
- [openclaw.md](openclaw.md) — same plaintext-secrets-in-plist anti-pattern.
- [../ARCHITECTURE.md](../ARCHITECTURE.md)
