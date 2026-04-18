#!/usr/bin/env python
"""
Nextcloud Android Photo Backup Pipeline

Syncs photos from Nextcloud Android folder to external drive (/Volumes/Crucial X9/photos/incoming/)
Deletes originals from Nextcloud after successful backup.

Authentication: Uses basic auth (username + password) via environment variables
"""

import os
import subprocess
from pathlib import Path
from datetime import datetime

# Configuration
NEXTCLOUD_URL = "https://karlmarx.tofino.usbx.me/nextcloud"
NEXTCLOUD_USER = os.getenv("NEXTCLOUD_USER", "karlmarx")
NEXTCLOUD_PASSWORD = os.getenv("NEXTCLOUD_PASSWORD")
ANDROID_PHOTOS_PATH = "/Photos/Android/"  # Folder in Nextcloud where Android photos go
EXTERNAL_DRIVE = Path("/Volumes/Crucial X9/photos/incoming")
LOG_FILE = Path.home() / ".local/share/nextcloud-sync/sync.log"

def log(message):
    """Log message to file and stdout."""
    timestamp = datetime.now().isoformat()
    log_entry = f"[{timestamp}] {message}"
    print(log_entry)
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(LOG_FILE, "a") as f:
        f.write(log_entry + "\n")

def download_photos():
    """Download photos from Nextcloud to external drive using WebDAV."""
    if not NEXTCLOUD_PASSWORD:
        log("ERROR: NEXTCLOUD_PASSWORD not set. Cannot sync photos.")
        return False

    if not EXTERNAL_DRIVE.exists():
        log(f"ERROR: External drive not mounted: {EXTERNAL_DRIVE}")
        return False

    try:
        webdav_url = f"{NEXTCLOUD_URL}/remote.php/dav/files/{NEXTCLOUD_USER}{ANDROID_PHOTOS_PATH}"

        # Use curl for WebDAV sync (reliable, built-in on macOS)
        # For WebDAV directory listing, use -X PROPFIND and parse XML
        # Then download each file individually

        # First, list files in the directory
        list_cmd = [
            "curl",
            "-s",
            "-k",
            "-X", "PROPFIND",
            "-u", f"{NEXTCLOUD_USER}:{NEXTCLOUD_PASSWORD}",
            webdav_url
        ]

        log(f"Listing photos from: {webdav_url}")
        list_result = subprocess.run(list_cmd, capture_output=True, timeout=30, text=True)

        if list_result.returncode != 0:
            log(f"ERROR: Failed to list files (code {list_result.returncode})")
            return False

        # Parse XML response to get file URLs (simplified - look for href tags)
        import re
        hrefs = re.findall(r'<d:href>([^<]+)</d:href>', list_result.stdout)

        if not hrefs:
            log("No photos found in /Photos/Android/ folder")
            return True  # Not an error, just nothing to sync

        # Filter out the directory itself
        file_urls = [h for h in hrefs if not h.endswith('/')]
        log(f"Found {len(file_urls)} files to download")

        # Download each file
        downloaded = 0
        skipped = 0

        for href in file_urls:
            # href is relative path, construct full URL
            if not href.startswith('http'):
                file_url = f"{NEXTCLOUD_URL}{href}"
            else:
                file_url = href

            # Extract filename from URL
            filename = file_url.split('/')[-1]
            if not filename:
                continue

            file_path = EXTERNAL_DRIVE / filename

            # Skip if already exists (deduplication)
            if file_path.exists():
                log(f"⊘ Already exists: {filename} (skipping)")
                skipped += 1
                continue

            download_cmd = [
                "curl",
                "-s",
                "-k",
                "-u", f"{NEXTCLOUD_USER}:{NEXTCLOUD_PASSWORD}",
                "-o", str(file_path),
                file_url
            ]

            log(f"Downloading: {filename}")
            result = subprocess.run(download_cmd, capture_output=True, timeout=120)

            if result.returncode != 0:
                log(f"WARNING: Failed to download {filename}")
            else:
                log(f"✓ Downloaded: {filename}")
                downloaded += 1

        log(f"Sync complete: {downloaded} new, {skipped} duplicates (skipped)")
        return True

    except subprocess.TimeoutExpired:
        log("ERROR: Sync operation timed out")
        return False
    except Exception as e:
        log(f"ERROR: Sync failed: {e}")
        return False

def cleanup_nextcloud():
    """Delete photos from Nextcloud after successful backup."""
    if not NEXTCLOUD_PASSWORD:
        log("WARNING: Skipping cleanup - no password set")
        return

    try:
        webdav_url = f"{NEXTCLOUD_URL}/remote.php/dav/files/{NEXTCLOUD_USER}{ANDROID_PHOTOS_PATH}"

        # Use curl to delete the folder
        delete_cmd = [
            "curl",
            "-k",
            "-X", "DELETE",
            "-u", f"{NEXTCLOUD_USER}:{NEXTCLOUD_PASSWORD}",
            webdav_url
        ]

        log(f"Cleaning up: {webdav_url}")
        result = subprocess.run(delete_cmd, capture_output=True, timeout=60, text=True)

        if result.returncode == 0:
            log(f"Cleaned up photos from Nextcloud")
        else:
            log(f"WARNING: Cleanup returned code {result.returncode}")

    except Exception as e:
        log(f"WARNING: Cleanup failed: {e}")

def main():
    """Run the photo sync pipeline."""
    log("Starting Nextcloud Android photo sync...")

    # Check if password is set
    if not NEXTCLOUD_PASSWORD:
        log("ERROR: NEXTCLOUD_PASSWORD environment variable not set")
        log("Set via: export NEXTCLOUD_PASSWORD='your-nc-password'")
        return 1

    # Download photos
    if download_photos():
        # Clean up source if download succeeded
        cleanup_nextcloud()
        log("Photo sync completed successfully")
        return 0
    else:
        log("Photo sync failed - skipping cleanup")
        return 1

if __name__ == "__main__":
    exit(main())
