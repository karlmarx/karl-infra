#!/usr/bin/env python
"""
Nextcloud Android Photo Backup Pipeline

Syncs photos from Nextcloud Android folder to external drive (/Volumes/Crucial X9/photos/incoming/)
Deletes originals from Nextcloud after successful backup.

Authentication: Uses basic auth (username + password) via environment variables

Hardening (2026-05-31): on this date a sync run saved Nextcloud HTML *login
pages* as 17 `.jpg` files (curl returns 0 on a 401, and the old code only
checked the curl exit code), then the folder-level cleanup DELETE wiped the
originals off the server — permanent loss of half a photo shoot. To prevent a
repeat:
  1. Per-file HTTP status is captured (`-w %{http_code}`); only 200 is accepted.
  2. Downloaded bytes are validated as real media (magic bytes), never HTML.
  3. Files download to a `.part` temp and are renamed in only on success, so a
     corrupt body never lands at the real path.
  4. Cleanup deletes ONLY the specific remote files verified on the SSD
     (per-file DELETE) — never the whole folder.
  5. A 401/403 aborts the entire run (skips cleanup) and logs an ERROR, instead
     of silently succeeding and then deleting.
"""

import os
import re
import subprocess
from pathlib import Path
from datetime import datetime
from urllib.parse import unquote

# Configuration
NEXTCLOUD_URL = "https://karlmarx.tofino.usbx.me/nextcloud"
NEXTCLOUD_USER = os.getenv("NEXTCLOUD_USER", "karlmarx")
NEXTCLOUD_PASSWORD = os.getenv("NEXTCLOUD_PASSWORD")

# Scope policy (2026-05-19): under /InstantUpload/ ONLY pull from these named
# subfolders. Any other subfolder Karl adds later is ignored by the AI pipeline
# (e.g. if a Nextcloud Android upload rule starts pushing to a new directory,
# we don't want it silently ingested). Outside /InstantUpload/ is unrestricted.
ALLOWED_INSTANTUPLOAD_SUBFOLDERS = ("Camera", "Screenshots")
INSTANTUPLOAD_BASE = "/InstantUpload"
# Backwards-compat alias kept so other scripts that import this name still work
ANDROID_PHOTOS_PATH = f"{INSTANTUPLOAD_BASE}/Camera/"

EXTERNAL_DRIVE = Path("/Volumes/Crucial X9/photos/incoming")
LOG_FILE = Path.home() / ".local/share/nextcloud-sync/sync.log"


class _AuthError(Exception):
    """Raised when the server returns 401/403 — the app password is bad/expired.

    Bubbles up to abort the run so cleanup never deletes originals we couldn't
    actually authenticate to read.
    """


def log(message):
    """Log message to file and stdout."""
    timestamp = datetime.now().isoformat()
    log_entry = f"[{timestamp}] {message}"
    print(log_entry)
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(LOG_FILE, "a") as f:
        f.write(log_entry + "\n")


def _abs_url(href: str) -> str:
    """Build an absolute URL from a PROPFIND href, matching the construction
    that the downloader has always used (kept identical so download and delete
    target the exact same URLs)."""
    return href if href.startswith("http") else f"{NEXTCLOUD_URL}{href}"


def _looks_like_media(path: Path) -> bool:
    """True only if the file's leading magic bytes are a real image/video.

    This is the gate that rejects the Nextcloud HTML login page (the 2026-05-31
    failure mode). Accepts JPEG (incl. Pixel Motion Photos, which are a JPEG with
    an MP4 appended — so we do NOT require a trailing FF D9), PNG, GIF, and
    ISO-BMFF (HEIC/MP4/MOV via the 'ftyp' box). Everything else — HTML, XML,
    empty, truncated-before-the-header — is rejected.
    """
    try:
        with open(path, "rb") as fh:
            head = fh.read(16)
    except OSError:
        return False
    if len(head) < 12:
        return False
    if head[:3] == b"\xff\xd8\xff":            # JPEG / JFIF / Motion Photo
        return True
    if head[:8] == b"\x89PNG\r\n\x1a\n":        # PNG
        return True
    if head[:6] in (b"GIF87a", b"GIF89a"):      # GIF
        return True
    if head[4:8] == b"ftyp":                    # HEIC / MP4 / MOV (ISO-BMFF)
        return True
    return False


