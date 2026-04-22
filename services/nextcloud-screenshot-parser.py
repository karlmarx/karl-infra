#!/usr/bin/env python
"""
Nextcloud Screenshot Parser - Multi-purpose Document Extractor

Syncs Screenshots folder from Nextcloud Android InstantUploads
Uses MLX-VLM to detect and classify: return labels, receipts, warranties, invoices, etc.
Creates TODOs for time-sensitive items, organizes on external drive
"""

import os
import subprocess
import json
from pathlib import Path
from datetime import datetime, timedelta
import re
import shutil

# Configuration
NEXTCLOUD_URL = "https://karlmarx.tofino.usbx.me/nextcloud"
NEXTCLOUD_USER = os.getenv("NEXTCLOUD_USER", "karlmarx")
NEXTCLOUD_PASSWORD = os.getenv("NEXTCLOUD_PASSWORD")
SCREENSHOTS_PATH = "/InstantUpload/Screenshots/"  # Folder where Android InstantUpload saves screenshots
EXTERNAL_DRIVE = Path("/Volumes/Crucial X9/photos/incoming/screenshots")
DOCUMENTS_DIR = Path("/Volumes/Crucial X9/documents")
LOG_FILE = Path.home() / ".local/share/nextcloud-sync/screenshot-parser.log"
CATALOG_FILE = Path.home() / ".local/share/nextcloud-sync/document-catalog.json"
TODOIST_INBOX = Path.home() / "karl-todo"  # Git-synced Todoist mirror

def log(message):
    """Log message to file and stdout."""
    timestamp = datetime.now().isoformat()
    log_entry = f"[{timestamp}] {message}"
    print(log_entry)
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(LOG_FILE, "a") as f:
        f.write(log_entry + "\n")

def list_screenshots():
    """List all screenshots in Nextcloud."""
    webdav_url = f"{NEXTCLOUD_URL}/remote.php/dav/files/{NEXTCLOUD_USER}{SCREENSHOTS_PATH}"

    list_cmd = [
        "curl",
        "-s",
        "-k",
        "-m", "10",  # 10 second timeout for curl
        "-X", "PROPFIND",
        "-u", f"{NEXTCLOUD_USER}:{NEXTCLOUD_PASSWORD}",
        webdav_url
    ]

    try:
        result = subprocess.run(list_cmd, capture_output=True, timeout=15, text=True)

        if result.returncode != 0:
            log(f"WARNING: Failed to list screenshots (code {result.returncode})")
            return []

        # Parse XML response
        import re
        hrefs = re.findall(r'<d:href>([^<]+)</d:href>', result.stdout)

        # Filter out directory itself and non-image files
        image_extensions = ('.jpg', '.jpeg', '.png', '.gif', '.webp')
        file_urls = [h for h in hrefs if not h.endswith('/') and any(h.lower().endswith(ext) for ext in image_extensions)]

        return file_urls

    except subprocess.TimeoutExpired:
        log(f"WARNING: Screenshot listing timed out (folder may be empty or path incorrect)")
        return []

def download_screenshot(file_url, local_path):
    """Download a single screenshot."""
    download_cmd = [
        "curl",
        "-s",
        "-k",
        "-u", f"{NEXTCLOUD_USER}:{NEXTCLOUD_PASSWORD}",
        "-o", str(local_path),
        file_url
    ]

    result = subprocess.run(download_cmd, capture_output=True, timeout=120)
    return result.returncode == 0

def analyze_document(image_path):
    """Use MLX-VLM to classify and extract info from document/screenshot."""
    try:
        # Multi-part analysis
        classify_prompt = """Classify this image into ONE category:
- return_label (shipping return, RMA, barcode)
- receipt (purchase receipt, invoice)
- warranty (warranty info, guarantee card)
- ticket (event, appointment, confirmation)
- deadline (bill, payment due, deadline notice)
- other (anything else important to keep)

Only respond with the category name."""

        mlx_cmd = [
            "python3", "-c",
            f"""
import sys
from mlx_vlm.generate import generate_image_description

try:
    classification = generate_image_description("{image_path}", '{classify_prompt}')
    print(classification.strip().lower())
except Exception as e:
    print("other")
"""
        ]

        result = subprocess.run(mlx_cmd, capture_output=True, timeout=60, text=True)

        if result.returncode == 0:
            category = result.stdout.strip().lower()
            # Validate category
            valid_categories = ['return_label', 'receipt', 'warranty', 'ticket', 'deadline', 'other']
            if any(cat in category for cat in valid_categories):
                return category

        return "other"

    except Exception as e:
        log(f"WARNING: MLX-VLM analysis failed: {e}")
        return "other"

def extract_dates(image_path):
    """Extract dates from image using OCR/MLX-VLM."""
    try:
        date_prompt = """Extract any dates visible in this image (return deadlines, expiry dates, event dates, payment dates).
Format: YYYY-MM-DD if possible, or describe the date (e.g., "30 days from purchase").
If no dates found, respond with 'none'."""

        mlx_cmd = [
            "python3", "-c",
            f"""
import sys
from mlx_vlm.generate import generate_image_description

try:
    dates = generate_image_description("{image_path}", '{date_prompt}')
    print(dates.strip())
except Exception as e:
    print("none")
"""
        ]

        result = subprocess.run(mlx_cmd, capture_output=True, timeout=60, text=True)

        if result.returncode == 0:
            dates_str = result.stdout.strip()
            if dates_str.lower() != "none":
                return dates_str

        return None

    except Exception as e:
        log(f"WARNING: Date extraction failed: {e}")
        return None

