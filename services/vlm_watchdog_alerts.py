#!/usr/bin/env python3
"""Reactive watchdog alerts for the VLM stack.

Runs every 10 min via launchd. Checks several conditions and emits ONE
combined email when any fire. Per-check throttle prevents alert spam
(same condition won't re-alert within 60 min).

Checks:
  1. memory_pause_flood — memory_guard logged 3+ pauses in last 60 min
  2. mlx_server_down — :8081 unreachable for >5 min
  3. worker_plateau — JSON count hasn't advanced in >24h
  4. unexpected_27b — disable-27b flag set but :8080 process exists
  5. continuous_log_stale — no log activity in >30 min while worker is running

State persisted at ~/.local/share/vlm-alerts/state.json — tracks last-alert
timestamps per check, plus auxiliary state (first-fail-time for mlx server,
last-seen video count for plateau detection).
"""

# /// script
# requires-python = ">=3.14"
# dependencies = ["psutil", "requests"]
# ///

from __future__ import annotations

import json
import os
import re
import socket
import sys
import urllib.error
import urllib.request
from datetime import datetime, timedelta
from pathlib import Path

import psutil

# Allow importing the shared email helper which lives next to this file
sys.path.insert(0, str(Path(__file__).parent))
from _emaillib import send as send_email  # noqa: E402

STATE_FILE = Path.home() / ".local/share/vlm-alerts/state.json"
GUARD_LOG = Path.home() / "memory_guard.log"
CONTINUOUS_LOG_DIR = Path.home() / ".local/share/local-vlm-analysis"
VIDEOS_DIR = Path("/Users/kmx/projects/local-vlm-analysis/data/videos")
DISABLE_27B = Path.home() / ".openclaw/watchdog/disable-27b"
MLX_8081 = "http://localhost:8081/v1/models"

ALERT_THROTTLE = timedelta(minutes=60)
MLX_DOWN_TOLERANCE = timedelta(minutes=5)
MEMORY_PAUSE_WINDOW = timedelta(minutes=60)
MEMORY_PAUSE_THRESHOLD = 3
WORKER_PLATEAU_THRESHOLD = timedelta(hours=24)
LOG_STALE_THRESHOLD = timedelta(minutes=30)


def load_state() -> dict:
    if not STATE_FILE.exists():
        return {}
    try:
        return json.loads(STATE_FILE.read_text())
    except json.JSONDecodeError:
        return {}


def save_state(state: dict) -> None:
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, indent=2, default=str))


def should_alert(state: dict, check: str, now: datetime) -> bool:
    last = state.get("last_alert", {}).get(check)
    if not last:
        return True
    try:
        last_dt = datetime.fromisoformat(last)
    except ValueError:
        return True
    return now - last_dt > ALERT_THROTTLE


def mark_alerted(state: dict, check: str, now: datetime) -> None:
    state.setdefault("last_alert", {})[check] = now.isoformat()


def check_memory_pause_flood(state: dict, now: datetime) -> str | None:
    if not GUARD_LOG.exists():
        return None
    cutoff = now - MEMORY_PAUSE_WINDOW
    count = 0
    log_pattern = re.compile(r"\[(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\] WARNING: Memory low")
    for line in GUARD_LOG.read_text(errors="replace").splitlines()[-2000:]:
        m = log_pattern.search(line)
        if m:
            try:
                ts = datetime.strptime(m.group(1), "%Y-%m-%d %H:%M:%S")
            except ValueError:
                continue
            if ts > cutoff:
                count += 1
    if count >= MEMORY_PAUSE_THRESHOLD:
        return f"memory_guard fired pause {count}× in last 60 min (threshold={MEMORY_PAUSE_THRESHOLD})"
    return None


def check_mlx_server(state: dict, now: datetime) -> str | None:
    """Returns alert message if :8081 has been down for >MLX_DOWN_TOLERANCE."""
    try:
        with urllib.request.urlopen(MLX_8081, timeout=5) as r:
            ok = r.status == 200
    except (urllib.error.URLError, socket.timeout):
        ok = False

    if ok:
        # clear any tracked first-fail
        state.pop("mlx_first_fail", None)
        return None

    first_fail = state.get("mlx_first_fail")
    if not first_fail:
        state["mlx_first_fail"] = now.isoformat()
        return None  # tolerate transient blip

    try:
        first_dt = datetime.fromisoformat(first_fail)
    except ValueError:
        state["mlx_first_fail"] = now.isoformat()
        return None

    elapsed = now - first_dt
    if elapsed > MLX_DOWN_TOLERANCE:
        return f"mlx-vlm :8081 unreachable for {int(elapsed.total_seconds() / 60)} min"
    return None