def _download_subfolder(subfolder: str) -> tuple[int, int, list[str]]:
    """Download all files from /InstantUpload/<subfolder>/ → EXTERNAL_DRIVE/<subfolder>/.

    Returns (downloaded, skipped, verified_hrefs) where verified_hrefs are the
    remote hrefs now confirmed present on the SSD as valid media (safe to delete
    from the server). Raises _AuthError on a 401/403.
    """
    remote_path = f"{INSTANTUPLOAD_BASE}/{subfolder}/"
    webdav_url = f"{NEXTCLOUD_URL}/remote.php/dav/files/{NEXTCLOUD_USER}{remote_path}"
    local_dir = EXTERNAL_DRIVE / subfolder
    local_dir.mkdir(parents=True, exist_ok=True)

    log(f"Listing {remote_path}")
    list_result = subprocess.run(
        ["curl", "-s", "-k", "-X", "PROPFIND",
         "-w", "\n%{http_code}",
         "-u", f"{NEXTCLOUD_USER}:{NEXTCLOUD_PASSWORD}", webdav_url],
        capture_output=True, timeout=30, text=True,
    )
    if list_result.returncode != 0:
        log(f"WARNING: Failed to list {remote_path} (curl code {list_result.returncode})")
        return (0, 0, [])
    body, _, list_code = (list_result.stdout or "").rpartition("\n")
    list_code = list_code.strip()
    if list_code in ("401", "403"):
        raise _AuthError(f"PROPFIND {remote_path} → HTTP {list_code}")
    if list_code and not list_code.startswith("2"):
        log(f"WARNING: PROPFIND {remote_path} → HTTP {list_code}")
        return (0, 0, [])

    hrefs = re.findall(r"<d:href>([^<]+)</d:href>", body)
    file_urls = [h for h in hrefs if not h.endswith("/")]
    if not file_urls:
        log(f"  {remote_path}: 0 files")
        return (0, 0, [])
    log(f"  {remote_path}: {len(file_urls)} files")

    downloaded = skipped = 0
    verified: list[str] = []
    for href in file_urls:
        file_url = _abs_url(href)
        filename = unquote(file_url.split("/")[-1])
        if not filename:
            continue
        dest = local_dir / filename
        # Skip only if a VALID media file already exists (a corrupt stub must be
        # re-fetched — the old `st_size > 12342` check let 512KB HTML stubs pass).
        if dest.exists() and _looks_like_media(dest):
            skipped += 1
            verified.append(href)  # already safely on SSD → safe to clean up
            continue

        tmp = dest.with_name(dest.name + ".part")
        result = subprocess.run(
            ["curl", "-s", "-k", "-u", f"{NEXTCLOUD_USER}:{NEXTCLOUD_PASSWORD}",
             "-o", str(tmp), "-w", "%{http_code}", file_url],
            capture_output=True, timeout=180, text=True,
        )
        http_code = (result.stdout or "").strip()[-3:]
        try:
            if result.returncode != 0:
                log(f"  WARNING: transfer error for {filename} (curl {result.returncode})")
            elif http_code in ("401", "403"):
                tmp.unlink(missing_ok=True)
                raise _AuthError(f"GET {filename} → HTTP {http_code}")
            elif http_code != "200":
                log(f"  WARNING: HTTP {http_code} for {filename} — discarding")
            elif not _looks_like_media(tmp):
                # The exact 2026-05-31 failure: a non-image body (login page) came
                # back with some status. Never let it masquerade as a photo.
                log(f"  WARNING: {filename} is not valid media (HTTP {http_code}, "
                    f"likely an HTML/login page) — discarding, NOT deleting source")
            else:
                tmp.replace(dest)            # atomic rename: real path only ever holds a valid file
                downloaded += 1
                verified.append(href)
                continue
        finally:
            tmp.unlink(missing_ok=True)
    return (downloaded, skipped, verified)