def create_todo(title, due_date=None, category=""):
    """Create a TODO in karl-todo (Todoist mirror)."""
    if not TODOIST_INBOX.exists():
        log(f"WARNING: {TODOIST_INBOX} not found, skipping TODO creation")
        return

    try:
        todo_file = TODOIST_INBOX / "todo.md"
        if not todo_file.exists():
            log(f"WARNING: {todo_file} not found")
            return

        # Format: - [ ] Task (@project +tag due:YYYY-MM-DD)
        due_str = f" due:{due_date}" if due_date else ""
        project_tag = f"@{category}" if category else ""
        task_line = f"- [ ] {title} {project_tag}{due_str}\n"

        with open(todo_file, "a") as f:
            f.write(task_line)

        log(f"✓ Created TODO: {title}")

    except Exception as e:
        log(f"WARNING: Failed to create TODO: {e}")

def process_screenshots():
    """Download, analyze, and organize screenshots."""
    if not NEXTCLOUD_PASSWORD:
        log("ERROR: NEXTCLOUD_PASSWORD not set")
        return False

    file_urls = list_screenshots()

    if not file_urls:
        log("No screenshots found in /InstantUpload/Screenshots/")
        return True

    log(f"Found {len(file_urls)} screenshots to process")

    EXTERNAL_DRIVE.mkdir(parents=True, exist_ok=True)
    DOCUMENTS_DIR.mkdir(parents=True, exist_ok=True)

    processed = 0
    catalog = {}
    todos_created = 0

    for file_url in file_urls:
        if not file_url.startswith('http'):
            file_url = f"{NEXTCLOUD_URL}{file_url}"

        filename = file_url.split('/')[-1]
        if not filename:
            continue

        # Download to temp location
        temp_path = EXTERNAL_DRIVE / filename

        # Skip if already processed
        if temp_path.exists():
            log(f"⊘ Already processed: {filename}")
            continue

        log(f"Processing: {filename}")

        if not download_screenshot(file_url, temp_path):
            log(f"WARNING: Failed to download {filename}")
            continue

        # Analyze document
        category = analyze_document(str(temp_path))
        dates = extract_dates(str(temp_path))

        # Organize by category
        org_path = DOCUMENTS_DIR / category
        org_path.mkdir(parents=True, exist_ok=True)
        final_path = org_path / filename

        shutil.move(str(temp_path), str(final_path))
        log(f"✓ [{category.upper()}] {filename}")

        # Catalog entry
        catalog_entry = {
            "detected": datetime.now().isoformat(),
            "path": str(final_path),
            "type": category,
            "dates": dates
        }
        catalog[filename] = catalog_entry

        # Create TODO for time-sensitive items
        if category == "return_label":
            create_todo(f"Return: {filename[:20]}...", due_date=dates, category="returns")
            todos_created += 1

        elif category == "deadline":
            create_todo(f"Deadline: {filename[:20]}...", due_date=dates, category="deadlines")
            todos_created += 1

        elif category == "ticket":
            create_todo(f"Event: {filename[:20]}...", due_date=dates, category="tickets")
            todos_created += 1

        elif category == "receipt":
            create_todo(f"Receipt: {filename[:20]}...", due_date=None, category="receipts")
            todos_created += 1

        elif category == "warranty":
            create_todo(f"Warranty: {filename[:20]}...", due_date=dates, category="warranties")
            todos_created += 1

        processed += 1

    # Update catalog
    if processed > 0:
        CATALOG_FILE.parent.mkdir(parents=True, exist_ok=True)
        try:
            with open(CATALOG_FILE, "r") as f:
                existing = json.load(f)
            existing.update(catalog)
        except:
            existing = catalog

        with open(CATALOG_FILE, "w") as f:
            json.dump(existing, f, indent=2)

    log(f"Processed {processed} documents, created {todos_created} TODOs")
    return True

def cleanup_nextcloud():
    """Delete screenshots from Nextcloud after processing."""
    if not NEXTCLOUD_PASSWORD:
        log("WARNING: Skipping cleanup - no password")
        return

    try:
        webdav_url = f"{NEXTCLOUD_URL}/remote.php/dav/files/{NEXTCLOUD_USER}{SCREENSHOTS_PATH}"

        delete_cmd = [
            "curl",
            "-s",
            "-k",
            "-m", "5",  # 5 second timeout for curl
            "-X", "DELETE",
            "-u", f"{NEXTCLOUD_USER}:{NEXTCLOUD_PASSWORD}",
            webdav_url
        ]

        result = subprocess.run(delete_cmd, capture_output=True, timeout=10)

        if result.returncode == 0:
            log("Cleaned up screenshots from Nextcloud")
        else:
            log(f"WARNING: Cleanup returned code {result.returncode} (folder may not exist)")

    except subprocess.TimeoutExpired:
        log(f"WARNING: Cleanup timed out (skipping)")
    except Exception as e:
        log(f"WARNING: Cleanup failed: {e}")

def main():
    """Run screenshot parser pipeline."""
    log("Starting Nextcloud screenshot parser...")

    if not NEXTCLOUD_PASSWORD:
        log("ERROR: NEXTCLOUD_PASSWORD not set")
        return 1

    if process_screenshots():
        cleanup_nextcloud()
        log("Screenshot parsing completed")
        return 0
    else:
        log("Screenshot parsing failed")
        return 1

if __name__ == "__main__":
    exit(main())