def check_worker_plateau(state: dict, now: datetime) -> str | None:
    """Alert if JSON count hasn't advanced in WORKER_PLATEAU_THRESHOLD."""
    if not VIDEOS_DIR.exists():
        return None
    count = sum(1 for _ in VIDEOS_DIR.glob("*.json"))

    plateau_state = state.get("plateau", {})
    last_count = plateau_state.get("count")
    last_ts = plateau_state.get("ts")

    if last_count != count or last_ts is None:
        state["plateau"] = {"count": count, "ts": now.isoformat()}
        return None

    try:
        last_dt = datetime.fromisoformat(last_ts)
    except ValueError:
        state["plateau"] = {"count": count, "ts": now.isoformat()}
        return None

    if now - last_dt > WORKER_PLATEAU_THRESHOLD:
        hrs = int((now - last_dt).total_seconds() / 3600)
        return f"video count stuck at {count} for {hrs}h (no new JSON written)"
    return None


def check_unexpected_27b(state: dict, now: datetime) -> str | None:
    if not DISABLE_27B.exists():
        return None
    for proc in psutil.process_iter(["pid", "cmdline"]):
        try:
            cmd = " ".join(proc.info.get("cmdline") or [])
            if "Qwen3.5-27B" in cmd or ":8080" in cmd and "mlx_vlm" in cmd:
                return f"27B server running (PID {proc.info['pid']}) despite disable-27b flag set"
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    return None


def check_continuous_log_stale(state: dict, now: datetime) -> str | None:
    """If launchd-managed worker is running but log hasn't budged in 30 min."""
    worker_up = any(
        "continuous_process.py" in " ".join(p.info.get("cmdline") or [])
        for p in psutil.process_iter(["cmdline"])
    )
    if not worker_up:
        return None

    if not CONTINUOUS_LOG_DIR.exists():
        return None
    logs = sorted(CONTINUOUS_LOG_DIR.glob("continuous-*.log"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not logs:
        return None
    latest_log = logs[0]
    last_mtime = datetime.fromtimestamp(latest_log.stat().st_mtime)
    if now - last_mtime > LOG_STALE_THRESHOLD:
        elapsed = int((now - last_mtime).total_seconds() / 60)
        return f"worker process up but log idle for {elapsed} min (last write to {latest_log.name})"
    return None


CHECKS = [
    ("memory_pause_flood", check_memory_pause_flood),
    ("mlx_server_down", check_mlx_server),
    ("worker_plateau", check_worker_plateau),
    ("unexpected_27b", check_unexpected_27b),
    ("continuous_log_stale", check_continuous_log_stale),
]


def main() -> int:
    now = datetime.now()
    state = load_state()
    firings = []
    for name, fn in CHECKS:
        try:
            msg = fn(state, now)
        except Exception as e:
            msg = f"check {name} raised {type(e).__name__}: {e}"
        if msg and should_alert(state, name, now):
            firings.append((name, msg))
            mark_alerted(state, name, now)

    save_state(state)

    if not firings:
        print(f"[{now:%H:%M:%S}] ok ({len(CHECKS)} checks, 0 firings)")
        return 0

    subject = f"⚠️ VLM watchdog · {len(firings)} alert{'s' if len(firings) > 1 else ''}"
    lines = [f"# VLM watchdog alerts", f"_{now.isoformat(timespec='seconds')}_", ""]
    for name, msg in firings:
        lines.append(f"- **{name}** — {msg}")
    lines.extend([
        "",
        "Throttled: same check won't re-alert for 60 min.",
        "",
        f"Verify: `launchctl print gui/$(id -u)/com.kmx.vlm-watchdog-alerts`",
        f"Logs: `tail ~/.local/share/vlm-alerts/stderr.log`",
        f"State: `cat ~/.local/share/vlm-alerts/state.json`",
        "",
        "Dashboard: https://command.93.fyi/status",
    ])
    plain = "\n".join(lines)
    html = (
        "<html><body style='font-family:-apple-system,sans-serif;max-width:600px;margin:1rem auto'>"
        "<pre style='white-space:pre-wrap'>"
        + plain.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        + "</pre></body></html>"
    )

    ok, info = send_email(subject, plain, html)
    print(f"[{now:%H:%M:%S}] {len(firings)} firings — email {'✓' if ok else '✗'} {info}")
    for n, m in firings:
        print(f"  - {n}: {m}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
