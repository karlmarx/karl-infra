#!/usr/bin/env python3
"""Watch for new workout videos and process them with Gemma."""

# /// script
# requires-python = ">=3.14"
# dependencies = ["psutil"]
# ///

import argparse
import os
import sqlite3
import sys
import time
import urllib.request
from datetime import datetime, timedelta
from logging.handlers import RotatingFileHandler
from pathlib import Path
import logging

import psutil


def setup_logging(log_path: Path) -> logging.Logger:
    """Configure logger with file rotation."""
    log_path.parent.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger("workout_watcher")
    logger.setLevel(logging.DEBUG)

    handler = RotatingFileHandler(log_path, maxBytes=5*1024*1024, backupCount=3)
    formatter = logging.Formatter("[%(asctime)s] %(levelname)s: %(message)s", "%H:%M:%S")
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    return logger


def ram_available_gb() -> float:
    """Return available RAM in GB."""
    return psutil.virtual_memory().available / (1024**3)


def ram_state() -> str:
    """Return RAM state: 'ok' | 'caution' | 'tight' | 'critical'."""
    available_gb = ram_available_gb()
    if available_gb < 0.2:
        return "critical"
    elif available_gb < 0.5:
        return "tight"
    elif available_gb < 1.0:
        return "caution"
    else:
        return "ok"


def mlx_is_up(logger: logging.Logger) -> bool:
    """Check if MLX-VLM server is responding."""
    try:
        urllib.request.urlopen("http://localhost:8080/v1/models", timeout=3)
        return True
    except Exception as e:
        logger.warning(f"MLX-VLM health check failed: {e}")
        return False


def db_connect(db_path: Path) -> sqlite3.Connection:
    """Open state DB, create schema if needed."""
    db_path.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(db_path)
    con.execute("PRAGMA journal_mode=WAL")

    con.execute("""
        CREATE TABLE IF NOT EXISTS videos (
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
        )
    """)
    con.commit()
    return con


def acquire_lock(lock_path: Path) -> bool:
    """Attempt to acquire a lockfile. Return True if acquired."""
    if lock_path.exists():
        try:
            pid = int(lock_path.read_text().strip())
            os.kill(pid, 0)  # signal 0 = existence check
            return False  # already running
        except (ProcessLookupError, ValueError):
            pass  # stale lock

    lock_path.parent.mkdir(parents=True, exist_ok=True)
    lock_path.write_text(str(os.getpid()))
    return True


def release_lock(lock_path: Path):
    """Remove the lockfile."""
    try:
        lock_path.unlink()
    except FileNotFoundError:
        pass


def discover_videos(
    scan_root: Path,
    db: sqlite3.Connection,
    logger: logging.Logger,
    max_age_days: int = 30,
    list_only: bool = False
) -> list[Path]:
    """
    Walk scan_root for .mp4 files matching filter criteria.
    Returns list of unprocessed videos.
    """
    # Get already-processed SHAs from DB
    cursor = db.execute("SELECT sha FROM videos")
    processed_shas = set(row[0] for row in cursor.fetchall())

    cutoff_time = datetime.now() - timedelta(days=max_age_days)

    candidates = []
    for mp4_path in scan_root.rglob("*.mp4"):
        size = mp4_path.stat().st_size
        mtime = datetime.fromtimestamp(mp4_path.stat().st_mtime)

        # Filter: size, age, must be a file
        if not mp4_path.is_file():
            continue
        if size < 5_000_000 or size > 2_000_000_000:
            continue
        if mtime < cutoff_time:
            continue

        # Compute SHA to check if already processed
        try:
            sys.path.insert(0, os.getenv("WORKOUT_DATA_ROOT", "/Users/kmx/projects/local-vlm-analysis"))
            from extract_frames import sha256_head
            sha = sha256_head(mp4_path)
        except ImportError:
            logger.error("Could not import sha256_head from extract_frames")
            continue

        if sha in processed_shas:
            continue

        candidates.append(mp4_path)
        if list_only:
            size_mb = size / (1024**2)
            logger.info(f"[list] {mp4_path.name} ({size_mb:.1f} MB, SHA {sha[:8]}...)")

    return candidates