def download_photos() -> tuple[bool, list[str]]:
    """Download photos from the ALLOWED /InstantUpload/ subfolders only.

    Enforces the scope policy declared at the top of this file. Returns
    (ok, verified_hrefs). On auth failure returns (False, []) so the caller
    skips cleanup entirely.
    """
    if not NEXTCLOUD_PASSWORD:
        log("ERROR: NEXTCLOUD_PASSWORD not set. Cannot sync photos.")
        return (False, [])
    if not EXTERNAL_DRIVE.exists():
        log(f"ERROR: External drive not mounted: {EXTERNAL_DRIVE}")
        return (False, [])

    try:
        # Discover what's actually under /InstantUpload/ so we can log whether
        # any disallowed subfolders exist (for visibility).
        base_url = f"{NEXTCLOUD_URL}/remote.php/dav/files/{NEXTCLOUD_USER}{INSTANTUPLOAD_BASE}/"
        list_result = subprocess.run(
            ["curl", "-s", "-k", "-X", "PROPFIND", "-H", "Depth: 1",
             "-u", f"{NEXTCLOUD_USER}:{NEXTCLOUD_PASSWORD}", base_url],
            capture_output=True, timeout=30, text=True,
        )
        present = set()
        for href in re.findall(r"<d:href>([^<]+)</d:href>", list_result.stdout):
            m = re.search(rf"{re.escape(INSTANTUPLOAD_BASE)}/([^/]+)/?$", href)
            if m:
                present.add(m.group(1))
        skipped_subs = present - set(ALLOWED_INSTANTUPLOAD_SUBFOLDERS)
        if skipped_subs:
            log(f"Ignoring disallowed InstantUpload subfolders: {sorted(skipped_subs)} "
                f"(allowlist: {ALLOWED_INSTANTUPLOAD_SUBFOLDERS})")

        total_new = total_skip = 0
        all_verified: list[str] = []
        for sub in ALLOWED_INSTANTUPLOAD_SUBFOLDERS:
            new, skip, verified = _download_subfolder(sub)
            total_new += new
            total_skip += skip
            all_verified.extend(verified)
        log(f"Sync complete: {total_new} new, {total_skip} already-present "
            f"(across {ALLOWED_INSTANTUPLOAD_SUBFOLDERS})")
        return (True, all_verified)

    except _AuthError as e:
        log(f"ERROR: authentication failed ({e}). The Nextcloud app password is "
            f"likely expired/invalid. ABORTING run — no source files deleted. "
            f"Regenerate an app password at /settings/user/security and update "
            f"the LaunchAgent.")
        return (False, [])
    except subprocess.TimeoutExpired:
        log("ERROR: Sync operation timed out")
        return (False, [])
    except Exception as e:
        log(f"ERROR: Sync failed: {e}")
        return (False, [])


def cleanup_nextcloud(verified_hrefs: list[str]) -> None:
    """Delete from Nextcloud ONLY the files verified present on the SSD.

    Per-file WebDAV DELETE (never a folder-level wipe), so an original is removed
    from the server only after a valid copy is confirmed locally. The Camera
    folder is then ensured-present via MKCOL: on 2026-04-26 a folder-level delete
    left it gone and Nextcloud Android stopped re-creating it → 3 weeks of failed
    uploads, so we always leave a valid upload target behind.
    """
    if not NEXTCLOUD_PASSWORD:
        log("WARNING: Skipping cleanup - no password set")
        return
    if not verified_hrefs:
        log("Cleanup: nothing verified on SSD this run — leaving server untouched")
    else:
        creds = f"{NEXTCLOUD_USER}:{NEXTCLOUD_PASSWORD}"
        deleted = 0
        for href in verified_hrefs:
            url = _abs_url(href)
            name = unquote(url.split("/")[-1])
            result = subprocess.run(
                ["curl", "-s", "-k", "-X", "DELETE", "-u", creds, url,
                 "-o", "/dev/null", "-w", "%{http_code}"],
                capture_output=True, timeout=60, text=True,
            )
            code = (result.stdout or "").strip()[-3:]
            if result.returncode == 0 and code in ("200", "204", "404"):
                deleted += 1
            else:
                log(f"WARNING: cleanup DELETE {name} → HTTP {code} (curl {result.returncode})")
        log(f"Cleanup: deleted {deleted}/{len(verified_hrefs)} verified files from Nextcloud")

    # Always ensure the Camera folder exists for the next phone upload.
    try:
        creds = f"{NEXTCLOUD_USER}:{NEXTCLOUD_PASSWORD}"
        webdav_url = f"{NEXTCLOUD_URL}/remote.php/dav/files/{NEXTCLOUD_USER}{ANDROID_PHOTOS_PATH}"
        recreate = subprocess.run(
            ["curl", "-k", "-X", "MKCOL", "-u", creds, webdav_url,
             "-o", "/dev/null", "-w", "%{http_code}"],
            capture_output=True, timeout=30, text=True,
        )
        code = recreate.stdout.strip()
        if code in ("201", "405"):  # 201=created, 405=already exists
            log(f"Upload folder preserved (MKCOL {code})")
        else:
            log(f"WARNING: Folder recreation got HTTP {code}")
    except Exception as e:
        log(f"WARNING: Folder preservation failed: {e}")


def main():
    """Run the photo sync pipeline."""
    log("Starting Nextcloud Android photo sync...")

    if not NEXTCLOUD_PASSWORD:
        log("ERROR: NEXTCLOUD_PASSWORD environment variable not set")
        log("Set via: export NEXTCLOUD_PASSWORD='your-nc-password'")
        return 1

    ok, verified = download_photos()
    if ok:
        cleanup_nextcloud(verified)
        log("Photo sync completed successfully")
        return 0
    else:
        log("Photo sync failed - skipping cleanup (originals left intact on server)")
        return 1


if __name__ == "__main__":
    exit(main())