def process_one(
    video_path: Path,
    db: sqlite3.Connection,
    logger: logging.Logger,
    data_root: Path
) -> bool:
    """
    Process one video with the full Gemma pipeline.
    Updates DB on success/failure. Returns True on success.
    """
    # Change to data_root so relative paths in process_video work
    os.chdir(data_root)

    # Import here (after chdir)
    try:
        from extract_frames import sha256_head
        from process_video import process
    except ImportError as e:
        logger.error(f"Could not import pipeline: {e}")
        return False

    sha = sha256_head(video_path)
    logger.info(f"Processing {video_path.name} (SHA {sha[:8]}...)")

    try:
        result = process(str(video_path), no_audio=True)
        json_path = data_root / "data" / "videos" / f"{sha}.json"

        if json_path.exists():
            db.execute(
                "INSERT OR REPLACE INTO videos (sha, source_path, file_name, size_bytes, gemma_done_at, gemma_json_path, retry_count) "
                "VALUES (?, ?, ?, ?, datetime('now'), ?, 0)",
                (sha, str(video_path), video_path.name, video_path.stat().st_size, str(json_path))
            )
            db.commit()
            logger.info(f"✓ Processed {video_path.name}")
            return True
        else:
            logger.error(f"process() succeeded but JSON not found: {json_path}")
            db.execute(
                "INSERT OR REPLACE INTO videos (sha, source_path, file_name, size_bytes, gemma_error, retry_count) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (sha, str(video_path), video_path.name, video_path.stat().st_size, "JSON not written", 0)
            )
            db.commit()
            return False

    except Exception as e:
        logger.error(f"✗ Failed to process {video_path.name}: {e}")
        db.execute(
            "INSERT OR IGNORE INTO videos (sha, source_path, file_name, size_bytes, gemma_error, retry_count) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (sha, str(video_path), video_path.name, video_path.stat().st_size, str(e)[:200], 0)
        )
        db.commit()
        return False


def main():
    """Main watcher loop."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--list-only", action="store_true", help="List videos without processing")
    parser.add_argument("--interval", type=int, default=900, help="Sleep interval in seconds")
    parser.add_argument("--max-age-days", type=int, default=30, help="Max age of videos to process")
    args = parser.parse_args()

    scan_root = Path(os.getenv("WORKOUT_SCAN_ROOT", "/Volumes/Crucial X9/photos/incoming"))
    data_root = Path(os.getenv("WORKOUT_DATA_ROOT", "/Users/kmx/projects/local-vlm-analysis"))
    max_per_run = int(os.getenv("MAX_PER_RUN", "5"))
    log_path = Path.home() / ".local/share/workout-pipeline/ingest-stdout.log"
    lock_path = Path.home() / ".local/share/workout-pipeline/ingest.lock"
    db_path = Path.home() / ".local/share/workout-pipeline/state.db"

    logger = setup_logging(log_path)
    logger.info(f"Starting watcher (scan_root={scan_root}, data_root={data_root})")

    if not mlx_is_up(logger):
        logger.error("MLX-VLM server not responding. Exiting.")
        return 1

    if args.list_only:
        db = db_connect(db_path)
        discover_videos(scan_root, db, logger, max_age_days=args.max_age_days, list_only=True)
        db.close()
        return 0

    # Main loop
    while True:
        if not acquire_lock(lock_path):
            logger.debug("Watcher already running, exiting")
            return 0

        try:
            state = ram_state()
            available_gb = ram_available_gb()
            logger.info(f"RAM state: {state} ({available_gb:.1f} GB available)")

            if state == "critical":
                logger.warning("RAM critical, exiting watcher")
                return 0

            if state == "tight":
                logger.warning("RAM tight, will retry after sleep")
                time.sleep(300)
                state = ram_state()
                if state != "ok" and state != "caution":
                    logger.warning("RAM still tight after retry, exiting")
                    return 0

            db = db_connect(db_path)
            candidates = discover_videos(scan_root, db, logger, max_age_days=args.max_age_days)

            processed = 0
            for video_path in candidates[:max_per_run]:
                if process_one(video_path, db, logger, data_root):
                    processed += 1

                # Check RAM between videos
                if ram_state() == "critical":
                    logger.warning("RAM critical mid-run, stopping")
                    break

            db.close()
            logger.info(f"Cycle complete: {processed}/{len(candidates[:max_per_run])} processed")

        except Exception as e:
            logger.exception(f"Unhandled error: {e}")

        finally:
            release_lock(lock_path)

        logger.debug(f"Sleeping {args.interval}s until next cycle")
        time.sleep(args.interval)


if __name__ == "__main__":
    sys.exit(main())
